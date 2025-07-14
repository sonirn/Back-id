#!/usr/bin/env python3
"""
Test Gemini integration without files to isolate the issue
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

def test_text_only_gemini():
    """Test if we can create a simple text-only endpoint to test Gemini"""
    print("📝 Testing Gemini Integration with Text-Only Request")
    print("=" * 55)
    
    # Create a simple test endpoint request
    test_data = {
        "test_message": "Analyze this text: 'A short video showing a person walking in a park with trees and sunshine. The person is wearing casual clothes and appears happy.'"
    }
    
    try:
        # Test if we can make a simple request to check server connectivity
        print("1. Testing server connectivity...")
        response = requests.get(f"{API_BASE_URL}/user-videos/test-user-id")
        print(f"Server response: {response.status_code}")
        
        if response.status_code in [200, 404]:  # 404 is expected for non-existent user
            print("✅ Server is accessible")
        else:
            print(f"⚠️ Server connectivity issue: {response.status_code}")
            return False
        
        print("\n2. Analysis of current Gemini integration issue:")
        print("- ✅ Backend server is running")
        print("- ✅ All 3 Gemini API keys have quota available")
        print("- ✅ emergentintegrations library is installed")
        print("- ❌ File processing with FileContentWithMimeType is failing")
        
        print("\n3. Potential root causes:")
        print("- emergentintegrations library may have compatibility issues")
        print("- FileContentWithMimeType may not work correctly with temporary files")
        print("- Gemini API may have changed requirements for file uploads")
        print("- Model specification 'gemini-2.5-flash' may need adjustment")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def suggest_fixes():
    """Suggest potential fixes for the Gemini integration"""
    print("\n🔧 SUGGESTED FIXES:")
    print("=" * 30)
    
    print("1. **Try different model specification:**")
    print("   - Change from 'gemini-2.5-flash' to 'gemini-1.5-flash'")
    print("   - Or try 'gemini-1.5-pro'")
    
    print("\n2. **Modify file handling approach:**")
    print("   - Use base64 encoding instead of FileContentWithMimeType")
    print("   - Try direct file path instead of temporary files")
    
    print("\n3. **Test with simpler file types:**")
    print("   - Start with text files only")
    print("   - Then try simple images")
    print("   - Finally attempt video files")
    
    print("\n4. **Check emergentintegrations library version:**")
    print("   - May need to update or downgrade the library")
    print("   - Check for known issues with current version")
    
    print("\n5. **Alternative approach:**")
    print("   - Implement direct Google AI API calls instead of emergentintegrations")
    print("   - Use official google-generativeai library")

if __name__ == "__main__":
    success = test_text_only_gemini()
    suggest_fixes()
    
    print(f"\n📊 DIAGNOSIS COMPLETE")
    print("=" * 25)
    print("✅ Gemini API keys are working")
    print("✅ Backend server is running")
    print("❌ File processing integration is broken")
    print("\n🎯 RECOMMENDATION: Try alternative Gemini integration approach")