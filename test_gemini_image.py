#!/usr/bin/env python3
"""
Test Gemini integration with image file to isolate the issue
"""

import os
import requests
import tempfile
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

def create_simple_image():
    """Create a simple valid image file for testing"""
    # Create a simple 100x100 red image
    img = Image.new('RGB', (100, 100), color='red')
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    img.save(temp_file.name, 'JPEG')
    return temp_file.name

def test_gemini_with_image():
    """Test Gemini integration with a simple image file"""
    print("🖼️ Testing Gemini Integration with Simple Image File")
    print("=" * 55)
    
    try:
        # Create a test user first
        print("1. Creating test user...")
        user_response = requests.post(
            f"{API_BASE_URL}/create-user",
            data={"email": "gemini_image_test@example.com"}
        )
        
        if user_response.status_code != 200:
            print(f"❌ Failed to create user: {user_response.text}")
            return False
        
        user_id = user_response.json()['user_id']
        print(f"✅ User created: {user_id}")
        
        # Create a simple image file
        print("2. Creating simple image file...")
        image_file_path = create_simple_image()
        print(f"✅ Image file created: {image_file_path}")
        
        # Test upload with image only (no video)
        print("3. Testing upload with image as character_image...")
        with open(image_file_path, 'rb') as image_file:
            # Create a minimal text file as video (since video is required)
            video_content = b"fake video content for testing"
            
            files = {
                'video_file': ('test_video.mp4', video_content, 'video/mp4'),
                'character_image': ('test_character.jpg', image_file, 'image/jpeg')
            }
            
            data = {
                'user_id': user_id
            }
            
            response = requests.post(
                f"{API_BASE_URL}/upload-video",
                files=files,
                data=data,
                timeout=60
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Upload successful!")
                print(f"Session ID: {result.get('session_id')}")
                print(f"Analysis length: {len(result.get('analysis', ''))}")
                print(f"Plan length: {len(result.get('plan', ''))}")
                
                if result.get('analysis') and result.get('plan'):
                    print("✅ Gemini analysis completed successfully!")
                    return True
                else:
                    print("⚠️ Upload successful but analysis incomplete")
                    return False
                    
            else:
                error_text = response.text
                print(f"❌ Upload failed: {error_text}")
                
                # Analyze the error
                if "Unable to process input image" in error_text:
                    print("⚠️ Image processing issue")
                elif "quota" in error_text.lower():
                    print("⚠️ API quota issue")
                elif "internal error" in error_text.lower():
                    print("⚠️ Internal server error - may be file format related")
                else:
                    print("⚠️ Other Gemini processing error")
                
                return False
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    finally:
        # Clean up
        try:
            if 'image_file_path' in locals():
                os.unlink(image_file_path)
        except:
            pass

if __name__ == "__main__":
    success = test_gemini_with_image()
    
    print(f"\n📊 RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    if not success:
        print("\n💡 ANALYSIS:")
        print("- Gemini API keys are working (confirmed earlier)")
        print("- Issue appears to be with file processing in emergentintegrations library")
        print("- May need to investigate FileContentWithMimeType usage")
        print("- Could be related to file upload/temporary file handling")