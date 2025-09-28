import time
from flask import Flask, jsonify, request
from flask_cors import CORS

# Load environment variables (for OPENAI_KEY in .env)
import os
try:
    from dotenv import load_dotenv, find_dotenv
    # Find .env starting from here and upwards (project root has .env)
    load_dotenv(find_dotenv(), override=True)
except Exception:
    # Safe fallback if dotenv isn't available; env vars will still work if set in the shell
    pass

# Import our MosaicML AI assistant
try:
    from .mosaic_nutrition_ai import mosaic_nutrition_ai
except ImportError:
    from mosaic_nutrition_ai import mosaic_nutrition_ai

# Robust imports to work both as a module and as a script
try:
    from .db import init_db, SessionLocal
    from .models import FoodItem, NutritionFacts, CustomFood, UserGrocery
    from .usda_db import USDA_ENGINE
    from .usda_queries import search_usda, lookup_upc, get_basic_nutrients, get_food_basic
except ImportError:  # Running as a script
    import os, sys
    sys.path.append(os.path.dirname(__file__))
    from db import init_db, SessionLocal
    from models import FoodItem, NutritionFacts, CustomFood, UserGrocery
    from usda_db import USDA_ENGINE
    from usda_queries import search_usda, lookup_upc, get_basic_nutrients, get_food_basic

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize database and tables on startup
init_db()


@app.route('/api/time')
def get_current_time():
    return {'time': time.time()}


@app.route('/api/test-ai', methods=['POST'])
def test_ai():
    """Simple AI test endpoint"""
    try:
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_KEY")
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Missing OPENAI_KEY in environment/.env',
                'error_type': 'MissingCredentials'
            }), 500
        
        client = OpenAI(api_key=api_key, timeout=10.0)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in 3 words"}],
            max_tokens=10
        )
        
        return jsonify({
            'success': True,
            'response': response.choices[0].message.content,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': str(type(e))
        }), 500


@app.route('/api/foods', methods=['GET'])
def list_foods():
    """List a few food items for smoke testing."""
    session = SessionLocal()
    try:
        q = session.query(FoodItem).limit(25).all()
        data = []
        for f in q:
            facts = None
            if f.nutrition:
                facts = {
                    'calories': f.nutrition.calories,
                    'protein_g': f.nutrition.protein_g,
                    'carbs_g': f.nutrition.carbs_g,
                    'fat_g': f.nutrition.fat_g,
                }
            data.append({
                'id': f.id,
                'name': f.name,
                'brand': f.brand,
                'category': f.category,
                'upc': f.upc,
                'is_perishable': f.is_perishable,
                'nutrition': facts,
            })
        return jsonify(data)
    finally:
        session.close()


@app.get('/api/usda/search')
def api_usda_search():
    if USDA_ENGINE is None:
        return jsonify({'error': 'USDA DB not found. Place USDA.sqlite under data/vendor/USDADataBase.'}), 503
    q = (request.args.get('q') or '').strip()
    limit = int(request.args.get('limit', '20'))
    if not q:
        return jsonify([])
    results = search_usda(USDA_ENGINE, q, limit)
    return jsonify(results)


@app.get('/api/usda/search-with-nutrition')
def api_usda_search_with_nutrition():
    """Enhanced search that includes nutritional data and filters duplicates"""
    if USDA_ENGINE is None:
        return jsonify({'error': 'USDA DB not found. Place USDA.sqlite under data/vendor/USDADataBase.'}), 503
    
    q = (request.args.get('q') or '').strip()
    limit = int(request.args.get('limit', '20'))
    
    if not q:
        return jsonify([])
    
    # Get search results with a higher limit to account for filtering
    raw_results = search_usda(USDA_ENGINE, q, limit * 3)  # Get more results to filter
    
    # Filter and enhance results
    enhanced_results = []
    seen_descriptions = set()  # Track descriptions to avoid duplicates
    
    for result in raw_results:
        description = result.get('description', '')
        fdc_id = result.get('fdc_id')
        
        # Skip duplicates by description
        if description in seen_descriptions:
            continue
            
        # Prioritize branded_food over sub_sample_food
        data_type = result.get('data_type', '')
        if data_type == 'sub_sample_food':
            # Check if we already have a branded version of this
            if any(r['description'] == description and r.get('data_type') == 'branded_food' 
                   for r in enhanced_results):
                continue
        
        # Get nutritional data for this food item
        nutrition = get_basic_nutrients(USDA_ENGINE, fdc_id) if fdc_id else {}
        
        # Structure the enhanced result
        enhanced_result = {
            'fdc_id': fdc_id,
            'description': description,
            'data_type': data_type,
            'brand': result.get('brand'),
            'brand_name': result.get('brand_name'),
            'brand_owner': result.get('brand_owner'),
            'gtin_upc': result.get('gtin_upc'),
            'serving_size': result.get('serving_size'),
            'serving_size_unit': result.get('serving_size_unit'),
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
        
        # Stop once we have enough unique results
        if len(enhanced_results) >= limit:
            break
    
    return jsonify(enhanced_results)


@app.get('/api/usda/upc/<upc>')
def api_usda_upc(upc: str):
    if USDA_ENGINE is None:
        return jsonify({'error': 'USDA DB not found. Place USDA.sqlite under data/vendor/USDADataBase.'}), 503
    row = lookup_upc(USDA_ENGINE, upc)
    return jsonify(row or {})


@app.post('/api/usda/import/<int:fdc_id>')
def api_usda_import(fdc_id: int):
    if USDA_ENGINE is None:
        return jsonify({'error': 'USDA DB not found. Place USDA.sqlite under data/vendor/USDADataBase.'}), 503

    basic = get_food_basic(USDA_ENGINE, fdc_id)
    if not basic:
        return jsonify({'error': f'fdc_id {fdc_id} not found'}), 404

    facts = get_basic_nutrients(USDA_ENGINE, fdc_id)

    session = SessionLocal()
    try:
        # idempotent create by name/brand
        name = basic.get('description')
        brand = basic.get('brand_name') or basic.get('brand_owner')
        upc = basic.get('gtin_upc')

        existing = (
            session.query(FoodItem)
            .filter(FoodItem.name == name)
            .filter(FoodItem.brand == brand)
            .filter(FoodItem.upc == upc)
            .first()
        )
        item = existing
        if not item:
            item = FoodItem(
                name=name,
                brand=brand,
                category=None,
                upc=upc,
                is_perishable=True,
            )
            session.add(item)
            session.flush()

        # Upsert nutrition facts
        if item.nutrition:
            session.delete(item.nutrition)
            session.flush()

        nf = NutritionFacts(
            food_item_id=item.id,
            serving_size=basic.get('serving_size'),
            serving_unit=basic.get('serving_size_unit'),
            calories=facts.get('calories'),
            protein_g=facts.get('protein_g'),
            carbs_g=facts.get('carbs_g'),
            fat_g=facts.get('fat_g'),
            fiber_g=facts.get('fiber_g'),
            sugar_g=facts.get('sugar_g'),
        )
        session.add(nf)
        session.commit()
        return jsonify({'food_item_id': item.id}), 201
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI-powered nutrition chat using MosaicML"""
    print(f"🔥 [AI Chat] Starting request processing at {time.time()}")
    
    try:
        print("📝 [AI Chat] Parsing request data...")
        data = request.get_json()
        user_message = data.get('message', '').strip() if data else ''
        
        print(f"💬 [AI Chat] User message: {user_message[:100]}...")
        
        if not user_message:
            print("❌ [AI Chat] Empty message received")
            return jsonify({'error': 'Message is required'}), 400
        
        print("🤖 [AI Chat] Calling MosaicML AI service...")
        # Generate AI response using MosaicML
        ai_response = mosaic_nutrition_ai.generate_nutrition_advice(user_message)
        
        print(f"✅ [AI Chat] Response generated: {len(ai_response)} characters")
        
        # Try to extract macros JSON from the AI response
        macros = None
        try:
            macros = mosaic_nutrition_ai.extract_macros_json(ai_response)
        except Exception:
            macros = None
        
        response_data = {
            'user_message': user_message,
            'ai_response': ai_response,
            'macros': macros,
            'timestamp': time.time(),
            'powered_by': 'MosaicML (Databricks Open Source)'
        }
        
        print("📤 [AI Chat] Returning response to client")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ [AI Chat] Error occurred: {str(e)}")
        print(f"❌ [AI Chat] Error type: {type(e)}")
        import traceback
        print(f"❌ [AI Chat] Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'error': f'MosaicML service error: {str(e)}',
            'error_type': str(type(e)),
            'timestamp': time.time()
        }), 500


@app.route('/api/ai/status', methods=['GET'])
def ai_status():
    """Check if MosaicML AI is ready"""
    ai_ready = mosaic_nutrition_ai.is_ready()
    return jsonify({
        'ai_ready': ai_ready,
        'service': 'MosaicML',
        'model': 'Databricks Open Source',
        'status': 'ready' if ai_ready else 'initializing'
    })


@app.route('/api/ai/recipe-suggestions', methods=['POST'])
def ai_recipe_suggestions():
    """AI-powered recipe suggestions based on user's grocery inventory"""
    print(f"🍳 [Recipe Suggestions] Starting request processing at {time.time()}")
    
    try:
        print("📝 [Recipe Suggestions] Parsing request data...")
        data = request.get_json()
        user_message = data.get('message', 'What can I cook with my available groceries?').strip()
        user_id = data.get('user_id', 'demo_user')
        
        print(f"💬 [Recipe Suggestions] User message: {user_message}")
        print(f"👤 [Recipe Suggestions] User ID: {user_id}")
        
        if not user_message:
            print("❌ [Recipe Suggestions] Empty message received")
            return jsonify({'error': 'Message is required'}), 400
        
        print("🤖 [Recipe Suggestions] Calling inventory-aware AI...")
        # Generate recipe suggestions based on user's groceries
        ai_response = mosaic_nutrition_ai.suggest_recipes_with_inventory(user_message, user_id)
        
        print(f"✅ [Recipe Suggestions] Suggestions generated: {len(ai_response)} characters")
        
        # Try to extract macros JSON from the AI response
        macros = None
        try:
            macros = mosaic_nutrition_ai.extract_macros_json(ai_response)
        except Exception:
            macros = None
        
        response_data = {
            'user_message': user_message,
            'user_id': user_id,
            'recipe_suggestions': ai_response,
            'macros': macros,
            'timestamp': time.time(),
            'powered_by': 'MosaicML + User Grocery Inventory',
            'feature': 'inventory_aware_recipes'
        }
        
        print("📤 [Recipe Suggestions] Returning suggestions to client")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ [Recipe Suggestions] Error occurred: {str(e)}")
        print(f"❌ [Recipe Suggestions] Error type: {type(e)}")
        import traceback
        print(f"❌ [Recipe Suggestions] Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'error': f'Recipe suggestion service error: {str(e)}',
            'error_type': str(type(e)),
            'timestamp': time.time()
        }), 500


# Recipe Generation Endpoints
@app.route('/api/recipes/generate', methods=['POST'])
def generate_recipe():
    """Generate a single recipe based on parameters"""
    try:
        data = request.get_json() or {}
        
        # Extract parameters
        meal_type = data.get('meal_type', 'dinner')
        dietary_preferences = data.get('dietary_preferences', [])
        nutrition_goals = data.get('nutrition_goals', {})
        servings = data.get('servings', 2)
        
        # Recipe generation not yet implemented - return placeholder
        return jsonify({'error': 'Recipe generation feature coming soon!'}), 501
        
    except Exception as e:
        return jsonify({'error': f'Recipe generation error: {str(e)}'}), 500


@app.route('/api/recipes/meal-plan', methods=['POST'])
def generate_meal_plan():
    """Generate a complete meal plan"""
    try:
        data = request.get_json() or {}
        
        # Extract parameters
        days = data.get('days', 7)
        meals_per_day = data.get('meals_per_day', 3)
        
        # Meal plan generation not yet implemented - return placeholder
        return jsonify({'error': 'Meal plan generation feature coming soon!'}), 501
        
    except Exception as e:
        return jsonify({'error': f'Meal plan generation error: {str(e)}'}), 500


@app.route('/api/recipes/suggestions', methods=['GET'])
def recipe_suggestions():
    """Get recipe suggestions based on available ingredients or preferences"""
    try:
        # Get query parameters
        ingredients = request.args.get('ingredients', '').split(',') if request.args.get('ingredients') else []
        meal_type = request.args.get('meal_type', 'dinner')
        dietary_pref = request.args.get('dietary', '').split(',') if request.args.get('dietary') else []
        
        # Recipe suggestions not yet implemented - return placeholder  
        return jsonify({'error': 'Recipe suggestions feature coming soon!'}), 501
        
    except Exception as e:
        return jsonify({'error': f'Suggestion generation error: {str(e)}'}), 500


# Advanced Databricks Recipe Generation Endpoints
@app.route('/api/recipes/databricks/generate', methods=['POST'])
def generate_databricks_recipe():
    """Generate recipe using Databricks Model Serving with advanced features"""
    try:
        data = request.get_json() or {}
        
        # Extract enhanced parameters
        ingredients = data.get('ingredients', [])
        meal_type = data.get('meal_type', 'dinner')
        dietary_preferences = data.get('dietary_preferences', [])
        nutrition_goals = data.get('nutrition_goals', {})
        cuisine_style = data.get('cuisine_style', 'international')
        servings = data.get('servings', 2)
        cooking_time = data.get('cooking_time')
        skill_level = data.get('skill_level', 'intermediate')
        
        # Databricks recipe generation not yet implemented - return placeholder
        return jsonify({'error': 'Databricks recipe generation feature coming soon!'}), 501
        
    except Exception as e:
        return jsonify({'error': f'Databricks recipe generation error: {str(e)}'}), 500


@app.route('/api/recipes/databricks/batch', methods=['POST'])
def generate_batch_recipes():
    """Generate multiple recipes with variety using Databricks"""
    try:
        data = request.get_json() or {}
        
        count = data.get('count', 5)
        variety_params = data.get('variety_params')
        
        # Batch recipe generation not yet implemented - return placeholder
        return jsonify({'error': 'Batch recipe generation feature coming soon!'}), 501
        
    except Exception as e:
        return jsonify({'error': f'Batch recipe generation error: {str(e)}'}), 500


@app.route('/api/recipes/databricks/status', methods=['GET'])
def databricks_status():
    """Check Databricks Model Serving status"""
    try:
        # Databricks status check not yet implemented - return placeholder
        return jsonify({
            'databricks_available': False,
            'service': 'Databricks Model Serving',
            'status': 'not_configured',
            'message': 'Databricks integration coming soon!'
        })
        
    except Exception as e:
        return jsonify({'error': f'Status check error: {str(e)}'}), 500


# Register grocery management endpoints
try:
    from grocery_endpoints import register_grocery_routes
    register_grocery_routes(app)
    print("✅ Grocery management endpoints registered")
except ImportError as e:
    print(f"⚠️  Could not import grocery endpoints: {e}")
except Exception as e:
    print(f"❌ Error registering grocery endpoints: {e}")

# Register favorites endpoints
try:
    from favorites_endpoints import register_favorites_routes
    register_favorites_routes(app)
    print("✅ Favorites endpoints registered")
except ImportError as e:
    print(f"⚠️  Could not import favorites endpoints: {e}")
except Exception as e:
    print(f"❌ Error registering favorites endpoints: {e}")


if __name__ == '__main__':
    # Run without reloader to avoid duplicate processes and port conflicts
    app.run(debug=False, port=5001, use_reloader=False)
