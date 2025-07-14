#!/usr/bin/env python3
"""
Test Gemini integration with actual video file processing
"""

import os
import requests
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

def create_minimal_mp4():
    """Create a minimal valid MP4 file for testing"""
    # This is a minimal MP4 header that should be recognized as a valid video file
    mp4_header = bytes([
        0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70,  # ftyp box
        0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00,  # isom brand
        0x69, 0x73, 0x6F, 0x6D, 0x69, 0x73, 0x6F, 0x32,  # compatible brands
        0x61, 0x76, 0x63, 0x31, 0x6D, 0x70, 0x34, 0x31,  # avc1, mp41
        0x00, 0x00, 0x00, 0x08, 0x66, 0x72, 0x65, 0x65   # free box
    ])
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_file.write(mp4_header)
    temp_file.close()
    return temp_file.name

def test_gemini_with_real_video():
    """Test Gemini integration with a minimal but valid MP4 file"""
    print("🎬 Testing Gemini Integration with Valid MP4 File")
    print("=" * 55)
    
    try:
        # Create a test user first
        print("1. Creating test user...")
        user_response = requests.post(
            f"{API_BASE_URL}/create-user",
            data={"email": "gemini_test@example.com"}
        )
        
        if user_response.status_code != 200:
            print(f"❌ Failed to create user: {user_response.text}")
            return False
        
        user_id = user_response.json()['user_id']
        print(f"✅ User created: {user_id}")
        
        # Create a minimal valid MP4 file
        print("2. Creating minimal valid MP4 file...")
        video_file_path = create_minimal_mp4()
        print(f"✅ MP4 file created: {video_file_path}")
        
        # Test upload with valid MP4
        print("3. Testing upload with valid MP4...")
        with open(video_file_path, 'rb') as video_file:
            files = {
                'video_file': ('test_video.mp4', video_file, 'video/mp4')
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
                    print("⚠️ File format issue - Gemini cannot process this MP4 format")
                elif "quota" in error_text.lower():
                    print("⚠️ API quota issue")
                else:
                    print("⚠️ Other Gemini processing error")
                
                return False
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    finally:
        # Clean up
        try:
            if 'video_file_path' in locals():
                os.unlink(video_file_path)
        except:
            pass

if __name__ == "__main__":
    success = test_gemini_with_real_video()
    
    print(f"\n📊 RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    if not success:
        print("\n💡 RECOMMENDATIONS:")
        print("1. Gemini may require specific video formats/codecs")
        print("2. File size limitations may apply")
        print("3. Consider using image files for initial testing")
        print("4. Check Gemini API documentation for supported formats")