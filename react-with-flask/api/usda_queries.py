from __future__ import annotations

from typing import Iterable, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine, Row

# FoodData Central standard nutrient IDs (kcal, grams)
NUTRIENT_IDS = {
    "calories_kcal": 1008,
    "protein_g": 1003,
    "carbs_g": 1005,
    "fat_g": 1004,
    "fiber_g": 1079,
    "sugar_g": 2000,
}


def search_usda(engine: Engine, q: str, limit: int = 20) -> list[dict]:
    # Searches across description, brand fields, and exact UPC match
    # Prioritize data types that are more likely to have nutrition info
    sql = text(
        """
        SELECT f.fdc_id,
               f.description,
               f.data_type,
               COALESCE(b.brand_name, b.brand_owner) AS brand,
               b.brand_name,
               b.brand_owner,
               b.gtin_upc,
               b.serving_size,
               b.serving_size_unit
        FROM food f
        LEFT JOIN branded_food b ON b.fdc_id = f.fdc_id
        WHERE f.description LIKE :pat
           OR b.brand_name LIKE :pat
           OR b.brand_owner LIKE :pat
           OR b.gtin_upc = :q
        ORDER BY 
            CASE f.data_type 
                WHEN 'branded_food' THEN 1
                WHEN 'foundation_food' THEN 2
                WHEN 'sr_legacy_food' THEN 3
                WHEN 'survey_fndds_food' THEN 4
                ELSE 5
            END,
            f.fdc_id DESC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows: Iterable[Row] = conn.execute(sql, {"pat": f"%{q}%", "q": q, "limit": limit}).fetchall()
    return [dict(row._mapping) for row in rows]


def lookup_upc(engine: Engine, upc: str) -> Optional[dict]:
    sql = text(
        """
        SELECT f.fdc_id,
               f.description,
               f.data_type,
               b.brand_name,
               b.brand_owner,
               b.gtin_upc,
               b.serving_size,
               b.serving_size_unit
        FROM branded_food b
        JOIN food f ON f.fdc_id = b.fdc_id
        WHERE b.gtin_upc = :upc
        LIMIT 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"upc": upc}).fetchone()
    return dict(row._mapping) if row else None


def get_food_basic(engine: Engine, fdc_id: int) -> Optional[dict]:
    sql = text(
        """
        SELECT f.fdc_id,
               f.description,
               f.data_type,
               b.brand_name,
               b.brand_owner,
               b.gtin_upc,
               b.serving_size,
               b.serving_size_unit
        FROM food f
        LEFT JOIN branded_food b ON b.fdc_id = f.fdc_id
        WHERE f.fdc_id = :fdc_id
        LIMIT 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"fdc_id": fdc_id}).fetchone()
    return dict(row._mapping) if row else None


def get_basic_nutrients(engine: Engine, fdc_id: int) -> dict:
    # Join food_nutrient -> nutrient and pull a few common macros by nutrient_id
    # Note: some schemas may store nutrient number differently; adjust if needed
    sql = text(
        """
        SELECT fn.nutrient_id, n.name, n.unit_name, fn.amount
        FROM food_nutrient fn
        JOIN nutrient n ON n.id = fn.nutrient_id
        WHERE fn.fdc_id = :fdc_id
          AND fn.nutrient_id IN (:cal, :pro, :carb, :fat, :fiber, :sugar)
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "fdc_id": fdc_id,
                "cal": NUTRIENT_IDS["calories_kcal"],
                "pro": NUTRIENT_IDS["protein_g"],
                "carb": NUTRIENT_IDS["carbs_g"],
                "fat": NUTRIENT_IDS["fat_g"],
                "fiber": NUTRIENT_IDS["fiber_g"],
                "sugar": NUTRIENT_IDS["sugar_g"],
            },
        ).fetchall()
    out: dict = {}
    for r in rows:
        nid = r._mapping["nutrient_id"]
        amt = float(r._mapping["amount"]) if r._mapping["amount"] is not None else None
        if nid == NUTRIENT_IDS["calories_kcal"]:
            out["calories"] = amt
        elif nid == NUTRIENT_IDS["protein_g"]:
            out["protein_g"] = amt
        elif nid == NUTRIENT_IDS["carbs_g"]:
            out["carbs_g"] = amt
        elif nid == NUTRIENT_IDS["fat_g"]:
            out["fat_g"] = amt
        elif nid == NUTRIENT_IDS["fiber_g"]:
            out["fiber_g"] = amt
        elif nid == NUTRIENT_IDS["sugar_g"]:
            out["sugar_g"] = amt
    return out