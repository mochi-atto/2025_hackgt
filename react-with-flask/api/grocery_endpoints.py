"""
Grocery Management API Endpoints
Handles user grocery tracking, expiration dates, and custom foods
"""

import time
from datetime import date, datetime, timedelta
from flask import jsonify, request
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import joinedload

# Import database components
try:
    from .db import SessionLocal
    from .models import FoodItem, NutritionFacts, CustomFood, UserGrocery
    from .usda_db import USDA_ENGINE
    from .usda_queries import get_basic_nutrients, get_food_basic
except ImportError:
    import os, sys
    sys.path.append(os.path.dirname(__file__))
    from db import SessionLocal
    from models import FoodItem, NutritionFacts, CustomFood, UserGrocery
    from usda_db import USDA_ENGINE
    from usda_queries import get_basic_nutrients, get_food_basic


def register_grocery_routes(app):
    """Register all grocery management routes with the Flask app"""
    
    # ============================================
    # USER GROCERY INVENTORY ENDPOINTS
    # ============================================
    
    @app.route('/api/groceries', methods=['GET'])
    def get_user_groceries():
        """Get user's current grocery inventory"""
        user_id = request.args.get('user_id', 'demo_user')
        include_expired = request.args.get('include_expired', 'false').lower() == 'true'
        
        session = SessionLocal()
        try:
            query = session.query(UserGrocery).filter(UserGrocery.user_id == user_id)
            
            if not include_expired:
                query = query.filter(UserGrocery.is_expired == False)
            
            groceries = query.options(
                joinedload(UserGrocery.food_item).joinedload(FoodItem.nutrition),
                joinedload(UserGrocery.custom_food)
            ).order_by(UserGrocery.expiration_date.asc()).all()
            
            result = []
            today = date.today()
            
            for grocery in groceries:
                # Calculate days until expiration
                days_until_expiry = None
                expiry_status = "unknown"
                if grocery.expiration_date:
                    days_until_expiry = (grocery.expiration_date - today).days
                    if days_until_expiry < 0:
                        expiry_status = "expired"
                    elif days_until_expiry <= 3:
                        expiry_status = "expiring_soon"
                    elif days_until_expiry <= 7:
                        expiry_status = "expiring_this_week"
                    else:
                        expiry_status = "fresh"
                
                # Get food info (USDA or custom)
                food_info = {}
                if grocery.food_item:
                    food_info = {
                        'type': 'usda',
                        'name': grocery.food_item.name,
                        'brand': grocery.food_item.brand,
                        'category': grocery.food_item.category,
                        'nutrition': {
                            'calories': grocery.food_item.nutrition.calories if grocery.food_item.nutrition else None,
                            'protein_g': grocery.food_item.nutrition.protein_g if grocery.food_item.nutrition else None,
                            'carbs_g': grocery.food_item.nutrition.carbs_g if grocery.food_item.nutrition else None,
                            'fat_g': grocery.food_item.nutrition.fat_g if grocery.food_item.nutrition else None,
                        } if grocery.food_item.nutrition else None
                    }
                elif grocery.custom_food:
                    food_info = {
                        'type': 'custom',
                        'name': grocery.custom_food.name,
                        'description': grocery.custom_food.description,
                        'nutrition': {
                            'calories': grocery.custom_food.calories,
                            'protein_g': grocery.custom_food.protein_g,
                            'carbs_g': grocery.custom_food.carbs_g,
                            'fat_g': grocery.custom_food.fat_g,
                        },
                        'nutrition_estimated': grocery.custom_food.nutrition_estimated
                    }
                
                result.append({
                    'id': grocery.id,
                    'food_info': food_info,
                    'quantity': grocery.quantity,
                    'unit': grocery.unit,
                    'location': grocery.location,
                    'purchase_date': grocery.purchase_date.isoformat() if grocery.purchase_date else None,
                    'expiration_date': grocery.expiration_date.isoformat() if grocery.expiration_date else None,
                    'opened_date': grocery.opened_date.isoformat() if grocery.opened_date else None,
                    'is_opened': grocery.is_opened,
                    'is_expired': grocery.is_expired,
                    'notes': grocery.notes,
                    'days_until_expiry': days_until_expiry,
                    'expiry_status': expiry_status,
                    'created_at': grocery.created_at.isoformat(),
                    'updated_at': grocery.updated_at.isoformat()
                })
            
            return jsonify({
                'groceries': result,
                'total_items': len(result),
                'expiring_soon': len([g for g in result if g['expiry_status'] == 'expiring_soon']),
                'expired': len([g for g in result if g['expiry_status'] == 'expired'])
            })
            
        finally:
            session.close()
    
    
    @app.route('/api/groceries', methods=['POST'])
    def add_grocery_item():
        """Add a new grocery item to user's inventory"""
        data = request.get_json()
        user_id = data.get('user_id', 'demo_user')
        
        # Required fields
        food_type = data.get('food_type')  # 'usda' or 'custom'
        quantity = data.get('quantity', 1.0)
        unit = data.get('unit', 'unit')
        
        session = SessionLocal()
        try:
            grocery = UserGrocery(
                user_id=user_id,
                quantity=quantity,
                unit=unit,
                location=data.get('location'),
                purchase_date=datetime.fromisoformat(data['purchase_date']).date() if data.get('purchase_date') else None,
                expiration_date=datetime.fromisoformat(data['expiration_date']).date() if data.get('expiration_date') else None,
                is_opened=data.get('is_opened', False),
                notes=data.get('notes')
            )
            
            if food_type == 'usda':
                grocery.food_item_id = data.get('food_item_id')
            elif food_type == 'custom':
                grocery.custom_food_id = data.get('custom_food_id')
            else:
                return jsonify({'error': 'food_type must be "usda" or "custom"'}), 400
            
            session.add(grocery)
            session.commit()
            
            return jsonify({
                'id': grocery.id,
                'message': 'Grocery item added successfully',
                'created_at': grocery.created_at.isoformat()
            }), 201
            
        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Failed to add grocery item: {str(e)}'}), 500
        finally:
            session.close()
    
    
    @app.route('/api/groceries/<int:grocery_id>', methods=['PUT'])
    def update_grocery_item(grocery_id: int):
        """Update a grocery item (quantity, expiration, etc.)"""
        data = request.get_json()
        user_id = data.get('user_id', 'demo_user')
        
        session = SessionLocal()
        try:
            grocery = session.query(UserGrocery).filter(
                UserGrocery.id == grocery_id,
                UserGrocery.user_id == user_id
            ).first()
            
            if not grocery:
                return jsonify({'error': 'Grocery item not found'}), 404
            
            # Update fields if provided
            if 'quantity' in data:
                grocery.quantity = data['quantity']
            if 'unit' in data:
                grocery.unit = data['unit']
            if 'location' in data:
                grocery.location = data['location']
            if 'expiration_date' in data:
                grocery.expiration_date = datetime.fromisoformat(data['expiration_date']).date() if data['expiration_date'] else None
            if 'is_opened' in data:
                grocery.is_opened = data['is_opened']
                if data['is_opened'] and not grocery.opened_date:
                    grocery.opened_date = date.today()
            if 'is_expired' in data:
                grocery.is_expired = data['is_expired']
            if 'notes' in data:
                grocery.notes = data['notes']
            
            grocery.updated_at = datetime.utcnow()
            session.commit()
            
            return jsonify({
                'id': grocery.id,
                'message': 'Grocery item updated successfully',
                'updated_at': grocery.updated_at.isoformat()
            })
            
        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Failed to update grocery item: {str(e)}'}), 500
        finally:
            session.close()
    
    
    @app.route('/api/groceries/<int:grocery_id>', methods=['DELETE'])
    def delete_grocery_item(grocery_id: int):
        """Delete a grocery item from inventory"""
        user_id = request.args.get('user_id', 'demo_user')
        
        session = SessionLocal()
        try:
            grocery = session.query(UserGrocery).filter(
                UserGrocery.id == grocery_id,
                UserGrocery.user_id == user_id
            ).first()
            
            if not grocery:
                return jsonify({'error': 'Grocery item not found'}), 404
            
            session.delete(grocery)
            session.commit()
            
            return jsonify({'message': 'Grocery item deleted successfully'})
            
        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Failed to delete grocery item: {str(e)}'}), 500
        finally:
            session.close()
    
    
    # ============================================
    # CUSTOM FOOD ENDPOINTS
    # ============================================
    
    @app.route('/api/custom-foods', methods=['GET'])
    def get_custom_foods():
        """Get user's custom foods"""
        user_id = request.args.get('user_id', 'demo_user')
        
        session = SessionLocal()
        try:
            custom_foods = session.query(CustomFood).filter(
                or_(CustomFood.user_id == user_id, CustomFood.user_id.is_(None))
            ).order_by(desc(CustomFood.created_at)).all()
            
            result = []
            for food in custom_foods:
                result.append({
                    'id': food.id,
                    'name': food.name,
                    'description': food.description,
                    'serving_size': food.serving_size,
                    'serving_unit': food.serving_unit,
                    'nutrition': {
                        'calories': food.calories,
                        'protein_g': food.protein_g,
                        'carbs_g': food.carbs_g,
                        'fat_g': food.fat_g,
                        'fiber_g': food.fiber_g,
                        'sugar_g': food.sugar_g,
                    },
                    'nutrition_estimated': food.nutrition_estimated,
                    'estimated_confidence': food.estimated_confidence,
                    'user_id': food.user_id,
                    'created_at': food.created_at.isoformat(),
                    'updated_at': food.updated_at.isoformat()
                })
            
            return jsonify({'custom_foods': result, 'total_count': len(result)})
            
        finally:
            session.close()
    
    
    @app.route('/api/custom-foods', methods=['POST'])
    def create_custom_food():
        """Create a new custom food item"""
        data = request.get_json()
        user_id = data.get('user_id', 'demo_user')
        
        session = SessionLocal()
        try:
            custom_food = CustomFood(
                name=data['name'],
                description=data.get('description'),
                serving_size=data.get('serving_size'),
                serving_unit=data.get('serving_unit', 'serving'),
                calories=data.get('calories'),
                protein_g=data.get('protein_g'),
                carbs_g=data.get('carbs_g'),
                fat_g=data.get('fat_g'),
                fiber_g=data.get('fiber_g'),
                sugar_g=data.get('sugar_g'),
                nutrition_estimated=data.get('nutrition_estimated', False),
                estimated_confidence=data.get('estimated_confidence'),
                user_id=user_id
            )
            
            session.add(custom_food)
            session.commit()
            
            return jsonify({
                'id': custom_food.id,
                'name': custom_food.name,
                'message': 'Custom food created successfully',
                'created_at': custom_food.created_at.isoformat()
            }), 201
            
        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Failed to create custom food: {str(e)}'}), 500
        finally:
            session.close()
    
    
    @app.route('/api/custom-foods/estimate-nutrition', methods=['POST'])
    def estimate_custom_food_nutrition():
        """Use AI to estimate nutrition for a custom food"""
        data = request.get_json()
        food_name = data.get('name', '')
        description = data.get('description', '')
        serving_size = data.get('serving_size', 1)
        serving_unit = data.get('serving_unit', 'serving')
        
        try:
            # Import AI module
            from mosaic_nutrition_ai import mosaic_nutrition_ai
            
            # Create prompt for AI to estimate nutrition
            prompt = f"""Please estimate the nutrition facts for this food item:
            
Name: {food_name}
Description: {description}
Serving size: {serving_size} {serving_unit}

Please provide estimates for:
- Calories
- Protein (g)
- Carbohydrates (g) 
- Fat (g)
- Fiber (g)
- Sugar (g)

Format your response as JSON with these exact keys: calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g.
Provide only reasonable estimates based on typical foods. If you're unsure, be conservative."""
            
            ai_response = mosaic_nutrition_ai.generate_nutrition_advice(prompt)
            
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON-like content in the response
            json_match = re.search(r'\{[^}]*\}', ai_response)
            if json_match:
                try:
                    estimated_nutrition = json.loads(json_match.group())
                    confidence = 0.7  # Medium confidence for AI estimates
                except:
                    estimated_nutrition = None
                    confidence = 0.3
            else:
                estimated_nutrition = None
                confidence = 0.3
            
            if not estimated_nutrition:
                # Fallback estimates based on food type keywords
                estimated_nutrition = {
                    'calories': 200,
                    'protein_g': 10,
                    'carbs_g': 20,
                    'fat_g': 8,
                    'fiber_g': 3,
                    'sugar_g': 5
                }
                confidence = 0.4
            
            return jsonify({
                'estimated_nutrition': estimated_nutrition,
                'confidence': confidence,
                'ai_response': ai_response,
                'message': f'Nutrition estimated with {int(confidence*100)}% confidence'
            })
            
        except Exception as e:
            return jsonify({
                'error': f'Failed to estimate nutrition: {str(e)}',
                'fallback_nutrition': {
                    'calories': 200,
                    'protein_g': 10,
                    'carbs_g': 20,
                    'fat_g': 8,
                    'fiber_g': 3,
                    'sugar_g': 5
                },
                'confidence': 0.3
            }), 500
    
    
    # ============================================
    # EXPIRATION TRACKING ENDPOINTS
    # ============================================
    
    @app.route('/api/groceries/expiring', methods=['GET'])
    def get_expiring_items():
        """Get items that are expiring soon"""
        user_id = request.args.get('user_id', 'demo_user')
        days_ahead = int(request.args.get('days', '7'))  # Look ahead 7 days by default
        
        session = SessionLocal()
        try:
            expiry_threshold = date.today() + timedelta(days=days_ahead)
            
            expiring_items = session.query(UserGrocery).filter(
                UserGrocery.user_id == user_id,
                UserGrocery.expiration_date.isnot(None),
                UserGrocery.expiration_date <= expiry_threshold,
                UserGrocery.is_expired == False
            ).options(
                joinedload(UserGrocery.food_item),
                joinedload(UserGrocery.custom_food)
            ).order_by(UserGrocery.expiration_date.asc()).all()
            
            result = []
            today = date.today()
            
            for item in expiring_items:
                days_until_expiry = (item.expiration_date - today).days
                urgency = "expired" if days_until_expiry < 0 else "critical" if days_until_expiry <= 1 else "warning"
                
                # Guard against rare bad rows with neither reference
                if item.food_item is None and item.custom_food is None:
                    # Skip or label unknown item to avoid 500s in production
                    result.append({
                        'id': item.id,
                        'food_name': '(unknown item)',
                        'food_type': 'unknown',
                        'quantity': item.quantity,
                        'unit': item.unit,
                        'location': item.location,
                        'expiration_date': item.expiration_date.isoformat(),
                        'days_until_expiry': days_until_expiry,
                        'urgency': urgency
                    })
                    continue

                food_name = item.food_item.name if item.food_item else item.custom_food.name
                food_type = 'usda' if item.food_item else 'custom'
                
                result.append({
                    'id': item.id,
                    'food_name': food_name,
                    'food_type': food_type,
                    'quantity': item.quantity,
                    'unit': item.unit,
                    'location': item.location,
                    'expiration_date': item.expiration_date.isoformat(),
                    'days_until_expiry': days_until_expiry,
                    'urgency': urgency
                })
            
            return jsonify({
                'expiring_items': result,
                'total_count': len(result),
                'critical_count': len([i for i in result if i['urgency'] == 'critical']),
                'warning_count': len([i for i in result if i['urgency'] == 'warning'])
            })
            
        finally:
            session.close()
    
    
    @app.route('/api/groceries/mark-expired', methods=['POST'])
    def mark_items_expired():
        """Mark expired items as expired"""
        data = request.get_json()
        user_id = data.get('user_id', 'demo_user')
        grocery_ids = data.get('grocery_ids', [])
        
        session = SessionLocal()
        try:
            updated_count = session.query(UserGrocery).filter(
                UserGrocery.id.in_(grocery_ids),
                UserGrocery.user_id == user_id
            ).update({'is_expired': True, 'updated_at': datetime.utcnow()})
            
            session.commit()
            
            return jsonify({
                'message': f'Marked {updated_count} items as expired',
                'updated_count': updated_count
            })
            
        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Failed to mark items as expired: {str(e)}'}), 500
        finally:
            session.close()