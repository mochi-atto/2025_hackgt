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

        # Validate one-of
        if bool(food_item_id) == bool(custom_food_id):
            return jsonify({'error': 'Provide exactly one of food_item_id or custom_food_id'}), 400

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