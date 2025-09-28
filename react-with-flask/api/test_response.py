#!/usr/bin/env python3
"""
Test script to see the full AI response from the Flask API
"""

import requests
import json

def test_ai_response():
    """Test the AI chat and show full response"""
    
    base_url = "http://127.0.0.1:5001"
    
    # Test question about salmon
    payload = {"message": "What are the health benefits of salmon?"}
    
    print("🧪 Testing AI chat response...")
    print(f"📝 Question: {payload['message']}")
    print("\n" + "="*60)
    
    try:
        response = requests.post(
            f"{base_url}/api/ai/chat", 
            json=payload, 
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ SUCCESS! Got AI response:")
            print(f"🤖 AI Response ({len(result.get('ai_response', ''))} characters):")
            print("\n" + "-"*50)
            print(result.get('ai_response', 'No response'))
            print("-"*50)
            
            print(f"\n📊 Full Response Data:")
            print(f"   User Message: {result.get('user_message', 'N/A')}")
            print(f"   Timestamp: {result.get('timestamp', 'N/A')}")
            print(f"   Powered By: {result.get('powered_by', 'N/A')}")
            
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask server")
        print("💡 Make sure to start the server first with: python api.py")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_ai_response()