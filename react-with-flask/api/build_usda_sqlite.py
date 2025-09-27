from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


REQUIRED_FILES = {
    "food": "food.csv",
    "branded_food": "branded_food.csv",
    "food_nutrient": "food_nutrient.csv",
    "nutrient": "nutrient.csv",
}


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def create_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;
        PRAGMA temp_store = MEMORY;
        PRAGMA mmap_size = 134217728; -- 128MB

        DROP TABLE IF EXISTS food;
        DROP TABLE IF EXISTS branded_food;
        DROP TABLE IF EXISTS food_nutrient;
        DROP TABLE IF EXISTS nutrient;

        CREATE TABLE food (
            fdc_id INTEGER PRIMARY KEY,
            description TEXT,
            data_type TEXT
        );

        CREATE TABLE branded_food (
            fdc_id INTEGER PRIMARY KEY,
            brand_name TEXT,
            brand_owner TEXT,
            gtin_upc TEXT,
            serving_size REAL,
            serving_size_unit TEXT
        );

        CREATE TABLE food_nutrient (
            fdc_id INTEGER,
            nutrient_id INTEGER,
            amount REAL
        );

        CREATE TABLE nutrient (
            id INTEGER PRIMARY KEY,
            nutrient_id INTEGER, -- numeric code (e.g., 1008 for kcal)
            name TEXT,
            unit_name TEXT
        );
        """
    )
    conn.commit()


autotypes = {
    "food": {
        "fdc_id": "int64",
        "description": "string",
        "data_type": "string",
    },
    "branded_food": {
        "fdc_id": "int64",
        "brand_name": "string",
        "brand_owner": "string",
        "gtin_upc": "string",
        "serving_size": "float64",
        "serving_size_unit": "string",
    },
    "food_nutrient": {
        "fdc_id": "int64",
        "nutrient_id": "int64",  # references nutrient.id
        "amount": "float64",
    },
    "nutrient": {
        "id": "int64",
        # 'nutrient_nbr' in CSV is string; we'll cast to numeric into nutrient_id
        "name": "string",
        "unit_name": "string",
        "nutrient_nbr": "string",
    },
}


def import_csv_chunked(conn: sqlite3.Connection, csv_path: Path, table: str, usecols: list[str], rename: dict[str, str] | None = None, chunksize: int = 200_000):
    rename = rename or {}
    total = 0
    for chunk in pd.read_csv(csv_path, usecols=usecols, dtype={c: autotypes.get(table, {}).get(c) for c in usecols}, chunksize=chunksize):
        if rename:
            chunk = chunk.rename(columns=rename)
        # Special handling for nutrient.number -> nutrient_id (int)
        if table == "nutrient" and "nutrient_nbr" in usecols:
            # coerce to numeric; drop NaNs
            chunk["nutrient_id"] = pd.to_numeric(chunk["nutrient_nbr"], errors="coerce").astype("Int64")
            chunk = chunk.drop(columns=["nutrient_nbr"])  # we store nutrient_id instead
            # ensure unit_name column matches schema
            # (CSV already uses unit_name)
        # Ensure correct column order for destination table names
        # Use small write chunks to avoid SQLite variable limit (default ~999)
        chunk.to_sql(table, conn, if_exists="append", index=False, method=None, chunksize=1000)
        total += len(chunk)
    return total


def create_indexes(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_food_desc ON food(description);
        CREATE INDEX IF NOT EXISTS idx_bf_upc ON branded_food(gtin_upc);
        CREATE INDEX IF NOT EXISTS idx_bf_brand ON branded_food(brand_name, brand_owner);
        CREATE INDEX IF NOT EXISTS idx_fn_fdc ON food_nutrient(fdc_id);
        CREATE INDEX IF NOT EXISTS idx_fn_nutrient ON food_nutrient(nutrient_id);
        CREATE INDEX IF NOT EXISTS idx_nutrient_code ON nutrient(nutrient_id);
        """
    )
    conn.commit()


def build(csv_dir: Path, out_db: Path, overwrite: bool = False):
    csv_dir = csv_dir.resolve()
    out_db = out_db.resolve()

    missing = [name for name, f in REQUIRED_FILES.items() if not (csv_dir / f).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required CSV files in {csv_dir}: {missing}")

    ensure_parent(out_db)
    if out_db.exists():
        if not overwrite:
            raise FileExistsError(f"Output DB already exists at {out_db}. Use --overwrite to replace.")
        out_db.unlink()

    conn = sqlite3.connect(out_db)
    try:
        create_schema(conn)

        # Import food
        total_food = import_csv_chunked(
            conn,
            csv_dir / REQUIRED_FILES["food"],
            table="food",
            usecols=["fdc_id", "description", "data_type"],
        )
        print(f"Imported food: {total_food}")

        # Import branded_food
        total_branded = import_csv_chunked(
            conn,
            csv_dir / REQUIRED_FILES["branded_food"],
            table="branded_food",
            usecols=[
                "fdc_id",
                "brand_name",
                "brand_owner",
                "gtin_upc",
                "serving_size",
                "serving_size_unit",
            ],
        )
        print(f"Imported branded_food: {total_branded}")

        # Import nutrient
        total_nutrient = import_csv_chunked(
            conn,
            csv_dir / REQUIRED_FILES["nutrient"],
            table="nutrient",
            usecols=["id", "name", "unit_name", "nutrient_nbr"],
        )
        print(f"Imported nutrient: {total_nutrient}")

        # Import food_nutrient (only required columns)
        total_fn = import_csv_chunked(
            conn,
            csv_dir / REQUIRED_FILES["food_nutrient"],
            table="food_nutrient",
            usecols=["fdc_id", "nutrient_id", "amount"],
        )
        print(f"Imported food_nutrient: {total_fn}")

        create_indexes(conn)
        print("Indexes created.")

        # Optimize DB size
        conn.execute("VACUUM")
        conn.commit()
        print(f"SQLite built at: {out_db}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Build USDA SQLite from FoodData Central CSVs (subset)")
    parser.add_argument("--csv-dir", required=True, help="Path to USDA CSV folder (contains food.csv, branded_food.csv, nutrient.csv, food_nutrient.csv)")
    parser.add_argument("--out", required=True, help="Output SQLite file path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output DB if it exists")

    args = parser.parse_args()
    csv_dir = Path(args.csv_dir)
    out_path = Path(args.out)

    build(csv_dir, out_path, overwrite=args.overwrite)


if __name__ == "__main__":
    main()