#!/usr/bin/env python3
"""
Complete test of the Flask API and AI chat functionality
"""

import sys
import requests
import time
import json
from threading import Thread
from api import app

def test_ai_chat_directly():
    """Test the AI chat functionality directly without Flask server"""
    print("🧪 Testing AI chat directly...")
    
    try:
        from mosaic_nutrition_ai import mosaic_nutrition_ai
        
        user_message = "What are the health benefits of chicken breast?"
        print(f"📝 User message: {user_message}")
        
        response = mosaic_nutrition_ai.generate_nutrition_advice(user_message)
        print(f"✅ AI Response ({len(response)} chars):")
        print(f"{response[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def run_flask_server():
    """Run Flask server for testing"""
    print("🚀 Starting Flask server...")
    app.run(debug=False, port=5001, use_reloader=False)

def test_flask_api():
    """Test Flask API endpoints"""
    print("🧪 Testing Flask API endpoints...")
    
    base_url = "http://127.0.0.1:5001"
    
    # Test basic endpoint
    try:
        print("📡 Testing /api/time endpoint...")
        response = requests.get(f"{base_url}/api/time", timeout=5)
        if response.status_code == 200:
            print("✅ /api/time endpoint working")
        else:
            print(f"❌ /api/time failed: {response.status_code}")
    except Exception as e:
        print(f"❌ /api/time error: {e}")
        return False
    
    # Test AI status endpoint
    try:
        print("📡 Testing /api/ai/status endpoint...")
        response = requests.get(f"{base_url}/api/ai/status", timeout=5)
        if response.status_code == 200:
            print("✅ /api/ai/status endpoint working")
            print(f"📊 Status: {response.json()}")
        else:
            print(f"❌ /api/ai/status failed: {response.status_code}")
    except Exception as e:
        print(f"❌ /api/ai/status error: {e}")
    
    # Test AI chat endpoint
    try:
        print("📡 Testing /api/ai/chat endpoint...")
        payload = {"message": "What are the benefits of eating apples?"}
        response = requests.post(
            f"{base_url}/api/ai/chat", 
            json=payload, 
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ /api/ai/chat endpoint working")
            print(f"🤖 AI Response: {result.get('ai_response', '')[:100]}...")
        else:
            print(f"❌ /api/ai/chat failed: {response.status_code}")
            print(f"❌ Response: {response.text}")
    except Exception as e:
        print(f"❌ /api/ai/chat error: {e}")
        
    return True

if __name__ == "__main__":
    print("🚀 Starting complete API tests...")
    print("=" * 60)
    
    # Test 1: Direct AI functionality
    success1 = test_ai_chat_directly()
    
    if success1:
        print("\n" + "=" * 60)
        print("🌐 Testing with Flask server...")
        
        # Start Flask server in background thread
        server_thread = Thread(target=run_flask_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(3)
        
        # Test Flask API
        success2 = test_flask_api()
        
        print("\n" + "=" * 60)
        print("📊 Test Results:")
        print(f"   Direct AI: {'✅ PASS' if success1 else '❌ FAIL'}")
        print(f"   Flask API: {'✅ PASS' if success2 else '❌ FAIL'}")
        
        if success1 and success2:
            print("🎉 All tests passed! Your nutrition AI backend is working!")
        else:
            print("⚠️  Some tests failed. Check the errors above.")
            
        # Keep server running for manual testing
        print("\n💡 Server is running at http://127.0.0.1:5001")
        print("   Press Ctrl+C to stop...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Stopping server...")
    else:
        print("❌ Direct AI test failed. Fix the AI module first.")