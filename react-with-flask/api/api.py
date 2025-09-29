import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy.orm import joinedload
import re

# Load environment variables (for OPENAI_KEY in .env)
import os
try:
    from dotenv import load_dotenv, find_dotenv
    # Find .env starting from here and upwards (project root has .env)
    env_file = find_dotenv()
    if env_file:
        print(f"📄 Loading .env from: {env_file}")
        load_dotenv(env_file, override=True)
        print(f"🔑 OPENAI_KEY loaded: {'Yes' if os.getenv('OPENAI_KEY') else 'No'}")
    else:
        print("⚠️  No .env file found")
except Exception as e:
    print(f"❌ Error loading .env: {e}")
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
# Configure CORS for React frontend
# Get allowed origins from environment or use defaults
allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
if os.getenv('FLASK_ENV') == 'production':
    # Add your Render frontend URL here
    allowed_origins.extend([
        'https://your-react-frontend.onrender.com',
        'https://*.onrender.com'  # Allow any Render subdomain
    ])

CORS(app, origins=allowed_origins, 
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Initialize database and tables on startup
init_db()


def get_smart_expiration_days(food_name: str, category: str = None, data_type: str = None) -> int:
    """Calculate smart expiration days based on food type and name."""
    food_name_lower = food_name.lower()
    category_lower = (category or '').lower()
    data_type_lower = (data_type or '').lower()
    
    # Very perishable items (1-3 days)
    very_perishable = [
        'lettuce', 'spinach', 'arugula', 'kale', 'mixed greens', 'salad',
        'berries', 'strawberries', 'raspberries', 'blackberries', 'blueberries',
        'mushrooms', 'sprouts', 'herbs', 'basil', 'cilantro', 'parsley',
        'fish', 'seafood', 'shrimp', 'crab', 'lobster', 'salmon', 'tuna',
        'ground meat', 'ground beef', 'ground chicken', 'ground turkey'
    ]
    
    # Short-term perishable (3-7 days)
    short_term = [
        'broccoli', 'cauliflower', 'asparagus', 'green beans', 'peas',
        'bananas', 'avocado', 'tomatoes', 'cucumber', 'zucchini', 'bell pepper',
        'milk', 'cream', 'yogurt', 'sour cream', 'cottage cheese',
        'chicken breast', 'chicken thigh', 'pork', 'beef steak', 'fresh meat',
        'bread', 'bagels', 'muffins', 'croissant'
    ]
    
    # Medium-term perishable (1-2 weeks)
    medium_term = [
        'carrots', 'celery', 'cabbage', 'onions', 'garlic',
        'apples', 'oranges', 'lemons', 'limes', 'grapes', 'pears',
        'cheese', 'cheddar', 'mozzarella', 'swiss', 'parmesan',
        'eggs', 'butter', 'margarine'
    ]
    
    # Long-term items (3-4 weeks)
    long_term = [
        'potatoes', 'sweet potatoes', 'winter squash', 'pumpkin',
        'whole grain bread', 'tortillas'
    ]
    
    # Very long-term / pantry items (6+ months)
    pantry_items = [
        'rice', 'pasta', 'beans', 'lentils', 'quinoa', 'oats',
        'flour', 'sugar', 'salt', 'spices', 'oil', 'vinegar',
        'canned', 'frozen', 'dried', 'cereal', 'crackers', 'nuts'
    ]
    
    # Check by specific food name keywords
    for item in very_perishable:
        if item in food_name_lower:
            return 2  # 2 days
    
    for item in short_term:
        if item in food_name_lower:
            return 5  # 5 days
    
    for item in medium_term:
        if item in food_name_lower:
            return 10  # 10 days
    
    for item in long_term:
        if item in food_name_lower:
            return 21  # 3 weeks
    
    for item in pantry_items:
        if item in food_name_lower:
            return 180  # 6 months
    
    # Check by category/data_type
    if any(x in category_lower for x in ['produce', 'vegetable', 'fruit']):
        # Fresh produce - shorter expiration
        if any(x in food_name_lower for x in ['lettuce', 'greens', 'berries']):
            return 2
        else:
            return 7  # 1 week for most produce
    
    if any(x in category_lower for x in ['dairy', 'milk']):
        return 7  # 1 week for dairy
    
    if any(x in category_lower for x in ['meat', 'poultry', 'seafood']):
        return 3  # 3 days for fresh meat
    
    if any(x in category_lower for x in ['frozen']):
        return 90  # 3 months for frozen items
    
    if any(x in category_lower for x in ['canned', 'pantry']):
        return 365  # 1 year for canned/pantry items
    
    if data_type_lower == 'branded_food':
        # Processed foods typically last longer
        return 30  # 1 month
    
    # Default fallback
    return 14  # 2 weeks


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


@app.get('/api/search')
def api_unified_search():
    """Unified search endpoint for dashboard compatibility - searches both USDA and local foods"""
    query = (request.args.get('query') or '').strip()
    limit = int(request.args.get('limit', '20'))
    favorites_only = request.args.get('favorites_only', '').lower() == 'true'
    user_id = request.args.get('user_id', 'demo_user')
    
    results = []
    
    # Import models for favorites
    from models import UserFavorite
    
    session = SessionLocal()
    try:
        if favorites_only:
            # Search only user's favorites
            favs = (
                session.query(UserFavorite)
                .filter(UserFavorite.user_id == user_id)
                .options(joinedload(UserFavorite.food_item), joinedload(UserFavorite.custom_food))
                .order_by(UserFavorite.created_at.desc())
                .all()
            )
            
            for fav in favs:
                if query and query.lower() not in (fav.display_name or '').lower():
                    # If there's a search query, filter by it
                    if fav.food_item and query.lower() not in fav.food_item.name.lower():
                        continue
                    elif fav.custom_food and query.lower() not in fav.custom_food.name.lower():
                        continue
                
                if fav.food_item:
                    item = {
                        'id': f"local_{fav.food_item.id}",
                        'name': fav.display_name or fav.food_item.name,
                        'category': fav.food_item.category,
                        'brand': fav.food_item.brand,
                        'source': 'local',
                        'food_item_id': fav.food_item.id,
                        'is_favorite': True,
                        'favorite_id': fav.id
                    }
                elif fav.custom_food:
                    item = {
                        'id': f"custom_{fav.custom_food.id}",
                        'name': fav.display_name or fav.custom_food.name,
                        'category': 'Custom Food',
                        'brand': None,
                        'source': 'custom',
                        'custom_food_id': fav.custom_food.id,
                        'is_favorite': True,
                        'favorite_id': fav.id
                    }
                
                results.append(item)
                if len(results) >= limit:
                    break
        else:
            # Regular search with favorite status
            if not query:
                return jsonify([])
                
            # Get user's favorites to mark them in results
            user_favorites = {}
            favs = (
                session.query(UserFavorite)
                .filter(UserFavorite.user_id == user_id)
                .all()
            )
            for fav in favs:
                if fav.food_item_id:
                    user_favorites[f"local_{fav.food_item_id}"] = fav.id
                elif fav.custom_food_id:
                    user_favorites[f"custom_{fav.custom_food_id}"] = fav.id
            
            # Search USDA database first
            if USDA_ENGINE is not None:
                try:
                    usda_results = search_usda(USDA_ENGINE, query, limit)
                    for result in usda_results:
                        # Transform USDA results to match dashboard expectations
                        item_id = f"usda_{result.get('fdc_id')}"
                        item = {
                            'id': item_id,
                            'name': result.get('description', ''),
                            'category': result.get('data_type', ''),
                            'brand': result.get('brand_name') or result.get('brand_owner'),
                            'source': 'usda',
                            'fdc_id': result.get('fdc_id'),
                            'is_favorite': item_id in user_favorites,
                            'favorite_id': user_favorites.get(item_id)
                        }
                        results.append(item)
                except Exception as e:
                    print(f"USDA search error: {e}")
            
            # Search local food items
            local_foods = session.query(FoodItem).filter(
                FoodItem.name.ilike(f'%{query}%')
            ).limit(limit - len(results)).all()
            
            for food in local_foods:
                item_id = f"local_{food.id}"
                item = {
                    'id': item_id,
                    'name': food.name,
                    'category': food.category,
                    'brand': food.brand,
                    'source': 'local',
                    'food_item_id': food.id,
                    'is_favorite': item_id in user_favorites,
                    'favorite_id': user_favorites.get(item_id)
                }
                results.append(item)
    
    except Exception as e:
        print(f"Search error: {e}")
    finally:
        session.close()
    
    return jsonify(results[:limit])


# Fridge API endpoints for dashboard compatibility (wraps grocery endpoints)
@app.route('/api/fridge', methods=['GET'])
def api_get_fridge_items():
    """Get user's fridge items - compatibility wrapper for grocery endpoints"""
    user_id = request.args.get('user_id', 'demo_user')
    
    session = SessionLocal()
    try:
        groceries = session.query(UserGrocery).filter(
            UserGrocery.user_id == user_id,
            UserGrocery.is_expired == False
        ).options(
            joinedload(UserGrocery.food_item).joinedload(FoodItem.nutrition),
            joinedload(UserGrocery.custom_food)
        ).order_by(UserGrocery.created_at.desc()).all()
        
        result = []
        for grocery in groceries:
            # Transform grocery data to match frontend expectations
            food_info = {}
            item_type = 'unknown'
            
            if grocery.food_item:
                # This is a USDA item (imported from USDA database)
                food_info = {
                    'name': grocery.food_item.name,
                    'brand': grocery.food_item.brand,
                    'category': grocery.food_item.category,
                }
                item_type = 'usda'
            elif grocery.custom_food:
                # This is a custom food item
                food_info = {
                    'name': grocery.custom_food.name,
                    'brand': None,
                    'category': 'Custom Food',
                }
                item_type = 'custom'
            
            item = {
                'id': grocery.id,
                'name': food_info.get('name', ''),
                'brand': food_info.get('brand'),
                'category': food_info.get('category'),
                'type': item_type,  # Add type field to distinguish USDA vs custom
                'quantity': grocery.quantity,
                'unit': grocery.unit,
                'expiry_date': grocery.expiration_date.isoformat() if grocery.expiration_date else None,
                'created_at': grocery.created_at.isoformat(),
                'updated_at': grocery.updated_at.isoformat()
            }
            result.append(item)
        
        return jsonify(result)
        
    finally:
        session.close()


@app.route('/api/fridge', methods=['POST'])
def api_add_fridge_item():
    """Add item to fridge - compatibility wrapper for grocery endpoints"""
    data = request.get_json()
    user_id = data.get('user_id', 'demo_user')
    
    # Handle both USDA and local items from search results
    item_id = data.get('item_id')
    name = data.get('name', '')
    category = data.get('category')
    
    session = SessionLocal()
    try:
        # Calculate smart expiration date based on food type
        smart_days = get_smart_expiration_days(name, category)
        default_expiry = datetime.now().date() + timedelta(days=smart_days)
        
        print(f"🎯 Smart expiry for '{name}' (category: {category}): {smart_days} days → {default_expiry}")
        
        grocery = UserGrocery(
            user_id=user_id,
            quantity=1.0,
            unit='items',
            location='fridge',
            expiration_date=default_expiry
        )
        
        # Determine if this is a USDA item or needs to be created as custom
        if item_id and item_id.startswith('usda_'):
            # Extract USDA FDC ID and import the item first
            fdc_id_str = item_id.replace('usda_', '')
            try:
                fdc_id = int(fdc_id_str)
                # Try to import from USDA first
                from usda_queries import get_food_basic, get_basic_nutrients
                if USDA_ENGINE:
                    basic = get_food_basic(USDA_ENGINE, fdc_id)
                    facts = get_basic_nutrients(USDA_ENGINE, fdc_id)
                    
                    if basic:
                        # Create local FoodItem
                        food_name = basic.get('description')
                        brand = basic.get('brand_name') or basic.get('brand_owner')
                        upc = basic.get('gtin_upc')
                        
                        # Check if already exists
                        existing_food = session.query(FoodItem).filter(
                            FoodItem.name == food_name,
                            FoodItem.brand == brand,
                            FoodItem.upc == upc
                        ).first()
                        
                        if not existing_food:
                            existing_food = FoodItem(
                                name=food_name,
                                brand=brand,
                                category=category,
                                upc=upc,
                                is_perishable=True
                            )
                            session.add(existing_food)
                            session.flush()
                            
                            # Add nutrition facts
                            if facts:
                                nutrition = NutritionFacts(
                                    food_item_id=existing_food.id,
                                    calories=facts.get('calories'),
                                    protein_g=facts.get('protein_g'),
                                    carbs_g=facts.get('carbs_g'),
                                    fat_g=facts.get('fat_g'),
                                    fiber_g=facts.get('fiber_g'),
                                    sugar_g=facts.get('sugar_g')
                                )
                                session.add(nutrition)
                        
                        grocery.food_item_id = existing_food.id
                    else:
                        # Fall back to custom food
                        custom_food = CustomFood(
                            name=name,
                            description=f"Imported from search: {name}",
                            user_id=user_id
                        )
                        session.add(custom_food)
                        session.flush()
                        grocery.custom_food_id = custom_food.id
            except (ValueError, TypeError):
                # Invalid FDC ID format, create as custom food
                custom_food = CustomFood(
                    name=name,
                    description=f"Added from search: {name}",
                    user_id=user_id
                )
                session.add(custom_food)
                session.flush()
                grocery.custom_food_id = custom_food.id
                
        elif item_id and item_id.startswith('local_'):
            # Local food item - extract the ID
            local_id_str = item_id.replace('local_', '')
            try:
                local_id = int(local_id_str)
                grocery.food_item_id = local_id
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid local food item ID'}), 400
        else:
            # Create as custom food
            custom_food = CustomFood(
                name=name,
                description=f"Added manually: {name}",
                user_id=user_id
            )
            session.add(custom_food)
            session.flush()
            grocery.custom_food_id = custom_food.id
        
        session.add(grocery)
        session.commit()
        
        return jsonify({
            'id': grocery.id,
            'message': f'{name} added to fridge successfully'
        }), 201
        
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Failed to add item: {str(e)}'}), 500
    finally:
        session.close()


@app.route('/api/fridge/<int:item_id>', methods=['PUT'])
def api_update_fridge_item(item_id: int):
    """Update fridge item - compatibility wrapper for grocery endpoints"""
    data = request.get_json()
    user_id = data.get('user_id', 'demo_user')
    
    session = SessionLocal()
    try:
        grocery = session.query(UserGrocery).filter(
            UserGrocery.id == item_id,
            UserGrocery.user_id == user_id
        ).first()
        
        if not grocery:
            return jsonify({'error': 'Item not found'}), 404
        
        # Update fields if provided
        if 'quantity' in data:
            grocery.quantity = float(data['quantity'])
        if 'unit' in data:
            grocery.unit = data['unit']
        if 'expiry_date' in data:
            if data['expiry_date']:
                grocery.expiration_date = datetime.fromisoformat(data['expiry_date']).date()
            else:
                grocery.expiration_date = None
        if 'created_at' in data:
            if data['created_at']:
                # Update purchase date instead of created_at
                grocery.purchase_date = datetime.fromisoformat(data['created_at']).date()
        
        grocery.updated_at = datetime.utcnow()
        session.commit()
        
        return jsonify({
            'id': grocery.id,
            'message': 'Item updated successfully'
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Failed to update item: {str(e)}'}), 500
    finally:
        session.close()


@app.route('/api/fridge/<int:item_id>', methods=['DELETE'])
def api_delete_fridge_item(item_id: int):
    """Delete fridge item - compatibility wrapper for grocery endpoints"""
    user_id = request.args.get('user_id', 'demo_user')
    
    session = SessionLocal()
    try:
        grocery = session.query(UserGrocery).filter(
            UserGrocery.id == item_id,
            UserGrocery.user_id == user_id
        ).first()
        
        if not grocery:
            return jsonify({'error': 'Item not found'}), 404
        
        session.delete(grocery)
        session.commit()
        
        return jsonify({'message': 'Item removed from fridge'})
        
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Failed to delete item: {str(e)}'}), 500
    finally:
        session.close()


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
