#!/usr/bin/env python3
"""
Simple USDA SQLite builder - creates a basic database for food search
without the large food_nutrient table that was corrupted.
"""

import sqlite3
import pandas as pd
from pathlib import Path

def build_simple_usda():
    """Build a simple USDA SQLite database with basic food data"""
    csv_dir = Path("../data/vendor/FoodData_Central_csv_2024-04-18")
    out_db = Path("../data/vendor/USDADataBase/USDA.sqlite")
    
    # Ensure output directory exists
    out_db.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing database
    if out_db.exists():
        out_db.unlink()
    
    print(f"Building simple USDA database at {out_db}")
    
    # Create database connection
    conn = sqlite3.connect(out_db)
    cursor = conn.cursor()
    
    try:
        # Create schema
        cursor.executescript("""
            PRAGMA journal_mode = OFF;
            PRAGMA synchronous = OFF;
            PRAGMA temp_store = MEMORY;
            PRAGMA mmap_size = 134217728;

            CREATE TABLE food (
                fdc_id INTEGER PRIMARY KEY,
                description TEXT,
                data_type TEXT,
                UNIQUE(fdc_id)
            );

            CREATE TABLE branded_food (
                fdc_id INTEGER PRIMARY KEY,
                brand_name TEXT,
                brand_owner TEXT,
                gtin_upc TEXT,
                serving_size REAL,
                serving_size_unit TEXT,
                FOREIGN KEY (fdc_id) REFERENCES food(fdc_id)
            );

            CREATE INDEX idx_food_desc ON food(description);
            CREATE INDEX idx_food_type ON food(data_type);
            CREATE INDEX idx_branded_upc ON branded_food(gtin_upc);
            CREATE INDEX idx_branded_brand ON branded_food(brand_name);
        """)
        
        print("Schema created")
        
        # Import food.csv
        print("Importing food.csv...")
        food_chunks = pd.read_csv(
            csv_dir / "food.csv",
            usecols=["fdc_id", "description", "data_type"],
            chunksize=50000,
            dtype={"fdc_id": "int64", "description": "string", "data_type": "string"}
        )
        
        food_count = 0
        for chunk in food_chunks:
            # Filter out rows with NULL descriptions
            chunk = chunk.dropna(subset=['description'])
            # Only import if chunk has data
            if len(chunk) > 0:
                chunk.to_sql("food", conn, if_exists="append", index=False)
                food_count += len(chunk)
            if food_count % 100000 == 0 and food_count > 0:
                print(f"  Imported {food_count} food items...")
        
        print(f"Imported {food_count} food items")
        
        # Import branded_food.csv
        print("Importing branded_food.csv...")
        branded_chunks = pd.read_csv(
            csv_dir / "branded_food.csv",
            usecols=["fdc_id", "brand_name", "brand_owner", "gtin_upc", "serving_size", "serving_size_unit"],
            chunksize=50000,
            dtype={
                "fdc_id": "int64",
                "brand_name": "string",
                "brand_owner": "string", 
                "gtin_upc": "string",
                "serving_size": "float64",
                "serving_size_unit": "string"
            }
        )
        
        branded_count = 0
        for chunk in branded_chunks:
            # Filter out problematic rows
            chunk = chunk.dropna(subset=['fdc_id'])
            # Only import if chunk has data
            if len(chunk) > 0:
                chunk.to_sql("branded_food", conn, if_exists="append", index=False)
                branded_count += len(chunk)
            if branded_count % 100000 == 0 and branded_count > 0:
                print(f"  Imported {branded_count} branded food items...")
        
        print(f"Imported {branded_count} branded food items")
        
        # Optimize database
        print("Optimizing database...")
        cursor.execute("VACUUM")
        conn.commit()
        
        print(f"✅ Simple USDA database built successfully at {out_db}")
        print(f"   Food items: {food_count}")
        print(f"   Branded items: {branded_count}")
        
    except Exception as e:
        print(f"❌ Error building database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    build_simple_usda()
