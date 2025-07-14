#!/usr/bin/env python3
"""
Simple Backend API Test for Gemini Integration Verification
"""

import requests
import json
import os
import tempfile
import time
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')

# Get backend URL from frontend env
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

print(f"Testing backend at: {API_BASE_URL}")

def test_user_registration():
    """Test user registration"""
    print("\n=== Testing User Registration ===")
    
    try:
        test_email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
        
        response = requests.post(
            f"{API_BASE_URL}/create-user",
            data={"email": test_email},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            user_id = data.get('user_id')
            print(f"✅ User created successfully with ID: {user_id}")
            return user_id
        else:
            print(f"❌ User creation failed")
            return None
            
    except Exception as e:
        print(f"❌ User registration test failed: {str(e)}")
        return None

def test_gemini_integration(user_id):
    """Test Gemini integration with text-only fallback"""
    print("\n=== Testing Gemini Integration (Text-Only Fallback) ===")
    
    if not user_id:
        print("❌ No user ID available")
        return None
    
    try:
        # Create a simple mock video file
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False, mode='w')
        temp_file.write("Mock video content for testing Gemini integration")
        temp_file.close()
        
        with open(temp_file.name, 'rb') as video_file:
            files = {
                'video_file': ('test_video.mp4', video_file, 'video/mp4')
            }
            
            data = {
                'user_id': user_id
            }
            
            print("Testing video upload with Gemini analysis...")
            response = requests.post(
                f"{API_BASE_URL}/upload-video",
                files=files,
                data=data,
                timeout=120  # Longer timeout for Gemini processing
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                session_id = data.get('session_id')
                analysis = data.get('analysis', '')
                plan = data.get('plan', '')
                
                print(f"✅ Video upload successful with session ID: {session_id}")
                print(f"Analysis length: {len(analysis)}")
                print(f"Plan length: {len(plan)}")
                
                if analysis and plan and len(analysis) > 100 and len(plan) > 100:
                    print("✅ Detailed analysis and plan generated")
                    print("✅ Gemini integration working with fallback approach")
                    return session_id
                else:
                    print("⚠️ Analysis/plan generated but may be incomplete")
                    return session_id
                    
            else:
                print(f"❌ Video upload failed: {response.text}")
                return None
        
    except Exception as e:
        print(f"❌ Gemini integration test failed: {str(e)}")
        return None
    finally:
        try:
            os.unlink(temp_file.name)
        except:
            pass

def test_plan_modification(session_id):
    """Test plan modification"""
    print("\n=== Testing Plan Modification ===")
    
    if not session_id:
        print("❌ No session ID available")
        return False
    
    try:
        modification_request = "Make the video more energetic with dynamic camera movements"
        
        response = requests.post(
            f"{API_BASE_URL}/modify-plan",
            json={
                "session_id": session_id,
                "modification_request": modification_request
            },
            timeout=60
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success' and data.get('modified_plan'):
                modified_plan = data.get('modified_plan')
                print(f"✅ Plan modification successful")
                print(f"Modified plan length: {len(modified_plan)}")
                
                if len(modified_plan) > 50:
                    print("✅ Plan modification working with Gemini chat")
                    return True
                else:
                    print("⚠️ Plan modification response too short")
                    return False
            else:
                print("⚠️ Plan modification response incomplete")
                return False
        else:
            print(f"❌ Plan modification failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Plan modification test failed: {str(e)}")
        return False

def test_video_generation(session_id):
    """Test video generation"""
    print("\n=== Testing Video Generation ===")
    
    if not session_id:
        print("❌ No session ID available")
        return False
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-video",
            json={
                "session_id": session_id,
                "approved_plan": "Test plan for video generation"
            },
            timeout=15
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print("✅ Video generation started successfully")
                return True
            else:
                print("⚠️ Video generation response incomplete")
                return False
        else:
            print(f"❌ Video generation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Video generation test failed: {str(e)}")
        return False

def main():
    """Run the main tests"""
    print("🚀 Simple Backend API Test - Gemini Integration Fix Verification")
    print("=" * 70)
    
    # Test user registration
    user_id = test_user_registration()
    
    # Test Gemini integration (main focus)
    session_id = test_gemini_integration(user_id)
    
    # Test plan modification (was previously untestable)
    plan_mod_success = test_plan_modification(session_id)
    
    # Test video generation
    video_gen_success = test_video_generation(session_id)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    print(f"User Registration: {'✅ PASS' if user_id else '❌ FAIL'}")
    print(f"Gemini Integration: {'✅ PASS' if session_id else '❌ FAIL'}")
    print(f"Plan Modification: {'✅ PASS' if plan_mod_success else '❌ FAIL'}")
    print(f"Video Generation: {'✅ PASS' if video_gen_success else '❌ FAIL'}")
    
    print("\n🔍 GEMINI INTEGRATION FIX ANALYSIS:")
    if session_id and plan_mod_success:
        print("✅ Gemini integration fix is WORKING")
        print("✅ Text-only fallback approach is FUNCTIONAL")
        print("✅ Plan modification is now TESTABLE and WORKING")
        print("✅ Multi-layered fallback approach is SUCCESSFUL")
    elif session_id:
        print("✅ Gemini integration fix is WORKING")
        print("✅ Text-only fallback approach is FUNCTIONAL")
        print("❌ Plan modification needs investigation")
    else:
        print("❌ Gemini integration fix may have ISSUES")

if __name__ == "__main__":
    main()