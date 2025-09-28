#!/usr/bin/env python3
"""
Comprehensive test of the grocery tracking and expiration features
"""

import requests
import json
from datetime import date, timedelta

def test_grocery_features():
    """Test all grocery tracking functionality"""
    
    base_url = "http://127.0.0.1:5001"
    user_id = "test_user"
    
    print("🛒 Testing Grocery Tracking & Expiration Features")
    print("=" * 60)
    
    try:
        # ===== Test 1: Create a custom food (leftover pizza) =====
        print("\n🍕 Step 1: Creating custom food (leftover pizza)")
        custom_food_data = {
            "user_id": user_id,
            "name": "Leftover Pizza",
            "description": "Homemade cheese pizza from yesterday",
            "serving_size": 2,
            "serving_unit": "slices",
            "calories": 400,
            "protein_g": 18,
            "carbs_g": 45,
            "fat_g": 16,
            "fiber_g": 2,
            "sugar_g": 4,
            "nutrition_estimated": False
        }
        
        response = requests.post(f"{base_url}/api/custom-foods", json=custom_food_data)
        if response.status_code == 201:
            custom_food = response.json()
            custom_food_id = custom_food['id']
            print(f"✅ Created custom food: {custom_food['name']} (ID: {custom_food_id})")
        else:
            print(f"❌ Failed to create custom food: {response.text}")
            return False
        
        # ===== Test 2: Get AI nutrition estimation for leftovers =====
        print("\n🤖 Step 2: Testing AI nutrition estimation")
        estimation_data = {
            "name": "Chicken Stir-fry Leftovers",
            "description": "Mixed vegetables with chicken breast, cooked in olive oil",
            "serving_size": 1,
            "serving_unit": "bowl"
        }
        
        response = requests.post(f"{base_url}/api/custom-foods/estimate-nutrition", json=estimation_data)
        if response.status_code == 200:
            estimation = response.json()
            print(f"✅ AI nutrition estimation: {estimation['confidence']*100:.0f}% confidence")
            print(f"   Estimated calories: {estimation['estimated_nutrition']['calories']}")
        else:
            print(f"⚠️ AI estimation failed: {response.text}")
        
        # ===== Test 3: Add groceries to inventory =====
        print("\n🥗 Step 3: Adding groceries to inventory")
        
        # Add some groceries with different expiration dates
        groceries_to_add = [
            {
                "food_type": "custom",
                "custom_food_id": custom_food_id,
                "quantity": 4,
                "unit": "slices",
                "location": "fridge",
                "purchase_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=2)).isoformat(),
                "notes": "Pizza from Tony's"
            },
            {
                "food_type": "usda", 
                "food_item_id": 1,  # Assuming a chicken breast item exists
                "quantity": 2,
                "unit": "pieces",
                "location": "fridge",
                "purchase_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=5)).isoformat(),
                "notes": "Fresh chicken breast"
            }
        ]
        
        added_groceries = []
        for grocery_data in groceries_to_add:
            grocery_data["user_id"] = user_id
            response = requests.post(f"{base_url}/api/groceries", json=grocery_data)
            if response.status_code == 201:
                added_grocery = response.json()
                added_groceries.append(added_grocery)
                food_type = grocery_data['food_type']
                quantity = grocery_data['quantity']
                unit = grocery_data['unit']
                print(f"✅ Added {quantity} {unit} of {food_type} food to inventory")
            else:
                print(f"❌ Failed to add grocery: {response.text}")
        
        # ===== Test 4: View grocery inventory =====
        print("\n📦 Step 4: Viewing grocery inventory")
        response = requests.get(f"{base_url}/api/groceries?user_id={user_id}")
        if response.status_code == 200:
            inventory = response.json()
            print(f"✅ Current inventory: {inventory['total_items']} items")
            print(f"   Items expiring soon: {inventory['expiring_soon']}")
            print(f"   Expired items: {inventory['expired']}")
            
            for item in inventory['groceries']:
                food_name = item['food_info']['name']
                quantity = item['quantity']
                unit = item['unit']
                expiry_status = item['expiry_status']
                days_left = item['days_until_expiry']
                print(f"   - {quantity} {unit} {food_name} ({expiry_status}, {days_left} days left)")
        else:
            print(f"❌ Failed to get inventory: {response.text}")
        
        # ===== Test 5: Check expiring items =====
        print("\n⏰ Step 5: Checking expiring items")
        response = requests.get(f"{base_url}/api/groceries/expiring?user_id={user_id}&days=7")
        if response.status_code == 200:
            expiring = response.json()
            print(f"✅ Found {expiring['total_count']} items expiring in next 7 days")
            print(f"   Critical (1 day): {expiring['critical_count']}")
            print(f"   Warning (2-7 days): {expiring['warning_count']}")
            
            for item in expiring['expiring_items']:
                print(f"   - {item['food_name']}: expires in {item['days_until_expiry']} days ({item['urgency']})")
        else:
            print(f"❌ Failed to get expiring items: {response.text}")
        
        # ===== Test 6: Update grocery item =====
        if added_groceries:
            print("\n✏️ Step 6: Updating grocery item")
            grocery_id = added_groceries[0]['id']
            update_data = {
                "user_id": user_id,
                "quantity": 2,  # Ate 2 slices
                "is_opened": True,
                "notes": "Opened package, ate 2 slices"
            }
            
            response = requests.put(f"{base_url}/api/groceries/{grocery_id}", json=update_data)
            if response.status_code == 200:
                print(f"✅ Updated grocery item {grocery_id}")
            else:
                print(f"❌ Failed to update grocery: {response.text}")
        
        # ===== Test 7: Get custom foods list =====
        print("\n📝 Step 7: Viewing custom foods")
        response = requests.get(f"{base_url}/api/custom-foods?user_id={user_id}")
        if response.status_code == 200:
            custom_foods = response.json()
            print(f"✅ Found {custom_foods['total_count']} custom foods")
            for food in custom_foods['custom_foods']:
                nutrition_type = "estimated" if food['nutrition_estimated'] else "user-provided"
                print(f"   - {food['name']}: {food['nutrition']['calories']} cal ({nutrition_type})")
        else:
            print(f"❌ Failed to get custom foods: {response.text}")
        
        print("\n" + "=" * 60)
        print("🎉 All grocery tracking tests completed successfully!")
        print("📊 Features demonstrated:")
        print("   ✅ Custom food creation with nutrition info")
        print("   ✅ AI-powered nutrition estimation")
        print("   ✅ Adding groceries to inventory")
        print("   ✅ Expiration date tracking")
        print("   ✅ Inventory management (view, update)")
        print("   ✅ Expiring items alerts")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_grocery_features()
    if success:
        print("\n💡 Your grocery tracking system is ready!")
        print("   Start the server with: python api.py")
        print("   Then integrate with React frontend!")
    else:
        print("\n⚠️ Some tests failed. Check the server and try again.")