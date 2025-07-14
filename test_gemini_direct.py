#!/usr/bin/env python3
"""
Direct Gemini API Test - Test API keys and model availability
"""

import os
import asyncio
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage
import uuid

# Load environment variables
load_dotenv('/app/backend/.env')

# Get API keys
GEMINI_API_KEYS = [
    os.environ.get('GEMINI_API_KEY_1'),
    os.environ.get('GEMINI_API_KEY_2'),
    os.environ.get('GEMINI_API_KEY_3')
]

async def test_gemini_api_key(api_key, key_number):
    """Test a single Gemini API key with text-only request"""
    print(f"\n=== Testing Gemini API Key {key_number} ===")
    
    if not api_key:
        print(f"❌ API Key {key_number} not configured")
        return False
    
    try:
        # Test with simple text-only request (no files)
        chat = LlmChat(
            api_key=api_key,
            session_id=f"test_session_{uuid.uuid4()}",
            system_message="You are a helpful assistant."
        ).with_model("gemini", "gemini-2.5-flash")
        
        message = UserMessage(
            text="Hello! Please respond with 'API key working' if you can process this message."
        )
        
        print(f"Testing API key {key_number} with simple text request...")
        response = await chat.send_message(message)
        
        print(f"✅ API Key {key_number}: SUCCESS")
        print(f"Response: {response[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ API Key {key_number}: FAILED")
        print(f"Error: {str(e)}")
        return False

async def test_gemini_with_file():
    """Test Gemini with a simple file to check file processing capability"""
    print(f"\n=== Testing Gemini File Processing ===")
    
    # Use the first working API key
    working_key = None
    for i, key in enumerate(GEMINI_API_KEYS):
        if key and await test_gemini_api_key(key, i+1):
            working_key = key
            break
    
    if not working_key:
        print("❌ No working API keys found")
        return False
    
    try:
        # Create a simple text file for testing
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test text file for Gemini processing.")
            temp_file_path = f.name
        
        from emergentintegrations.llm.chat import FileContentWithMimeType
        
        chat = LlmChat(
            api_key=working_key,
            session_id=f"file_test_{uuid.uuid4()}",
            system_message="You are a helpful assistant that can analyze files."
        ).with_model("gemini", "gemini-2.5-flash")
        
        file_content = FileContentWithMimeType(
            file_path=temp_file_path,
            mime_type="text/plain"
        )
        
        message = UserMessage(
            text="Please analyze this text file and tell me what it contains.",
            file_contents=[file_content]
        )
        
        print("Testing file processing capability...")
        response = await chat.send_message(message)
        
        print("✅ File processing: SUCCESS")
        print(f"Response: {response[:200]}...")
        
        # Clean up
        os.unlink(temp_file_path)
        return True
        
    except Exception as e:
        print("❌ File processing: FAILED")
        print(f"Error: {str(e)}")
        return False

async def main():
    print("🔍 Direct Gemini API Testing")
    print("=" * 50)
    
    # Test all API keys
    working_keys = 0
    for i, key in enumerate(GEMINI_API_KEYS):
        if await test_gemini_api_key(key, i+1):
            working_keys += 1
    
    print(f"\n📊 Results: {working_keys}/{len(GEMINI_API_KEYS)} API keys working")
    
    if working_keys > 0:
        print("✅ At least one API key is functional")
        
        # Test file processing
        await test_gemini_with_file()
    else:
        print("❌ No API keys are working")
        print("❌ This explains why the video analysis is failing")

if __name__ == "__main__":
    asyncio.run(main())