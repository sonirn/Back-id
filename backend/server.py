from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import asyncio
import json
import aiofiles
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
import google.generativeai as genai
import tempfile
import time
import asyncio
from typing import Optional, Dict, Any

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Cloudflare R2 setup
s3_client = boto3.client(
    's3',
    endpoint_url=os.environ.get('CLOUDFLARE_API_ENDPOINT'),
    aws_access_key_id=os.environ.get('CLOUDFLARE_ACCESS_KEY'),
    aws_secret_access_key=os.environ.get('CLOUDFLARE_SECRET_KEY'),
    config=Config(signature_version='s3v4')
)

# Create the main app
app = FastAPI(title="Video Generation Platform", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class VideoUploadRequest(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class VideoAnalysisResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    analysis: str
    plan: str
    status: str
    created_at: datetime
    sample_video_path: str
    character_image_path: Optional[str] = None
    audio_path: Optional[str] = None

class PlanModificationRequest(BaseModel):
    session_id: str
    modification_request: str

class VideoGenerationRequest(BaseModel):
    session_id: str
    approved_plan: str

class VideoGenerationStatus(BaseModel):
    session_id: str
    status: str
    progress: float
    estimated_time_remaining: Optional[int] = None
    error: Optional[str] = None

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime = Field(default_factory=datetime.utcnow)

# Gemini API Keys rotation
GEMINI_API_KEYS = [
    os.environ.get('GEMINI_API_KEY_1'),
    os.environ.get('GEMINI_API_KEY_2'),
    os.environ.get('GEMINI_API_KEY_3')
]

current_gemini_key_index = 0

def get_next_gemini_key():
    global current_gemini_key_index
    key = GEMINI_API_KEYS[current_gemini_key_index]
    current_gemini_key_index = (current_gemini_key_index + 1) % len(GEMINI_API_KEYS)
    return key

# File upload utilities
async def save_uploaded_file(file: UploadFile, filename: str) -> str:
    """Save uploaded file to temporary directory and return path"""
    temp_dir = Path(tempfile.gettempdir()) / "video_uploads"
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / filename
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    return str(file_path)

async def upload_to_r2(file_path: str, bucket_key: str) -> str:
    """Upload file to Cloudflare R2 and return public URL"""
    try:
        bucket_name = "video-generation-bucket"
        
        # Create bucket if it doesn't exist
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except ClientError:
            s3_client.create_bucket(Bucket=bucket_name)
        
        # Upload file
        s3_client.upload_file(file_path, bucket_name, bucket_key)
        
        # Generate public URL
        url = f"{os.environ.get('CLOUDFLARE_API_ENDPOINT')}/{bucket_name}/{bucket_key}"
        return url
        
    except Exception as e:
        logger.error(f"Failed to upload to R2: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Text-based video analysis for fallback
async def analyze_video_text_only(video_path: str, character_image_path: Optional[str] = None, audio_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze video using text-based prompts when file upload fails"""
    try:
        gemini_key = get_next_gemini_key()
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Create a detailed prompt based on file information
        file_info = f"Video file: {video_path}"
        if character_image_path:
            file_info += f"\nCharacter image: {character_image_path}"
        if audio_path:
            file_info += f"\nAudio file: {audio_path}"
        
        prompt = f"""I have uploaded a video file that needs analysis, but I can't process it directly right now. 
        
        File information:
        {file_info}
        
        Please create a comprehensive video analysis framework and plan for generating a similar video. 
        
        Assume this is a typical short-form video (under 60 seconds) that would be suitable for mobile viewing in 9:16 aspect ratio.
        
        Please provide:
        1. A detailed analysis framework covering:
           - Visual content structure
           - Audio content considerations
           - Narrative flow patterns
           - Technical specifications
           - Style and aesthetic guidelines
        
        2. A comprehensive plan for generating a similar video including:
           - Scene-by-scene breakdown template
           - Technical specifications (9:16 aspect ratio, under 60 seconds)
           - Content creation guidelines to avoid copying
           - Shot composition recommendations
           - Audio requirements
           - Character development if applicable
        
        Format your response as JSON with 'analysis' and 'plan' fields."""
        
        response = model.generate_content(prompt)
        
        # Parse response
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # If not JSON, create structured response
            return {
                "analysis": f"Video Analysis Framework:\n{response.text[:len(response.text)//2]}",
                "plan": f"Video Generation Plan:\n{response.text[len(response.text)//2:]}"
            }
            
    except Exception as e:
        logger.error(f"Text-only Gemini analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {str(e)}")

# Alternative Video analysis with Official Google Generative AI library
async def analyze_video_with_official_gemini(video_path: str, character_image_path: Optional[str] = None, audio_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze video using official Google Generative AI library"""
    try:
        gemini_key = get_next_gemini_key()
        
        # Configure the Google Generative AI client
        genai.configure(api_key=gemini_key)
        
        # Choose the model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        files_to_upload = []
        
        # Upload video file
        print(f"Uploading video file: {video_path}")
        video_file = genai.upload_file(path=video_path)
        files_to_upload.append(video_file)
        
        # Upload character image if provided
        if character_image_path:
            print(f"Uploading character image: {character_image_path}")
            image_file = genai.upload_file(path=character_image_path)
            files_to_upload.append(image_file)
        
        # Upload audio file if provided
        if audio_path:
            print(f"Uploading audio file: {audio_path}")
            audio_file = genai.upload_file(path=audio_path)
            files_to_upload.append(audio_file)
        
        # Wait for files to be processed
        for file in files_to_upload:
            while file.state.name == "PROCESSING":
                print(f"Processing file: {file.name}")
                await asyncio.sleep(2)
                file = genai.get_file(file.name)
            
            if file.state.name != "ACTIVE":
                raise Exception(f"File processing failed: {file.name} - State: {file.state.name}")
        
        # Create the prompt
        prompt = """Please analyze this video in extreme detail. Include:
        1. Complete visual analysis (scenes, objects, people, actions, camera work)
        2. Audio analysis (speech, music, sound effects, mood)
        3. Narrative structure and flow
        4. Technical specifications
        5. Overall style and theme
        
        Then create a comprehensive plan for generating a similar video with:
        - Same style and aesthetic approach
        - Similar narrative structure
        - Same technical specifications (9:16 aspect ratio, under 60 seconds)
        - Different content to avoid copying
        - Specific shot-by-shot breakdown
        - Audio requirements
        - Character requirements if applicable
        
        Format your response as JSON with 'analysis' and 'plan' fields."""
        
        # Generate content
        response = model.generate_content([prompt] + files_to_upload)
        
        # Parse response
        try:
            # Try to parse as JSON first
            import json
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # If not JSON, create structured response
            return {
                "analysis": response.text[:len(response.text)//2],
                "plan": response.text[len(response.text)//2:]
            }
            
    except Exception as e:
        logger.error(f"Official Gemini analysis failed: {str(e)}")
        # Try next API key
        gemini_key = get_next_gemini_key()
        
        # Retry with different model
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Re-upload files for retry
            files_to_upload = []
            video_file = genai.upload_file(path=video_path)
            files_to_upload.append(video_file)
            
            if character_image_path:
                image_file = genai.upload_file(path=character_image_path)
                files_to_upload.append(image_file)
            
            if audio_path:
                audio_file = genai.upload_file(path=audio_path)
                files_to_upload.append(audio_file)
            
            # Wait for processing
            for file in files_to_upload:
                while file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    file = genai.get_file(file.name)
                
                if file.state.name != "ACTIVE":
                    raise Exception(f"File processing failed: {file.name}")
            
            # Generate content with retry
            response = model.generate_content([prompt] + files_to_upload)
            
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                return {
                    "analysis": response.text[:len(response.text)//2],
                    "plan": response.text[len(response.text)//2:]
                }
                
        except Exception as retry_e:
            logger.error(f"Retry with official Gemini also failed: {str(retry_e)}")
            raise HTTPException(status_code=500, detail=f"Video analysis failed with both approaches: {str(e)} | Retry: {str(retry_e)}")

# Video analysis with Gemini
async def analyze_video_with_gemini(video_path: str, character_image_path: Optional[str] = None, audio_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze video using Gemini - try official library first, then fallback to emergentintegrations"""
    try:
        # First try with official Google Generative AI library
        logger.info("Attempting video analysis with official Google Generative AI library...")
        return await analyze_video_with_official_gemini(video_path, character_image_path, audio_path)
        
    except Exception as official_error:
        logger.warning(f"Official Gemini library failed: {str(official_error)}")
        logger.info("Falling back to emergentintegrations library...")
        
        # Fallback to emergentintegrations library
        try:
            gemini_key = get_next_gemini_key()
            
            # Initialize Gemini chat - Use stable models with free tier availability
            chat = LlmChat(
                api_key=gemini_key,
                session_id=f"video_analysis_{uuid.uuid4()}",
                system_message="""You are an expert video analyst. Analyze the provided video in extreme detail including:
                1. Visual content: scenes, objects, people, actions, movements, colors, lighting
                2. Audio content: speech, music, sound effects, tone, mood
                3. Narrative structure: beginning, middle, end, story progression
                4. Style and aesthetics: camera angles, transitions, effects, filters
                5. Technical aspects: resolution, frame rate, duration, aspect ratio
                6. Overall theme and message
                
                Then create a detailed plan for generating a similar video with the same style, theme, and structure but with different content to avoid direct copying."""
            ).with_model("gemini", "gemini-2.5-flash-preview-04-17")
            
            # Prepare files for analysis
            file_contents = []
            
            # Add video file
            video_file = FileContentWithMimeType(
                file_path=video_path,
                mime_type="video/mp4"
            )
            file_contents.append(video_file)
            
            # Add character image if provided
            if character_image_path:
                image_file = FileContentWithMimeType(
                    file_path=character_image_path,
                    mime_type="image/jpeg"
                )
                file_contents.append(image_file)
            
            # Add audio file if provided
            if audio_path:
                audio_file = FileContentWithMimeType(
                    file_path=audio_path,
                    mime_type="audio/mpeg"
                )
                file_contents.append(audio_file)
            
            # Send analysis request
            message = UserMessage(
                text="""Please analyze this video in extreme detail. Include:
                1. Complete visual analysis (scenes, objects, people, actions, camera work)
                2. Audio analysis (speech, music, sound effects, mood)
                3. Narrative structure and flow
                4. Technical specifications
                5. Overall style and theme
                
                Then create a comprehensive plan for generating a similar video with:
                - Same style and aesthetic approach
                - Similar narrative structure
                - Same technical specifications (9:16 aspect ratio, under 60 seconds)
                - Different content to avoid copying
                - Specific shot-by-shot breakdown
                - Audio requirements
                - Character requirements if applicable
                
                Format your response as JSON with 'analysis' and 'plan' fields.""",
                file_contents=file_contents
            )
            
            response = await chat.send_message(message)
            
            # Parse response
            try:
                # Try to parse as JSON first
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # If not JSON, create structured response
                return {
                    "analysis": response[:len(response)//2],
                    "plan": response[len(response)//2:]
                }
                
        except Exception as fallback_error:
            logger.error(f"Both Gemini approaches failed - Official: {str(official_error)} | Fallback: {str(fallback_error)}")
            raise HTTPException(status_code=500, detail=f"Video analysis failed with both approaches: Official library error: {str(official_error)} | Emergentintegrations error: {str(fallback_error)}")

# Background task for video generation
async def generate_video_background(session_id: str, plan: str):
    """Background task for video generation"""
    try:
        # Update status to processing
        await db.video_generations.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": "processing", 
                "progress": 10,
                "estimated_time_remaining": 300  # 5 minutes
            }}
        )
        
        # Simulate video generation process
        # In real implementation, this would call WAN 2.1 and FFmpeg
        for progress in range(10, 100, 10):
            await asyncio.sleep(5)  # Simulate processing time
            await db.video_generations.update_one(
                {"session_id": session_id},
                {"$set": {
                    "progress": progress,
                    "estimated_time_remaining": max(0, 300 - (progress * 3))
                }}
            )
        
        # Simulate final video creation
        await asyncio.sleep(10)
        
        # Generate mock video URL (in real implementation, this would be the actual generated video)
        video_url = f"https://example.com/generated_videos/{session_id}.mp4"
        
        # Update status to completed
        await db.video_generations.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": "completed",
                "progress": 100,
                "video_url": video_url,
                "completed_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=7)
            }}
        )
        
    except Exception as e:
        logger.error(f"Video generation failed: {str(e)}")
        await db.video_generations.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": "failed",
                "error": str(e)
            }}
        )

# API Routes
@api_router.post("/upload-video", response_model=VideoAnalysisResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...),
    character_image: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None),
    user_id: str = Form(...)
):
    """Upload video and optional files for analysis"""
    try:
        session_id = str(uuid.uuid4())
        
        # Validate video file
        if not video_file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="Invalid video file type")
        
        # Save uploaded files
        video_filename = f"{session_id}_sample.mp4"
        video_path = await save_uploaded_file(video_file, video_filename)
        
        character_image_path = None
        if character_image:
            if not character_image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Invalid image file type")
            char_filename = f"{session_id}_character.jpg"
            character_image_path = await save_uploaded_file(character_image, char_filename)
        
        audio_path = None
        if audio_file:
            if not audio_file.content_type.startswith('audio/'):
                raise HTTPException(status_code=400, detail="Invalid audio file type")
            audio_filename = f"{session_id}_audio.mp3"
            audio_path = await save_uploaded_file(audio_file, audio_filename)
        
        # Upload to R2 storage
        r2_video_url = await upload_to_r2(video_path, f"samples/{video_filename}")
        
        r2_image_url = None
        if character_image_path:
            r2_image_url = await upload_to_r2(character_image_path, f"characters/{char_filename}")
        
        r2_audio_url = None
        if audio_path:
            r2_audio_url = await upload_to_r2(audio_path, f"audio/{audio_filename}")
        
        # Analyze video with Gemini
        analysis_result = await analyze_video_with_gemini(
            video_path, character_image_path, audio_path
        )
        
        # Create analysis record
        analysis_record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "session_id": session_id,
            "analysis": analysis_result.get("analysis", ""),
            "plan": analysis_result.get("plan", ""),
            "status": "analyzed",
            "created_at": datetime.utcnow(),
            "sample_video_path": r2_video_url,
            "character_image_path": r2_image_url,
            "audio_path": r2_audio_url
        }
        
        await db.video_analyses.insert_one(analysis_record)
        
        # Clean up temporary files
        if os.path.exists(video_path):
            os.remove(video_path)
        if character_image_path and os.path.exists(character_image_path):
            os.remove(character_image_path)
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        
        return VideoAnalysisResponse(**analysis_record)
        
    except Exception as e:
        logger.error(f"Video upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/modify-plan")
async def modify_plan(request: PlanModificationRequest):
    """Modify the generated plan based on user feedback"""
    try:
        # Get current analysis
        analysis = await db.video_analyses.find_one({"session_id": request.session_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Use stable Gemini model for plan modification
        gemini_key = get_next_gemini_key()
        chat = LlmChat(
            api_key=gemini_key,
            session_id=f"plan_modification_{uuid.uuid4()}",
            system_message=f"""You are a video generation expert. The user has requested modifications to this plan:
            
            ORIGINAL PLAN:
            {analysis['plan']}
            
            ORIGINAL ANALYSIS:
            {analysis['analysis']}
            
            Please modify the plan based on the user's request while maintaining the same structure and format."""
        ).with_model("gemini", "gemini-2.5-flash-preview-04-17")
        
        message = UserMessage(
            text=f"Please modify the video generation plan based on this request: {request.modification_request}"
        )
        
        modified_plan = await chat.send_message(message)
        
        # Update the analysis record
        await db.video_analyses.update_one(
            {"session_id": request.session_id},
            {"$set": {
                "plan": modified_plan,
                "modified_at": datetime.utcnow()
            }}
        )
        
        return {"status": "success", "modified_plan": modified_plan}
        
    except Exception as e:
        logger.error(f"Plan modification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/generate-video")
async def generate_video(request: VideoGenerationRequest, background_tasks: BackgroundTasks):
    """Start video generation process"""
    try:
        # Create generation record
        generation_record = {
            "session_id": request.session_id,
            "status": "queued",
            "progress": 0,
            "approved_plan": request.approved_plan,
            "created_at": datetime.utcnow(),
            "estimated_time_remaining": 300
        }
        
        await db.video_generations.insert_one(generation_record)
        
        # Start background generation task
        background_tasks.add_task(generate_video_background, request.session_id, request.approved_plan)
        
        return {"status": "success", "message": "Video generation started", "session_id": request.session_id}
        
    except Exception as e:
        logger.error(f"Video generation start failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/generation-status/{session_id}")
async def get_generation_status(session_id: str):
    """Get video generation status"""
    try:
        generation = await db.video_generations.find_one({"session_id": session_id})
        if not generation:
            raise HTTPException(status_code=404, detail="Generation not found")
        
        return VideoGenerationStatus(
            session_id=generation["session_id"],
            status=generation["status"],
            progress=generation.get("progress", 0),
            estimated_time_remaining=generation.get("estimated_time_remaining"),
            error=generation.get("error")
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/user-videos/{user_id}")
async def get_user_videos(user_id: str):
    """Get all videos for a user"""
    try:
        # Get all analyses for the user
        analyses = await db.video_analyses.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
        
        # Get generation status for each
        result = []
        for analysis in analyses:
            generation = await db.video_generations.find_one({"session_id": analysis["session_id"]})
            
            video_info = {
                "session_id": analysis["session_id"],
                "created_at": analysis["created_at"],
                "analysis": analysis["analysis"][:200] + "..." if len(analysis["analysis"]) > 200 else analysis["analysis"],
                "status": generation["status"] if generation else "analyzed",
                "progress": generation.get("progress", 0) if generation else 0,
                "video_url": generation.get("video_url") if generation else None
            }
            result.append(video_info)
        
        return {"videos": result}
        
    except Exception as e:
        logger.error(f"User videos fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/create-user")
async def create_user(email: str = Form(...)):
    """Create a new user"""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": email})
        if existing_user:
            return {"user_id": existing_user["id"], "message": "User already exists"}
        
        # Create new user
        user = User(email=email)
        await db.users.insert_one(user.dict())
        
        return {"user_id": user.id, "message": "User created successfully"}
        
    except Exception as e:
        logger.error(f"User creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analysis/{session_id}")
async def get_analysis(session_id: str):
    """Get analysis details for a session"""
    try:
        analysis = await db.video_analyses.find_one({"session_id": session_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Analysis fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)