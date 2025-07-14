#!/usr/bin/env python3
"""
Test video analysis with text-only description (no file upload)
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

def test_text_only_analysis():
    """Test video analysis with text description only"""
    print("📝 Testing Text-Only Video Analysis")
    print("=" * 40)
    
    try:
        # Create a test user first
        print("1. Creating test user...")
        user_response = requests.post(
            f"{API_BASE_URL}/create-user",
            data={"email": "text_analysis_test@example.com"}
        )
        
        if user_response.status_code != 200:
            print(f"❌ Failed to create user: {user_response.text}")
            return False
        
        user_id = user_response.json()['user_id']
        print(f"✅ User created: {user_id}")
        
        # Create a simple text file as video content
        print("2. Creating text description as video content...")
        video_description = """
        This is a sample video description for testing:
        
        The video shows a person walking through a beautiful park on a sunny day. 
        The person is wearing casual clothes - jeans and a light blue t-shirt.
        The park has green trees, a paved walking path, and there are birds chirping in the background.
        The video is about 30 seconds long and shows the person walking from left to right across the frame.
        The lighting is natural sunlight filtering through the trees.
        The camera follows the person smoothly as they walk.
        The overall mood is peaceful and relaxing.
        
        This would be converted to a 9:16 aspect ratio video for mobile viewing.
        """
        
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(video_description)
            temp_file_path = f.name
        
        print(f"✅ Text description file created: {temp_file_path}")
        
        # Test upload with text file as video
        print("3. Testing upload with text description...")
        with open(temp_file_path, 'rb') as text_file:
            files = {
                'video_file': ('sample_video.mp4', text_file, 'video/mp4')
            }
            
            data = {
                'user_id': user_id
            }
            
            response = requests.post(
                f"{API_BASE_URL}/upload-video",
                files=files,
                data=data,
                timeout=120
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Upload successful!")
                print(f"Session ID: {result.get('session_id')}")
                print(f"Analysis: {result.get('analysis', 'No analysis')[:200]}...")
                print(f"Plan: {result.get('plan', 'No plan')[:200]}...")
                
                if result.get('analysis') and result.get('plan'):
                    print("✅ Analysis and plan generation successful!")
                    return True
                else:
                    print("⚠️ Upload successful but analysis incomplete")
                    return False
                    
            else:
                error_text = response.text
                print(f"❌ Upload failed: {error_text}")
                return False
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    finally:
        # Clean up
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
        except:
            pass

if __name__ == "__main__":
    success = test_text_only_analysis()
    
    print(f"\n📊 RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    if success:
        print("✅ Text-only video analysis is working!")
        print("🎯 RECOMMENDATION: Use text-based analysis for now while debugging file upload issues")
    else:
        print("❌ Even text-only analysis failed")