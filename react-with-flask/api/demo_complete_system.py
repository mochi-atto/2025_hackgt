#!/usr/bin/env python3
"""
Complete Food Tracking System Demo
Demonstrates all features: grocery tracking, expiration monitoring, custom foods, AI nutrition advice, and inventory-based recipe suggestions
"""

import requests
import json
from datetime import date, timedelta
import time

class FoodTrackerDemo:
    def __init__(self, base_url="http://127.0.0.1:5001"):
        self.base_url = base_url
        self.user_id = "demo_user"
        
    def run_complete_demo(self):
        """Run a complete demo of all food tracking features"""
        
        print("🏆 COMPLETE FOOD TRACKING SYSTEM DEMO")
        print("=" * 70)
        print("🎯 Features: Grocery Tracking + Expiration Alerts + AI Recipe Suggestions")
        print("🚀 Powered by: Databricks MosaicML + USDA Nutrition Database")
        print("=" * 70)
        
        try:
            # Step 1: Create custom foods (leftovers)
            self.demo_custom_foods()
            
            # Step 2: Add groceries with expiration dates
            added_items = self.demo_add_groceries()
            
            # Step 3: View inventory and expiration alerts
            self.demo_inventory_management()
            
            # Step 4: Get AI nutrition advice
            self.demo_ai_nutrition_advice()
            
            # Step 5: Get AI recipe suggestions based on inventory
            self.demo_inventory_recipe_suggestions()
            
            # Step 6: Update groceries (eating/using items)
            self.demo_update_groceries(added_items)
            
            # Final summary
            self.demo_final_summary()
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
    
    def demo_custom_foods(self):
        """Demo custom food creation with AI estimation"""
        print("\\n🍳 STEP 1: Creating Custom Foods (Leftovers)")
        print("-" * 50)
        
        # Create leftover pasta
        leftover_pasta = {
            "user_id": self.user_id,
            "name": "Leftover Spaghetti Carbonara",
            "description": "Creamy pasta with bacon and parmesan, made last night",
            "serving_size": 1.5,
            "serving_unit": "cups",
            "calories": 520,
            "protein_g": 22,
            "carbs_g": 58,
            "fat_g": 24,
            "fiber_g": 3,
            "sugar_g": 4
        }
        
        response = requests.post(f"{self.base_url}/api/custom-foods", json=leftover_pasta)
        if response.status_code == 201:
            pasta_id = response.json()['id']
            print(f"✅ Created: {leftover_pasta['name']} (ID: {pasta_id})")
            self.pasta_id = pasta_id
        
        # Test AI nutrition estimation for mystery leftovers
        mystery_food = {
            "name": "Chicken Stir-fry Leftovers",
            "description": "Mixed vegetables, chicken breast, garlic, soy sauce, cooked in sesame oil",
            "serving_size": 1,
            "serving_unit": "bowl"
        }
        
        response = requests.post(f"{self.base_url}/api/custom-foods/estimate-nutrition", json=mystery_food)
        if response.status_code == 200:
            estimation = response.json()
            print(f"🤖 AI Estimated nutrition for {mystery_food['name']}:")
            print(f"    Confidence: {estimation['confidence']*100:.0f}%")
            print(f"    Calories: {estimation['estimated_nutrition']['calories']}")
            print(f"    Protein: {estimation['estimated_nutrition']['protein_g']}g")
    
    def demo_add_groceries(self):
        """Demo adding groceries with different expiration dates"""
        print("\\n🛒 STEP 2: Adding Groceries with Expiration Tracking")
        print("-" * 50)
        
        # Create groceries with strategic expiration dates
        groceries = [
            {
                "food_type": "custom",
                "custom_food_id": getattr(self, 'pasta_id', 1),
                "quantity": 3,
                "unit": "servings",
                "location": "fridge",
                "purchase_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=1)).isoformat(),  # Expires tomorrow!
                "notes": "Leftover from dinner, use soon!"
            },
            {
                "food_type": "usda",
                "food_item_id": 1,  # Assuming chicken exists
                "quantity": 1.5,
                "unit": "lbs",
                "location": "fridge",
                "purchase_date": (date.today() - timedelta(days=1)).isoformat(),
                "expiration_date": (date.today() + timedelta(days=4)).isoformat(),
                "notes": "Fresh chicken breast from butcher"
            },
            {
                "food_type": "usda",
                "food_item_id": 2,  # Assuming milk exists
                "quantity": 1,
                "unit": "gallon",
                "location": "fridge", 
                "purchase_date": (date.today() - timedelta(days=2)).isoformat(),
                "expiration_date": (date.today() + timedelta(days=6)).isoformat(),
                "notes": "Organic whole milk"
            }
        ]
        
        added_items = []
        for grocery in groceries:
            grocery["user_id"] = self.user_id
            response = requests.post(f"{self.base_url}/api/groceries", json=grocery)
            if response.status_code == 201:
                item = response.json()
                added_items.append(item)
                days_until_expiry = (date.fromisoformat(grocery['expiration_date']) - date.today()).days
                print(f"✅ Added: {grocery['quantity']} {grocery['unit']} ({grocery['food_type']} food)")
                print(f"    Location: {grocery['location']}, Expires in {days_until_expiry} days")
        
        return added_items
    
    def demo_inventory_management(self):
        """Demo viewing inventory and expiration alerts"""
        print("\\n📦 STEP 3: Inventory Management & Expiration Alerts")
        print("-" * 50)
        
        # Get current inventory
        response = requests.get(f"{self.base_url}/api/groceries?user_id={self.user_id}")
        if response.status_code == 200:
            inventory = response.json()
            print(f"📊 Current inventory: {inventory['total_items']} items")
            print(f"⚠️  Items expiring soon: {inventory['expiring_soon']}")
            print(f"❌ Expired items: {inventory['expired']}")
            print()
            
            for item in inventory['groceries']:
                status_emoji = {"fresh": "✅", "expiring_this_week": "⏰", "expiring_soon": "⚠️", "expired": "❌"}
                emoji = status_emoji.get(item['expiry_status'], "❓")
                
                print(f"{emoji} {item['quantity']} {item['unit']} {item['food_info']['name']}")
                print(f"    📍 {item['location']}, expires in {item['days_until_expiry']} days")
        
        # Check specifically for expiring items
        response = requests.get(f"{self.base_url}/api/groceries/expiring?user_id={self.user_id}&days=7")
        if response.status_code == 200:
            expiring = response.json()
            if expiring['total_count'] > 0:
                print(f"\\n🚨 EXPIRATION ALERT: {expiring['total_count']} items need attention!")
                for item in expiring['expiring_items']:
                    urgency_emoji = {"critical": "🔴", "warning": "🟡"}
                    emoji = urgency_emoji.get(item['urgency'], "🟢")
                    print(f"{emoji} {item['food_name']}: {item['days_until_expiry']} days left")
    
    def demo_ai_nutrition_advice(self):
        """Demo AI nutrition consultation"""
        print("\\n🤖 STEP 4: AI Nutrition Consultation")
        print("-" * 50)
        
        questions = [
            "What are the health benefits of chicken breast?",
            "I'm trying to build muscle, what should I focus on nutritionally?"
        ]
        
        for question in questions:
            print(f"\\n💭 Question: {question}")
            response = requests.post(
                f"{self.base_url}/api/ai/chat",
                json={"message": question, "user_id": self.user_id}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"🎯 AI Response: {result['ai_response'][:150]}...")
                print(f"    (Full response: {len(result['ai_response'])} characters)")
    
    def demo_inventory_recipe_suggestions(self):
        """Demo AI recipe suggestions based on current inventory"""
        print("\\n🍳 STEP 5: AI Recipe Suggestions Based on Your Groceries")
        print("-" * 50)
        
        recipe_requests = [
            "What can I cook with my available groceries? I want something quick!",
            "I need to use up ingredients that are expiring soon. Any ideas?",
            "Can you suggest a healthy dinner recipe using what I have?"
        ]
        
        for request in recipe_requests:
            print(f"\\n🍽️  Request: {request}")
            response = requests.post(
                f"{self.base_url}/api/ai/recipe-suggestions",
                json={"message": request, "user_id": self.user_id}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"👨‍🍳 Recipe Ideas: {result['recipe_suggestions'][:200]}...")
                print(f"    (Powered by: {result['powered_by']})")
                print(f"    (Full suggestions: {len(result['recipe_suggestions'])} characters)")
            else:
                print(f"❌ Failed to get recipe suggestions: {response.text}")
            
            time.sleep(1)  # Brief pause between requests
    
    def demo_update_groceries(self, added_items):
        """Demo updating groceries (consuming/using items)"""
        print("\\n✏️ STEP 6: Using/Consuming Groceries")
        print("-" * 50)
        
        if added_items:
            # "Eat" some of the leftover pasta
            item_id = added_items[0]['id']
            update_data = {
                "user_id": self.user_id,
                "quantity": 1.5,  # Ate 1.5 servings, 1.5 left
                "is_opened": True,
                "notes": "Had some for lunch, delicious!"
            }
            
            response = requests.put(f"{self.base_url}/api/groceries/{item_id}", json=update_data)
            if response.status_code == 200:
                print("✅ Updated leftover pasta: consumed 1.5 servings")
                print("    Marked as opened, updated notes")
    
    def demo_final_summary(self):
        """Show final system summary"""
        print("\\n🎉 DEMO COMPLETE - SYSTEM SUMMARY")
        print("=" * 70)
        
        # Get final inventory state
        response = requests.get(f"{self.base_url}/api/groceries?user_id={self.user_id}")
        if response.status_code == 200:
            inventory = response.json()
            print(f"📊 Final inventory: {inventory['total_items']} items")
            
        # Get custom foods count
        response = requests.get(f"{self.base_url}/api/custom-foods?user_id={self.user_id}")
        if response.status_code == 200:
            custom_foods = response.json()
            print(f"🍳 Custom foods created: {custom_foods['total_count']} items")
        
        print("\\n✨ FEATURES DEMONSTRATED:")
        print("   ✅ Custom food creation (leftovers, homemade items)")
        print("   ✅ AI-powered nutrition estimation")
        print("   ✅ Grocery inventory tracking with expiration dates")
        print("   ✅ Expiration alerts and prioritization")
        print("   ✅ AI nutrition consultation with real USDA data")
        print("   ✅ Inventory-aware recipe suggestions")
        print("   ✅ Grocery consumption tracking")
        print("   ✅ Location-based storage (fridge, pantry, freezer)")
        
        print("\\n🏆 READY FOR HACKATHON DEMO!")
        print("   🥇 Databricks Open Source Prize - MosaicML integration")
        print("   🥈 Best Overall App - Complete food waste reduction system") 
        print("   🥉 Most Practical - Real-world grocery tracking solution")

if __name__ == "__main__":
    print("🚀 Starting Complete Food Tracking System Demo...")
    print("💡 Make sure your Flask server is running: python api.py")
    print()
    
    demo = FoodTrackerDemo()
    demo.run_complete_demo()
    
    print("\\n" + "=" * 70)
    print("🎯 Next Steps:")
    print("   1. Integrate with React frontend using Cedar chat components")
    print("   2. Add user authentication and multi-user support")  
    print("   3. Implement push notifications for expiring items")
    print("   4. Add barcode scanning for easy grocery entry")
    print("   5. Create meal planning calendar integration")
    print("=" * 70)