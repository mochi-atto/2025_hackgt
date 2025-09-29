"""
Favorites API Endpoints
Manage user's favorite ingredients (USDA items or custom foods)
"""

from flask import jsonify, request
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

# Import database components
try:
    from .db import SessionLocal
    from .models import FoodItem, CustomFood, UserFavorite
except ImportError:
    import os, sys
    sys.path.append(os.path.dirname(__file__))
    from db import SessionLocal
    from models import FoodItem, CustomFood, UserFavorite


def register_favorites_routes(app):
    """Register favorites routes with the Flask app."""

    @app.route('/api/favorites', methods=['GET'])
    def list_favorites():
        user_id = request.args.get('user_id', 'demo_user')
        session = SessionLocal()
        try:
            favs = (
                session.query(UserFavorite)
                .filter(UserFavorite.user_id == user_id)
                .options(joinedload(UserFavorite.food_item), joinedload(UserFavorite.custom_food))
                .order_by(UserFavorite.created_at.desc())
                .all()
            )
            result = []
            for f in favs:
                if f.food_item:
                    item = {
                        'id': f.id,
                        'type': 'usda',
                        'user_id': f.user_id,
                        'food_item_id': f.food_item_id,
                        'display_name': f.display_name or f.food_item.name,
                        'notes': f.notes,
                        'created_at': f.created_at.isoformat(),
                        'food_info': {
                            'name': f.food_item.name,
                            'brand': f.food_item.brand,
                            'category': f.food_item.category,
                        },
                    }
                else:
                    item = {
                        'id': f.id,
                        'type': 'custom',
                        'user_id': f.user_id,
                        'custom_food_id': f.custom_food_id,
                        'display_name': f.display_name or f.custom_food.name,
                        'notes': f.notes,
                        'created_at': f.created_at.isoformat(),
                        'food_info': {
                            'name': f.custom_food.name,
                            'description': f.custom_food.description,
                        },
                    }
                result.append(item)
            return jsonify({'favorites': result, 'total_count': len(result)})
        finally:
            session.close()

    @app.route('/api/favorites', methods=['POST'])
    def add_favorite():
        data = request.get_json() or {}
        user_id = data.get('user_id', 'demo_user')
        food_item_id = data.get('food_item_id')
        custom_food_id = data.get('custom_food_id')
        display_name = data.get('display_name')
        notes = data.get('notes')
        
        # Handle USDA items from search results
        fdc_id = data.get('fdc_id')  # For USDA items from search
        source = data.get('source')  # "usda" for USDA items
        
        # Handle USDA items - try to find existing or import if needed
        if source == 'usda' and fdc_id and not food_item_id:
            print(f"🔄 Processing USDA item with FDC ID: {fdc_id}, display_name: '{display_name}'")
            
            # First, check if we already have this as a FoodItem
            lookup_session = SessionLocal()
            try:
                # Try to find by display name or similar name patterns
                search_conditions = [FoodItem.name.ilike(f'%{display_name}%')]
                
                # Add specific food type searches
                display_lower = display_name.lower()
                if 'chicken' in display_lower:
                    search_conditions.append(FoodItem.name.ilike('%chicken%'))
                if 'milk' in display_lower:
                    search_conditions.append(FoodItem.name.ilike('%milk%'))
                if 'beef' in display_lower:
                    search_conditions.append(FoodItem.name.ilike('%beef%'))
                if 'egg' in display_lower:
                    search_conditions.append(FoodItem.name.ilike('%egg%'))
                
                potential_matches = lookup_session.query(FoodItem).filter(
                    or_(*search_conditions)
                ).limit(5).all()
                
                print(f"🔍 Found {len(potential_matches)} potential matches in FoodItems")
                for match in potential_matches:
                    print(f"  - ID: {match.id}, Name: '{match.name}', Category: '{match.category}'")
                
                # Use the first reasonable match, or try USDA import
                if potential_matches:
                    # Use the first match
                    existing_food = potential_matches[0]
                    food_item_id = existing_food.id
                    display_name = display_name or existing_food.name
                    print(f"✅ Using existing FoodItem ID: {food_item_id}")
                else:
                    print(f"🔄 No existing FoodItem found, attempting USDA import...")
                    
                    # Try to import from USDA
                    try:
                        from usda_queries import get_food_basic, get_basic_nutrients
                        from usda_db import get_usda_engine
                        
                        usda_engine = get_usda_engine()
                        if usda_engine:
                            basic = get_food_basic(usda_engine, fdc_id)
                            
                            if basic:
                                food_name = basic.get('description') or display_name
                                brand = basic.get('brand_name') or basic.get('brand_owner')
                                category = data.get('category') or basic.get('data_type') or 'USDA Food'
                                upc = basic.get('gtin_upc')
                                
                                # Create new FoodItem
                                new_food = FoodItem(
                                    name=food_name,
                                    brand=brand,
                                    category=category,
                                    upc=upc,
                                    is_perishable=True
                                )
                                lookup_session.add(new_food)
                                lookup_session.flush()
                                
                                # Add nutrition if available
                                facts = get_basic_nutrients(usda_engine, fdc_id)
                                if facts:
                                    from models import NutritionFacts
                                    nutrition = NutritionFacts(
                                        food_item_id=new_food.id,
                                        calories=facts.get('calories'),
                                        protein_g=facts.get('protein_g'),
                                        carbs_g=facts.get('carbs_g'),
                                        fat_g=facts.get('fat_g'),
                                        fiber_g=facts.get('fiber_g'),
                                        sugar_g=facts.get('sugar_g')
                                    )
                                    lookup_session.add(nutrition)
                                
                                lookup_session.commit()
                                food_item_id = new_food.id
                                display_name = display_name or food_name
                                print(f"✅ Created new FoodItem ID: {food_item_id}")
                            else:
                                print(f"❌ No USDA data found for FDC ID: {fdc_id}")
                                raise Exception(f"No USDA data for FDC {fdc_id}")
                        else:
                            print(f"❌ USDA engine not available")
                            raise Exception("USDA engine not available")
                    except Exception as usda_error:
                        lookup_session.rollback()
                        print(f"💥 USDA import failed: {usda_error}")
                        # Fall back to custom food
                        from models import CustomFood
                        custom_food = CustomFood(
                            name=display_name,
                            description=f"USDA item (FDC: {fdc_id}) - Import failed",
                            user_id=user_id
                        )
                        lookup_session.add(custom_food)
                        lookup_session.commit()
                        custom_food_id = custom_food.id
                        print(f"🔄 Created CustomFood ID: {custom_food_id}")
                        
            finally:
                lookup_session.close()

        # Validate one-of after potential USDA import
        if bool(food_item_id) == bool(custom_food_id):
            return jsonify({'error': 'Provide exactly one of food_item_id or custom_food_id, or provide USDA item details'}), 400

        session = SessionLocal()
        try:
            # Prevent duplicates
            exists = (
                session.query(UserFavorite)
                .filter(
                    UserFavorite.user_id == user_id,
                    (UserFavorite.food_item_id == food_item_id) if food_item_id else (UserFavorite.custom_food_id == custom_food_id),
                )
                .first()
            )
            if exists:
                return jsonify({'error': 'Already in favorites', 'favorite_id': exists.id}), 409

            fav = UserFavorite(
                user_id=user_id,
                food_item_id=food_item_id,
                custom_food_id=custom_food_id,
                display_name=display_name,
                notes=notes,
            )
            session.add(fav)
            session.commit()
            return jsonify({'id': fav.id, 'message': 'Added to favorites'}), 201
        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Failed to add favorite: {str(e)}'}), 500
        finally:
            session.close()

    @app.route('/api/favorites/<int:fav_id>', methods=['DELETE'])
    def delete_favorite(fav_id: int):
        user_id = request.args.get('user_id', 'demo_user')
        session = SessionLocal()
        try:
            fav = (
                session.query(UserFavorite)
                .filter(UserFavorite.id == fav_id, UserFavorite.user_id == user_id)
                .first()
            )
            if not fav:
                return jsonify({'error': 'Favorite not found'}), 404
            session.delete(fav)
            session.commit()
            return jsonify({'message': 'Favorite removed'})
        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Failed to delete favorite: {str(e)}'}), 500
        finally:
            session.close()