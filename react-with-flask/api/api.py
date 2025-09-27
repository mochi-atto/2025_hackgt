import time
from flask import Flask, jsonify, request

# Robust imports to work both as a module and as a script
try:
    from .db import init_db, SessionLocal
    from .models import FoodItem, NutritionFacts
    from .usda_db import USDA_ENGINE
    from .usda_queries import search_usda, lookup_upc, get_basic_nutrients, get_food_basic
except ImportError:  # Running as a script
    import os, sys
    sys.path.append(os.path.dirname(__file__))
    from db import init_db, SessionLocal
    from models import FoodItem, NutritionFacts
    from usda_db import USDA_ENGINE
    from usda_queries import search_usda, lookup_upc, get_basic_nutrients, get_food_basic

app = Flask(__name__)

# Initialize database and tables on startup
init_db()


@app.route('/api/time')
def get_current_time():
    return {'time': time.time()}


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


@app.get('/api/usda/debug/<int:fdc_id>')
def api_usda_debug(fdc_id: int):
    """Debug endpoint to check nutrition data availability"""
    if USDA_ENGINE is None:
        return jsonify({'error': 'USDA DB not found'}), 503
    
    # Check basic food info
    basic = get_food_basic(USDA_ENGINE, fdc_id)
    
    # Check raw nutrient data
    from sqlalchemy import text
    sql = text("""
        SELECT fn.nutrient_id, n.name, n.unit_name, fn.amount
        FROM food_nutrient fn
        LEFT JOIN nutrient n ON n.id = fn.nutrient_id
        WHERE fn.fdc_id = :fdc_id
        LIMIT 10
    """)
    
    with USDA_ENGINE.connect() as conn:
        raw_nutrients = conn.execute(sql, {"fdc_id": fdc_id}).fetchall()
    
    nutrients_data = [dict(row._mapping) for row in raw_nutrients]
    
    # Check processed nutrients
    processed_nutrients = get_basic_nutrients(USDA_ENGINE, fdc_id)
    
    return jsonify({
        'fdc_id': fdc_id,
        'basic_info': basic,
        'raw_nutrients_sample': nutrients_data,
        'processed_nutrients': processed_nutrients
    })


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


if __name__ == '__main__':
    app.run(debug=True, port=5001)
