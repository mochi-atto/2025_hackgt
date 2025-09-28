#!/usr/bin/env python3
"""
Seed a few sample USDA-like FoodItems with NutritionFacts for demo/testing.
This does NOT require the USDA vendor database; it populates your app's own tables.
"""
from datetime import date, timedelta

from db import SessionLocal
from models import FoodItem, NutritionFacts

SAMPLES = [
    {
        "name": "Chicken Breast, raw, skinless",
        "brand": None,
        "category": "meat",
        "upc": None,
        "nutrition": {
            "serving_size": 100.0,
            "serving_unit": "g",
            "calories": 165.0,
            "protein_g": 31.0,
            "carbs_g": 0.0,
            "fat_g": 3.6,
            "fiber_g": 0.0,
            "sugar_g": 0.0,
        },
    },
    {
        "name": "Whole Milk",
        "brand": None,
        "category": "dairy",
        "upc": None,
        "nutrition": {
            "serving_size": 240.0,
            "serving_unit": "ml",
            "calories": 150.0,
            "protein_g": 8.0,
            "carbs_g": 12.0,
            "fat_g": 8.0,
            "fiber_g": 0.0,
            "sugar_g": 12.0,
        },
    },
    {
        "name": "Broccoli, raw",
        "brand": None,
        "category": "produce",
        "upc": None,
        "nutrition": {
            "serving_size": 100.0,
            "serving_unit": "g",
            "calories": 34.0,
            "protein_g": 2.8,
            "carbs_g": 6.6,
            "fat_g": 0.4,
            "fiber_g": 2.6,
            "sugar_g": 1.7,
        },
    },
]

def upsert_food(session, sample):
    name = sample["name"]
    brand = sample.get("brand")
    upc = sample.get("upc")
    category = sample.get("category")

    existing = (
        session.query(FoodItem)
        .filter(FoodItem.name == name)
        .filter(FoodItem.brand == brand)
        .filter(FoodItem.upc == upc)
        .first()
    )
    item = existing
    if not item:
        item = FoodItem(name=name, brand=brand, category=category, upc=upc, is_perishable=True)
        session.add(item)
        session.flush()

    # Upsert nutrition facts
    nf = item.nutrition
    if nf:
        session.delete(nf)
        session.flush()

    n = sample["nutrition"]
    nf = NutritionFacts(
        food_item_id=item.id,
        serving_size=n.get("serving_size"),
        serving_unit=n.get("serving_unit"),
        calories=n.get("calories"),
        protein_g=n.get("protein_g"),
        carbs_g=n.get("carbs_g"),
        fat_g=n.get("fat_g"),
        fiber_g=n.get("fiber_g"),
        sugar_g=n.get("sugar_g"),
    )
    session.add(nf)
    session.flush()
    return item.id


def main():
    session = SessionLocal()
    try:
        ids = []
        for s in SAMPLES:
            fid = upsert_food(session, s)
            ids.append({"name": s["name"], "id": fid})
        session.commit()
        print({"seeded": ids})
    except Exception as e:
        session.rollback()
        print({"error": str(e)})
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
