"""
Databricks Recipe AI Integration
Uses Databricks Model Serving for advanced recipe generation
Qualifies for Databricks Open Source prize by using Databricks ML infrastructure
"""
import os
import json
import requests
from typing import Dict, List, Optional
from dataclasses import asdict

# Import our local recipe AI for fallback
try:
    from .recipe_ai import recipe_ai, Recipe
except ImportError:
    from recipe_ai import recipe_ai, Recipe


class DatabricksRecipeAI:
    """Advanced recipe generation using Databricks Model Serving"""
    
    def __init__(self):
        """Initialize Databricks client"""
        self.databricks_host = os.getenv('DATABRICKS_HOST', 'your-workspace.databricks.com')
        self.databricks_token = os.getenv('DATABRICKS_TOKEN', '')
        self.model_endpoint = os.getenv('DATABRICKS_MODEL_ENDPOINT', '/serving-endpoints/recipe-generator')
        self.fallback_ai = recipe_ai
        
        # Headers for Databricks API
        self.headers = {
            'Authorization': f'Bearer {self.databricks_token}',
            'Content-Type': 'application/json'
        }
        
        print(f"🧱 Databricks Recipe AI initialized")
        print(f"Host: {self.databricks_host}")
        print(f"Endpoint: {self.model_endpoint}")
        
    def is_databricks_available(self) -> bool:
        """Check if Databricks Model Serving is available"""
        if not self.databricks_token or not self.databricks_host:
            return False
            
        try:
            # Test connection to Databricks
            response = requests.get(
                f"https://{self.databricks_host}/api/2.0/serving-endpoints",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Databricks unavailable: {e}")
            return False
    
    def generate_recipe_with_databricks(self, 
                                      ingredients: List[str],
                                      meal_type: str,
                                      dietary_preferences: List[str],
                                      nutrition_goals: Dict,
                                      cuisine_style: str = "international",
                                      servings: int = 2) -> Optional[Dict]:
        """Generate recipe using Databricks Model Serving"""
        
        if not self.is_databricks_available():
            print("⚠️  Databricks not available, using local AI")
            return None
            
        try:
            # Prepare the prompt for the Databricks model
            prompt = self._create_databricks_prompt(
                ingredients, meal_type, dietary_preferences, 
                nutrition_goals, cuisine_style, servings
            )
            
            # Call Databricks Model Serving endpoint
            payload = {
                "inputs": {
                    "prompt": prompt,
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                f"https://{self.databricks_host}{self.model_endpoint}",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_databricks_response(result)
            else:
                print(f"Databricks API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error calling Databricks: {e}")
            return None
    
    def generate_advanced_recipe(self,
                               ingredients: List[str] = None,
                               meal_type: str = "dinner",
                               dietary_preferences: List[str] = None,
                               nutrition_goals: Dict = None,
                               cuisine_style: str = "international",
                               servings: int = 2,
                               cooking_time: int = None,
                               skill_level: str = "intermediate") -> Recipe:
        """Generate recipe with Databricks or fallback to local AI"""
        
        ingredients = ingredients or []
        dietary_preferences = dietary_preferences or []
        nutrition_goals = nutrition_goals or {}
        
        # Try Databricks first
        databricks_result = self.generate_recipe_with_databricks(
            ingredients, meal_type, dietary_preferences, 
            nutrition_goals, cuisine_style, servings
        )
        
        if databricks_result:
            print("✅ Generated recipe using Databricks Model Serving")
            return self._convert_databricks_to_recipe(databricks_result)
        else:
            print("🔄 Using local AI fallback")
            # Use enhanced local generation with additional parameters
            return self._generate_enhanced_local_recipe(
                ingredients, meal_type, dietary_preferences, 
                nutrition_goals, cuisine_style, servings, 
                cooking_time, skill_level
            )
    
    def _create_databricks_prompt(self, 
                                 ingredients: List[str],
                                 meal_type: str,
                                 dietary_preferences: List[str],
                                 nutrition_goals: Dict,
                                 cuisine_style: str,
                                 servings: int) -> str:
        """Create a structured prompt for Databricks model"""
        
        prompt = f"""Create a detailed {cuisine_style} {meal_type} recipe for {servings} servings.

REQUIREMENTS:
- Meal Type: {meal_type}
- Cuisine Style: {cuisine_style}
- Servings: {servings}
- Dietary Preferences: {', '.join(dietary_preferences) if dietary_preferences else 'None'}
- Nutrition Goals: {json.dumps(nutrition_goals) if nutrition_goals else 'Balanced nutrition'}
"""

        if ingredients:
            prompt += f"\nPREFERRED INGREDIENTS: {', '.join(ingredients)}"
        
        prompt += """

RESPONSE FORMAT (JSON):
{
    "name": "Recipe Name",
    "description": "Brief description",
    "prep_time": 15,
    "cook_time": 30,
    "servings": 2,
    "difficulty": "easy/medium/hard",
    "cuisine": "cuisine_type",
    "ingredients": [
        {
            "name": "ingredient name",
            "amount": "1 cup",
            "notes": "preparation notes"
        }
    ],
    "instructions": [
        "Step 1: Detailed instruction",
        "Step 2: Detailed instruction"
    ],
    "nutrition_per_serving": {
        "calories": 450,
        "protein_g": 25,
        "carbs_g": 35,
        "fat_g": 20,
        "fiber_g": 8
    },
    "tips": [
        "Helpful cooking tip 1",
        "Helpful cooking tip 2"
    ],
    "dietary_tags": ["tag1", "tag2"]
}

Generate a creative, healthy, and delicious recipe following this format exactly:"""

        return prompt
    
    def _parse_databricks_response(self, response: Dict) -> Optional[Dict]:
        """Parse response from Databricks model"""
        try:
            # Extract the generated text
            if 'predictions' in response:
                generated_text = response['predictions'][0]['candidates'][0]['text']
            elif 'choices' in response:
                generated_text = response['choices'][0]['message']['content']
            else:
                generated_text = response.get('generated_text', '')
            
            # Try to parse JSON from the response
            # Look for JSON content between { and }
            start_idx = generated_text.find('{')
            end_idx = generated_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = generated_text[start_idx:end_idx]
                return json.loads(json_str)
            
            return None
            
        except Exception as e:
            print(f"Error parsing Databricks response: {e}")
            return None
    
    def _convert_databricks_to_recipe(self, databricks_data: Dict) -> Recipe:
        """Convert Databricks response to Recipe object"""
        from recipe_ai import RecipeIngredient
        
        # Parse ingredients
        ingredients = []
        for ing_data in databricks_data.get('ingredients', []):
            ingredient = RecipeIngredient(
                name=ing_data.get('name', ''),
                amount=self._parse_amount(ing_data.get('amount', '1')),
                unit=self._parse_unit(ing_data.get('amount', '1 unit')),
                nutrition=None  # Would need USDA lookup
            )
            ingredients.append(ingredient)
        
        # Get nutrition data
        nutrition = databricks_data.get('nutrition_per_serving', {})
        total_nutrition = {}
        servings = databricks_data.get('servings', 1)
        
        for key, value in nutrition.items():
            if isinstance(value, (int, float)):
                total_nutrition[key] = value * servings
        
        return Recipe(
            name=databricks_data.get('name', 'Generated Recipe'),
            ingredients=ingredients,
            instructions=databricks_data.get('instructions', []),
            prep_time=databricks_data.get('prep_time', 15),
            cook_time=databricks_data.get('cook_time', 30),
            servings=servings,
            total_nutrition=total_nutrition,
            dietary_tags=databricks_data.get('dietary_tags', [])
        )
    
    def _generate_enhanced_local_recipe(self,
                                      ingredients: List[str],
                                      meal_type: str,
                                      dietary_preferences: List[str],
                                      nutrition_goals: Dict,
                                      cuisine_style: str,
                                      servings: int,
                                      cooking_time: int,
                                      skill_level: str) -> Recipe:
        """Enhanced local recipe generation with additional parameters"""
        
        # Use the local AI but with enhanced logic
        base_recipe = self.fallback_ai.generate_recipe(
            meal_type=meal_type,
            dietary_preferences=dietary_preferences,
            nutrition_goals=nutrition_goals,
            servings=servings
        )
        
        # Enhance with cuisine style
        if cuisine_style != "international":
            base_recipe.name = f"{cuisine_style.title()} {base_recipe.name}"
            base_recipe.dietary_tags.append(cuisine_style)
        
        # Adjust for cooking time if specified
        if cooking_time:
            # Modify recipe complexity based on time constraints
            if cooking_time <= 15:  # Quick meals
                base_recipe.name = f"Quick {base_recipe.name}"
                base_recipe.cook_time = min(base_recipe.cook_time, 15)
                base_recipe.dietary_tags.append("quick")
            elif cooking_time >= 60:  # Slow cooking
                base_recipe.name = f"Slow-Cooked {base_recipe.name}"
                base_recipe.dietary_tags.append("slow-cooked")
        
        # Add skill level considerations
        if skill_level == "beginner":
            base_recipe.dietary_tags.append("beginner-friendly")
        elif skill_level == "advanced":
            base_recipe.dietary_tags.append("advanced")
        
        return base_recipe
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount from string like '1 cup' or '2.5'"""
        try:
            # Extract numeric part
            import re
            numbers = re.findall(r'\d+\.?\d*', amount_str)
            if numbers:
                return float(numbers[0])
            return 1.0
        except:
            return 1.0
    
    def _parse_unit(self, amount_str: str) -> str:
        """Parse unit from string like '1 cup' or '2.5 oz'"""
        try:
            # Common unit mappings
            if 'cup' in amount_str.lower():
                return 'cup'
            elif 'tbsp' in amount_str.lower() or 'tablespoon' in amount_str.lower():
                return 'tbsp'
            elif 'tsp' in amount_str.lower() or 'teaspoon' in amount_str.lower():
                return 'tsp'
            elif 'oz' in amount_str.lower():
                return 'oz'
            elif 'lb' in amount_str.lower() or 'pound' in amount_str.lower():
                return 'lb'
            elif 'g' in amount_str.lower() and 'gram' in amount_str.lower():
                return 'g'
            else:
                return 'unit'
        except:
            return 'unit'
    
    def batch_generate_recipes(self, 
                              count: int = 5,
                              variety_params: List[Dict] = None) -> List[Recipe]:
        """Generate multiple recipes with variety"""
        
        if not variety_params:
            # Default variety parameters
            variety_params = [
                {"meal_type": "breakfast", "cuisine_style": "american"},
                {"meal_type": "lunch", "cuisine_style": "mediterranean"},
                {"meal_type": "dinner", "cuisine_style": "asian"},
                {"meal_type": "dinner", "cuisine_style": "italian"},
                {"meal_type": "snack", "cuisine_style": "international"}
            ]
        
        recipes = []
        for i in range(count):
            params = variety_params[i % len(variety_params)]
            recipe = self.generate_advanced_recipe(**params)
            recipes.append(recipe)
        
        return recipes


# Global instance
databricks_recipe_ai = DatabricksRecipeAI()