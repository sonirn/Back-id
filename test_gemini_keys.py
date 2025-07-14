#!/usr/bin/env python3
"""
Test Gemini API keys directly to check quota availability
"""

import os
import asyncio
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Load environment variables
load_dotenv('/app/backend/.env')

# Get Gemini API keys
GEMINI_API_KEYS = [
    os.environ.get('GEMINI_API_KEY_1'),
    os.environ.get('GEMINI_API_KEY_2'),
    os.environ.get('GEMINI_API_KEY_3')
]

async def test_gemini_key(api_key, key_number):
    """Test a single Gemini API key with a simple text request"""
    print(f"\n=== Testing Gemini API Key {key_number} ===")
    
    if not api_key:
        print(f"❌ Key {key_number}: Not configured")
        return False
    
    try:
        # Initialize chat with gemini-2.5-flash model
        chat = LlmChat(
            api_key=api_key,
            session_id=f"test_session_{key_number}",
            system_message="You are a helpful assistant. Respond briefly."
        ).with_model("gemini", "gemini-2.5-flash")
        
        # Send a simple test message
        message = UserMessage(text="Hello, can you respond with 'API key working'?")
        
        print(f"🔄 Testing key {key_number}...")
        response = await chat.send_message(message)
        
        if response and len(response) > 0:
            print(f"✅ Key {key_number}: Working! Response: {response[:100]}...")
            return True
        else:
            print(f"❌ Key {key_number}: Empty response")
            return False
            
    except Exception as e:
        error_str = str(e)
        print(f"❌ Key {key_number}: Failed - {error_str[:200]}...")
        
        # Check for specific error types
        if "quota" in error_str.lower():
            print(f"⚠️ Key {key_number}: Quota exhausted")
        elif "invalid" in error_str.lower() or "unauthorized" in error_str.lower():
            print(f"⚠️ Key {key_number}: Invalid or unauthorized")
        elif "rate" in error_str.lower():
            print(f"⚠️ Key {key_number}: Rate limited")
        
        return False

async def test_all_keys():
    """Test all Gemini API keys"""
    print("🔑 Testing Gemini API Keys for Quota Availability")
    print("=" * 60)
    
    results = []
    
    for i, key in enumerate(GEMINI_API_KEYS, 1):
        result = await test_gemini_key(key, i)
        results.append(result)
        
        # Small delay between tests to avoid rate limiting
        if i < len(GEMINI_API_KEYS):
            await asyncio.sleep(2)
    
    # Summary
    working_keys = sum(results)
    total_keys = len([k for k in GEMINI_API_KEYS if k])
    
    print(f"\n📊 SUMMARY: {working_keys}/{total_keys} API keys are working")
    
    if working_keys > 0:
        print("✅ At least one API key has quota available")
        print("✅ Gemini integration should work with text-only requests")
    else:
        print("❌ No API keys have quota available")
        print("❌ All keys may be exhausted or invalid")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_all_keys())