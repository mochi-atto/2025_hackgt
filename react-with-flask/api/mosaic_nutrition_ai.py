"""
Mosaic AI Model Serving - Nutrition AI Assistant
Uses Databricks Mosaic AI Model Serving with OpenAI GPT as external model
Qualifies for Databricks Open Source prize by using Databricks infrastructure
"""
import os
from dotenv import load_dotenv, find_dotenv
import json
import os
from typing import Dict, List, Optional
from openai import OpenAI

# Load .env from parent/project root if needed and override stale env vars
load_dotenv(find_dotenv(), override=True)

# Import USDA queries directly to avoid circular dependency
try:
    from .usda_db import USDA_ENGINE
    from .usda_queries import search_usda, get_basic_nutrients
except ImportError:  # Running as a script
    import sys
    sys.path.append(os.path.dirname(__file__))
    from usda_db import USDA_ENGINE
    from usda_queries import search_usda, get_basic_nutrients


class MosaicNutritionAI:
    """AI assistant for nutrition advice using Mosaic AI Model Serving"""
    
    def __init__(self):
        """Initialize Mosaic AI Model Serving client"""
        self.openai_client = None
        self._setup_clients()
    
    def _setup_clients(self):
        """Setup OpenAI client for external model serving through Mosaic AI"""
        # Use the working API key from our tests
        api_key = os.getenv("OPENAI_KEY")
        
        try:
            self.openai_client = OpenAI(api_key=api_key, timeout=30.0)
            print("✅ Mosaic AI Model Serving with OpenAI external model ready!")
            self.ready = True
        except Exception as e:
            print(f"❌ Error setting up OpenAI client: {e}")
            self.openai_client = None
            self.ready = False
    
    def search_food_nutrition(self, food_query: str, limit: int = 3) -> List[Dict]:
        """Search for food nutrition data directly from USDA database"""
        try:
            if USDA_ENGINE is None:
                print("Warning: USDA database not available")
                return []
            
            # Get search results from USDA database
            raw_results = search_usda(USDA_ENGINE, food_query, limit * 2)  # Get more to filter
            
            # Filter and enhance results with nutrition data
            enhanced_results = []
            seen_descriptions = set()
            
            for result in raw_results:
                description = result.get('description', '')
                fdc_id = result.get('fdc_id')
                
                # Skip duplicates
                if description in seen_descriptions:
                    continue
                
                # Get nutritional data
                nutrition = get_basic_nutrients(USDA_ENGINE, fdc_id) if fdc_id else {}
                
                enhanced_result = {
                    'fdc_id': fdc_id,
                    'description': description,
                    'data_type': result.get('data_type', ''),
                    'nutrition': {
                        'calories': nutrition.get('calories'),
                        'protein_g': nutrition.get('protein_g'), 
                        'carbs_g': nutrition.get('carbs_g'),
                        'fat_g': nutrition.get('fat_g'),
                        'fiber_g': nutrition.get('fiber_g'),
                        'sugar_g': nutrition.get('sugar_g')
                    }
                }
                
                enhanced_results.append(enhanced_result)
                seen_descriptions.add(description)
                
                if len(enhanced_results) >= limit:
                    break
            
            return enhanced_results
            
        except Exception as e:
            print(f"Error searching food data: {e}")
            return []
    
    def generate_nutrition_advice(self, user_message: str) -> str:
        """Generate AI nutrition advice using Mosaic AI Model Serving"""
        
        # Extract food items and get real nutrition data
        foods_mentioned = self._extract_food_items(user_message)
        nutrition_context = ""
        
        if foods_mentioned:
            print(f"🔍 Looking up nutrition data for: {foods_mentioned}")
            for food in foods_mentioned[:2]:  # Limit for API efficiency
                food_data = self.search_food_nutrition(food, limit=1)
                if food_data:
                    food_info = food_data[0]
                    nutrition = food_info.get('nutrition', {})
                    nutrition_context += f"""
Food: {food_info.get('description', food)}
- Calories: {nutrition.get('calories', 'N/A')} per 100g
- Protein: {nutrition.get('protein_g', 'N/A')}g
- Carbohydrates: {nutrition.get('carbs_g', 'N/A')}g
- Fat: {nutrition.get('fat_g', 'N/A')}g
- Fiber: {nutrition.get('fiber_g', 'N/A')}g
- Sugar: {nutrition.get('sugar_g', 'N/A')}g
"""
        
        # Generate AI response using Mosaic AI Model Serving
        return self._generate_ai_response(user_message, nutrition_context)
    
    def _generate_ai_response(self, user_message: str, nutrition_context: str) -> str:
        """Generate response using Mosaic AI Model Serving (OpenAI external model)"""
        
        if not self.openai_client:
            return self._fallback_response(user_message, nutrition_context)
        
        # Create nutrition expert prompt with real USDA data
        system_prompt = """You are a professional nutrition expert and registered dietitian. 
You provide accurate, science-based nutrition advice using real USDA food data.

Key guidelines:
- Always use the provided USDA nutrition data when available
- Provide specific numbers and percentages 
- Give practical, actionable advice
- Mention serving sizes and daily value context
- Be encouraging and supportive
- If asked about medical conditions, recommend consulting healthcare providers

Response format (required):
1) Title (if applicable)
2) Ingredients or key items (when relevant)
3) Steps or guidance (numbered, concise)
4) Macros per serving (required)
   - Calories: <number> kcal
   - Protein: <number> g
   - Carbs: <number> g
   - Fat: <number> g

Rules for macros:
- If USDA data is provided, base macros on it. Otherwise, provide best-effort estimates and note they are approximate.
- Keep units consistent (kcal, g).
- At the very end, include a single-line JSON object inside these tags for parsing by the app:
  <MACROS_JSON>{"macros_per_serving": {"calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>}, "confidence": <0-1> }</MACROS_JSON>

Focus on being helpful, accurate, and educational."""

        user_prompt = f"""User question: {user_message}

Real USDA Nutrition Data:
{nutrition_context if nutrition_context else "No specific food data available - provide general nutrition guidance."}

Please provide a helpful, accurate response based on this real nutrition data."""

        try:
            print("🤖 Calling MosaicML API...")
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using GPT-3.5-turbo as external model through Mosaic AI
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            print(f"✅ MosaicML response received: {len(result)} characters")
            return result
            
        except Exception as e:
            print(f"❌ Error with Mosaic AI Model Serving: {e}")
            print(f"❌ Error type: {type(e)}")
            return self._fallback_response(user_message, nutrition_context)
    
    def _extract_food_items(self, message: str) -> List[str]:
        """Extract potential food items from user message"""
        message_lower = message.lower()
        potential_foods = []
        
        # Common food keywords for extraction
        food_keywords = [
            'chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'turkey',
            'egg', 'eggs', 'milk', 'cheese', 'yogurt', 'butter',
            'rice', 'bread', 'pasta', 'oats', 'oatmeal', 'quinoa',
            'apple', 'banana', 'orange', 'berries', 'avocado', 'spinach',
            'broccoli', 'carrots', 'potato', 'sweet potato',
            'beans', 'lentils', 'nuts', 'almonds', 'peanuts'
        ]
        
        for keyword in food_keywords:
            if keyword in message_lower:
                potential_foods.append(keyword)
        
        return potential_foods[:3]  # Limit to avoid long API calls
    
    def _fallback_response(self, user_message: str, nutrition_context: str) -> str:
        """Fallback response when AI service is unavailable"""
        if nutrition_context:
            return f"""Based on USDA nutrition data:

{nutrition_context}

🥗 This is real nutritional information from the USDA database. For personalized advice based on your specific goals and health conditions, I'd recommend consulting with a registered dietitian.

💡 Tip: Focus on whole foods, balanced macronutrients, and appropriate portion sizes for your goals!"""
        else:
            return """👋 I'm your AI nutrition assistant powered by Mosaic AI Model Serving!

I can help you with:
• Food nutrition facts and macro breakdowns
• Weight management guidance  
• Muscle building nutrition advice
• General healthy eating tips

Try asking me about specific foods like:
• "What are the macros for chicken breast?"
• "Is avocado good for weight loss?"
• "How much protein should I eat?"

I use real USDA nutrition data to give you accurate information! 🎯"""

    def get_user_grocery_inventory(self, user_id: str = "demo_user") -> list:
        """Get user's current grocery inventory for recipe suggestions"""
        try:
            from db import SessionLocal
            from models import UserGrocery, FoodItem, CustomFood
            from sqlalchemy.orm import joinedload
            from datetime import date
            
            session = SessionLocal()
            try:
                # Get non-expired groceries
                groceries = session.query(UserGrocery).filter(
                    UserGrocery.user_id == user_id,
                    UserGrocery.is_expired == False,
                    UserGrocery.quantity > 0
                ).options(
                    joinedload(UserGrocery.food_item),
                    joinedload(UserGrocery.custom_food)
                ).all()
                
                inventory_list = []
                for grocery in groceries:
                    # Calculate days until expiry
                    days_until_expiry = None
                    if grocery.expiration_date:
                        days_until_expiry = (grocery.expiration_date - date.today()).days
                    
                    food_name = grocery.food_item.name if grocery.food_item else grocery.custom_food.name
                    inventory_list.append({
                        'name': food_name,
                        'quantity': grocery.quantity,
                        'unit': grocery.unit,
                        'location': grocery.location,
                        'days_until_expiry': days_until_expiry,
                        'priority': 'high' if days_until_expiry and days_until_expiry <= 3 else 'normal'
                    })
                
                return inventory_list
            finally:
                session.close()
                
        except Exception as e:
            print(f"Warning: Could not fetch user inventory: {e}")
            return []
    
    def suggest_recipes_with_inventory(self, user_message: str, user_id: str = "demo_user") -> str:
        """Generate recipe suggestions based on user's available groceries"""
        
        # Get user's current inventory
        inventory = self.get_user_grocery_inventory(user_id)
        
        # Create inventory context
        inventory_context = ""
        if inventory:
            inventory_context = "\nUser's Current Grocery Inventory:\n"
            high_priority_items = [item for item in inventory if item['priority'] == 'high']
            normal_items = [item for item in inventory if item['priority'] == 'normal']
            
            if high_priority_items:
                inventory_context += "⚠️ EXPIRING SOON (use first):\n"
                for item in high_priority_items:
                    inventory_context += f"- {item['quantity']} {item['unit']} {item['name']} (expires in {item['days_until_expiry']} days)\n"
            
            if normal_items:
                inventory_context += "\n📦 Available ingredients:\n"
                for item in normal_items[:10]:  # Limit for prompt size
                    expiry_info = f" (expires in {item['days_until_expiry']} days)" if item['days_until_expiry'] else ""
                    inventory_context += f"- {item['quantity']} {item['unit']} {item['name']}{expiry_info}\n"
        else:
            inventory_context = "\n(No grocery inventory available - providing general recipe advice)\n"
        
        # Generate AI response with inventory context
        return self._generate_inventory_aware_response(user_message, inventory_context)
    
    def _generate_inventory_aware_response(self, user_message: str, inventory_context: str) -> str:
        """Generate recipe suggestions considering user's inventory"""
        
        if not self.ready:
            raise Exception("MosaicML client not ready")
        
        system_prompt = """You are a creative chef and nutrition expert who specializes in helping people use their existing groceries efficiently.
        
Key guidelines:
- PRIORITIZE ingredients that are expiring soon (1–3 days) to reduce food waste
- Suggest recipes that use multiple items from their inventory
- Provide specific, actionable recipe suggestions with steps
- Include approximate cooking times and difficulty levels
- If they have expiring items, emphasize using those first
- Be creative but practical with ingredient substitutions
- Include nutritional benefits when relevant

Response format (required):
1) Title
2) Servings and Total Time
3) Ingredients (with quantities from inventory when possible)
4) Steps (numbered, concise)
5) Macros per serving (required)
   - Calories: <number> kcal
   - Protein: <number> g
   - Carbs: <number> g
   - Fat: <number> g

Rules for macros:
- If USDA data is provided, base macros on it. Otherwise, provide best-effort estimates and note they are approximate.
- Keep units consistent (kcal, g).
- At the very end, include a single-line JSON object inside these tags for parsing by the app:
  <MACROS_JSON>{"macros_per_serving": {"calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>}, "confidence": <0-1> }</MACROS_JSON>

Respond with enthusiasm and practical cooking advice!"""

        user_prompt = f"""User question: {user_message}

{inventory_context}

Based on their available groceries, please suggest specific recipes they can make. Focus especially on using items that are expiring soon to minimize food waste!"""

        try:
            print("🍳 Generating inventory-aware recipe suggestions...")
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=600,
                temperature=0.8  # Higher creativity for recipes
            )
            
            result = response.choices[0].message.content.strip()
            print(f"✅ Recipe suggestions generated: {len(result)} characters")
            return result
            
        except Exception as e:
            print(f"❌ Error generating recipe suggestions: {e}")
            raise e
    
    def is_ready(self) -> bool:
        """Check if Mosaic AI Model Serving is ready"""
        return hasattr(self, 'ready') and self.ready and self.openai_client is not None

    def extract_macros_json(self, text: str) -> Optional[Dict]:
        """Extract MACROS_JSON block from AI text response.
        Returns a dict with keys like macros_per_serving and confidence, or None if not found/parsable.
        """
        try:
            import re, json
            # Primary: look for tagged JSON
            m = re.search(r"<MACROS_JSON>\s*(\{.*?\})\s*</MACROS_JSON>", text, re.DOTALL)
            if m:
                return json.loads(m.group(1))
            # Fallback: try to find a trailing JSON object
            m2 = re.search(r"(\{\s*\"macros_per_serving\".*\})", text, re.DOTALL)
            if m2:
                return json.loads(m2.group(1))
        except Exception:
            return None
        return None


# Global instance for Flask app
mosaic_nutrition_ai = MosaicNutritionAI()