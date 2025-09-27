from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from dateutil import parser as dateparser
from sqlalchemy.orm import Session

# Support both package and script execution
try:
    from .db import SessionLocal, init_db
    from .models import FoodItem, NutritionFacts
except ImportError:  # running as a script
    import os, sys
    sys.path.append(os.path.dirname(__file__))
    from db import SessionLocal, init_db
    from models import FoodItem, NutritionFacts


SAMPLE_CSV = Path(__file__).resolve().parents[1].with_name('data') / 'samples' / 'foods.csv'


def to_float(x: Optional[str]) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except ValueError:
        return None


def main(csv_path: Path = SAMPLE_CSV):
    init_db()
    if not csv_path.exists():
        raise SystemExit(f"CSV not found at {csv_path}. Create a sample first.")

    session: Session = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        with csv_path.open(newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name')
                if not name:
                    skipped += 1
                    continue
                brand = row.get('brand') or None
                category = row.get('category') or None
                upc = row.get('upc') or None
                is_perishable = (row.get('is_perishable') or 'true').strip().lower() in {'1', 'true', 'yes', 'y'}

                # Deduplicate by name+brand+upc
                existing = (
                    session.query(FoodItem)
                    .filter(FoodItem.name == name)
                    .filter(FoodItem.brand == brand)
                    .filter(FoodItem.upc == upc)
                    .first()
                )
                if existing:
                    skipped += 1
                    continue

                item = FoodItem(
                    name=name,
                    brand=brand,
                    category=category,
                    upc=upc,
                    is_perishable=is_perishable,
                )
                session.add(item)
                session.flush()  # To get item.id

                facts = NutritionFacts(
                    food_item_id=item.id,
                    serving_size=to_float(row.get('serving_size')),
                    serving_unit=row.get('serving_unit') or None,
                    calories=to_float(row.get('calories')),
                    protein_g=to_float(row.get('protein_g')),
                    carbs_g=to_float(row.get('carbs_g')),
                    fat_g=to_float(row.get('fat_g')),
                    fiber_g=to_float(row.get('fiber_g')),
                    sugar_g=to_float(row.get('sugar_g')),
                    sodium_mg=to_float(row.get('sodium_mg')),
                )
                session.add(facts)
                inserted += 1

        session.commit()
        print(f"Inserted {inserted} items; skipped {skipped}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()