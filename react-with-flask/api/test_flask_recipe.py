#!/usr/bin/env python3
"""
Test Flask API with recipe request
"""

import requests
import json
import sys

def test_recipe_api():
    """Test the recipe API request"""
    
    base_url = "http://127.0.0.1:5001"
    
    # Test recipe question
    payload = {"message": "Can you create a protein-packed breakfast recipe with eggs and oatmeal? Include the macros please!"}
    
    print("🧪 Testing Flask API with recipe request...")
    print(f"📝 Question: {payload['message']}")
    print("\n" + "="*70)
    
    try:
        print("📡 Sending request to Flask API...")
        response = requests.post(
            f"{base_url}/api/ai/chat", 
            json=payload, 
            timeout=45,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ SUCCESS! Got recipe response from Flask API:")
            print(f"🤖 AI Response ({len(result.get('ai_response', ''))} characters):")
            print("\n" + "-"*70)
            print(result.get('ai_response', 'No response'))
            print("-"*70)
            
            print(f"\n📊 Response metadata:")
            print(f"   Powered by: {result.get('powered_by', 'N/A')}")
            print(f"   Timestamp: {result.get('timestamp', 'N/A')}")
            
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask server")
        print("💡 Make sure to start the server first with: python api.py")
    except requests.exceptions.Timeout:
        print("❌ Request timed out (server might be processing)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_recipe_api()