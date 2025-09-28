#!/usr/bin/env python3
"""
Standalone test for MosaicML client without Flask dependencies
This will help isolate if the issue is with the AI client or Flask integration
"""

import sys
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_mosaicml_direct():
    """Test MosaicML API directly without any Flask dependencies"""
    
    print("🧪 Testing MosaicML API directly...")
    
    api_key = os.getenv("OPENAI_KEY")
    
    try:
        print("⏳ Initializing OpenAI client...")
        client = OpenAI(
            api_key=api_key,
            timeout=30.0
        )
        print("✅ Client initialized successfully")
        
        print("⏳ Making API call...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful nutrition assistant."},
                {"role": "user", "content": "What are the health benefits of eating apples?"}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ API call successful!")
        print(f"📝 Response ({len(result)} chars): {result[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"❌ Error type: {type(e)}")
        return False

def test_nutrition_ai_without_flask():
    """Test the nutrition AI logic without Flask circular dependency"""
    
    print("\n🧪 Testing nutrition AI logic without Flask...")
    
    # Simple version that doesn't call Flask API
    api_key = os.getenv("OPENAI_KEY")
    
    try:
        client = OpenAI(api_key=api_key, timeout=30.0)
        
        user_message = "I want to know about the nutrition in chicken breast"
        
        # Mock nutrition data (what we'd normally get from USDA)
        mock_nutrition_data = """
Chicken breast:
• Calories: 165 per 100g
• Protein: 31g
• Carbs: 0g
• Fat: 3.6g
• Fiber: 0g
"""
        
        system_prompt = """You are a professional nutrition expert and registered dietitian.
        
Key guidelines:
- Always use the provided USDA nutrition data when available
- Give specific, actionable advice
- Be encouraging and supportive  
- Focus on practical meal planning and healthy choices
- If asked about medical conditions, recommend consulting healthcare providers

Respond in a helpful, conversational tone."""

        user_prompt = f"""User question: {user_message}

Real USDA Nutrition Data:
{mock_nutrition_data}

Please provide helpful nutrition advice based on this real data."""

        print("⏳ Generating nutrition advice...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ Nutrition advice generated successfully!")
        print(f"📝 Response ({len(result)} chars):")
        print(f"{result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"❌ Error type: {type(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting MosaicML standalone tests...")
    print("=" * 60)
    
    # Test 1: Direct API call
    success1 = test_mosaicml_direct()
    
    # Test 2: Nutrition AI logic without Flask
    success2 = test_nutrition_ai_without_flask()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Direct API call: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"   Nutrition AI logic: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("🎉 All tests passed! The issue is likely with Flask integration.")
    else:
        print("⚠️  Some tests failed. Check API credentials and network.")