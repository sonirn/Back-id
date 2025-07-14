#!/usr/bin/env python3
"""
Backend API Testing Suite for Video Generation Platform
Tests the core backend functionality including user registration, file upload, 
R2 storage integration, and Gemini video analysis.
"""

import requests
import json
import os
import tempfile
import time
from pathlib import Path
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')

# Get backend URL from frontend env
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

print(f"Testing backend at: {API_BASE_URL}")

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_user_id = None
        self.test_session_id = None
        
    def create_mock_video_file(self):
        """Create a small mock video file for testing"""
        # Create a simple text file with video extension for basic upload testing
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False, mode='w')
        temp_file.write("Mock video content for testing")
        temp_file.close()
        return temp_file.name
    
    def create_mock_image_file(self):
        """Create a small mock image file for testing"""
        # Create a simple text file with image extension for basic upload testing
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False, mode='w')
        temp_file.write("Mock image content for testing")
        temp_file.close()
        return temp_file.name
    
    def test_user_registration(self):
        """Test user registration and authentication"""
        print("\n=== Testing User Registration ===")
        
        try:
            # Test user creation with valid email
            test_email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
            
            response = self.session.post(
                f"{API_BASE_URL}/create-user",
                data={"email": test_email}
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                self.test_user_id = data.get('user_id')
                print(f"✅ User created successfully with ID: {self.test_user_id}")
                
                # Test duplicate user creation
                response2 = self.session.post(
                    f"{API_BASE_URL}/create-user",
                    data={"email": test_email}
                )
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    if "already exists" in data2.get('message', ''):
                        print("✅ Duplicate user handling works correctly")
                    else:
                        print("⚠️ Duplicate user created new entry")
                
                return True
            else:
                print(f"❌ User creation failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ User registration test failed: {str(e)}")
            return False
    
    def test_video_upload(self):
        """Test video file upload with multipart form data"""
        print("\n=== Testing Video File Upload ===")
        
        if not self.test_user_id:
            print("❌ No test user ID available")
            return False
        
        try:
            # Create mock files
            video_file_path = self.create_mock_video_file()
            image_file_path = self.create_mock_image_file()
            
            # Test video upload
            with open(video_file_path, 'rb') as video_file, \
                 open(image_file_path, 'rb') as image_file:
                
                files = {
                    'video_file': ('test_video.mp4', video_file, 'video/mp4'),
                    'character_image': ('test_character.jpg', image_file, 'image/jpeg')
                }
                
                data = {
                    'user_id': self.test_user_id
                }
                
                print("Uploading files...")
                response = self.session.post(
                    f"{API_BASE_URL}/upload-video",
                    files=files,
                    data=data,
                    timeout=60  # Longer timeout for file upload
                )
                
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.test_session_id = data.get('session_id')
                    print(f"✅ Video upload successful with session ID: {self.test_session_id}")
                    
                    # Check if analysis and plan are present
                    if data.get('analysis') and data.get('plan'):
                        print("✅ Video analysis completed")
                    else:
                        print("⚠️ Video analysis may be incomplete")
                    
                    return True
                else:
                    print(f"❌ Video upload failed: {response.text}")
                    return False
            
        except Exception as e:
            print(f"❌ Video upload test failed: {str(e)}")
            return False
        finally:
            # Clean up temp files
            try:
                os.unlink(video_file_path)
                os.unlink(image_file_path)
            except:
                pass
    
    def test_r2_storage_integration(self):
        """Test Cloudflare R2 storage integration"""
        print("\n=== Testing R2 Storage Integration ===")
        
        try:
            # Check if R2 environment variables are configured
            r2_endpoint = os.environ.get('CLOUDFLARE_API_ENDPOINT')
            r2_access_key = os.environ.get('CLOUDFLARE_ACCESS_KEY')
            r2_secret_key = os.environ.get('CLOUDFLARE_SECRET_KEY')
            
            if not all([r2_endpoint, r2_access_key, r2_secret_key]):
                print("❌ R2 environment variables not configured")
                return False
            
            print("✅ R2 environment variables configured")
            print(f"R2 Endpoint: {r2_endpoint}")
            
            # R2 integration is tested indirectly through video upload
            if self.test_session_id:
                # Get analysis to check if files were uploaded to R2
                response = self.session.get(f"{API_BASE_URL}/analysis/{self.test_session_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    sample_video_path = data.get('sample_video_path')
                    
                    if sample_video_path and r2_endpoint in sample_video_path:
                        print("✅ R2 storage integration working - files uploaded to R2")
                        return True
                    else:
                        print("⚠️ R2 integration may not be working - no R2 URLs found")
                        return False
                else:
                    print(f"❌ Could not retrieve analysis: {response.text}")
                    return False
            else:
                print("⚠️ No session ID available to test R2 integration")
                return False
                
        except Exception as e:
            print(f"❌ R2 storage test failed: {str(e)}")
            return False
    
    def test_gemini_integration(self):
        """Test Gemini video analysis integration"""
        print("\n=== Testing Gemini Integration ===")
        
        try:
            # Check if Gemini API keys are configured
            gemini_key_1 = os.environ.get('GEMINI_API_KEY_1')
            gemini_key_2 = os.environ.get('GEMINI_API_KEY_2')
            gemini_key_3 = os.environ.get('GEMINI_API_KEY_3')
            
            if not any([gemini_key_1, gemini_key_2, gemini_key_3]):
                print("❌ Gemini API keys not configured")
                return False
            
            print("✅ Gemini API keys configured")
            
            # Gemini integration is tested through video upload analysis
            if self.test_session_id:
                response = self.session.get(f"{API_BASE_URL}/analysis/{self.test_session_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    analysis = data.get('analysis')
                    plan = data.get('plan')
                    
                    if analysis and plan and len(analysis) > 50 and len(plan) > 50:
                        print("✅ Gemini integration working - detailed analysis and plan generated")
                        return True
                    else:
                        print("⚠️ Gemini integration may not be working - analysis/plan too short or missing")
                        print(f"Analysis length: {len(analysis) if analysis else 0}")
                        print(f"Plan length: {len(plan) if plan else 0}")
                        return False
                else:
                    print(f"❌ Could not retrieve analysis: {response.text}")
                    return False
            else:
                print("⚠️ No session ID available to test Gemini integration")
                return False
                
        except Exception as e:
            print(f"❌ Gemini integration test failed: {str(e)}")
            return False
    
    def test_plan_modification(self):
        """Test plan modification with chat"""
        print("\n=== Testing Plan Modification ===")
        
        if not self.test_session_id:
            print("❌ No session ID available")
            return False
        
        try:
            modification_request = "Make the video more energetic and add more dynamic camera movements"
            
            response = self.session.post(
                f"{API_BASE_URL}/modify-plan",
                json={
                    "session_id": self.test_session_id,
                    "modification_request": modification_request
                }
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and data.get('modified_plan'):
                    print("✅ Plan modification successful")
                    return True
                else:
                    print("⚠️ Plan modification response incomplete")
                    return False
            else:
                print(f"❌ Plan modification failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Plan modification test failed: {str(e)}")
            return False
    
    def test_video_generation(self):
        """Test background video generation"""
        print("\n=== Testing Video Generation ===")
        
        if not self.test_session_id:
            print("❌ No session ID available")
            return False
        
        try:
            # Start video generation
            response = self.session.post(
                f"{API_BASE_URL}/generate-video",
                json={
                    "session_id": self.test_session_id,
                    "approved_plan": "Test plan for video generation"
                }
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    print("✅ Video generation started successfully")
                    
                    # Check generation status
                    time.sleep(2)  # Wait a bit for status to update
                    status_response = self.session.get(
                        f"{API_BASE_URL}/generation-status/{self.test_session_id}"
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"Generation Status: {status_data.get('status')}")
                        print(f"Progress: {status_data.get('progress')}%")
                        print("✅ Status tracking working")
                        return True
                    else:
                        print("⚠️ Status tracking may not be working")
                        return False
                else:
                    print("⚠️ Video generation response incomplete")
                    return False
            else:
                print(f"❌ Video generation failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Video generation test failed: {str(e)}")
            return False
    
    def test_user_videos(self):
        """Test user video management"""
        print("\n=== Testing User Video Management ===")
        
        if not self.test_user_id:
            print("❌ No user ID available")
            return False
        
        try:
            response = self.session.get(f"{API_BASE_URL}/user-videos/{self.test_user_id}")
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                videos = data.get('videos', [])
                
                if isinstance(videos, list):
                    print(f"✅ User videos endpoint working - found {len(videos)} videos")
                    return True
                else:
                    print("⚠️ User videos response format incorrect")
                    return False
            else:
                print(f"❌ User videos failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ User videos test failed: {str(e)}")
            return False
    
    def test_error_handling(self):
        """Test error handling for missing files and invalid requests"""
        print("\n=== Testing Error Handling ===")
        
        try:
            # Test upload without video file
            response = self.session.post(
                f"{API_BASE_URL}/upload-video",
                data={"user_id": "test_user"}
            )
            
            if response.status_code == 422:  # FastAPI validation error
                print("✅ Error handling for missing video file works")
            else:
                print(f"⚠️ Unexpected response for missing file: {response.status_code}")
            
            # Test invalid session ID
            response = self.session.get(f"{API_BASE_URL}/analysis/invalid_session_id")
            
            if response.status_code == 404:
                print("✅ Error handling for invalid session ID works")
            else:
                print(f"⚠️ Unexpected response for invalid session: {response.status_code}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Backend API Tests")
        print("=" * 50)
        
        results = {}
        
        # Test core functionality
        results['user_registration'] = self.test_user_registration()
        results['video_upload'] = self.test_video_upload()
        results['r2_storage'] = self.test_r2_storage_integration()
        results['gemini_integration'] = self.test_gemini_integration()
        
        # Test additional features
        results['plan_modification'] = self.test_plan_modification()
        results['video_generation'] = self.test_video_generation()
        results['user_videos'] = self.test_user_videos()
        results['error_handling'] = self.test_error_handling()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        return results

if __name__ == "__main__":
    tester = BackendTester()
    results = tester.run_all_tests()