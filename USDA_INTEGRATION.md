# USDA SQLite Integration

This project can use a read-only USDA FoodData Central SQLite database as a lookup source. We do not store the full USDA dataset in our app DB; instead, we import items on-demand that users select (e.g., after a UPC scan or search).

## 1) Build or Download the USDA SQLite

This repository expects a file at:

- 2025_hackgt/data/vendor/USDADataBase/USDA.sqlite

You can produce this SQLite using the tools from the upstream repo:

- https://github.com/ndivito/USDADataBase

Steps (summary):
- Download the USDA FoodData Central Full Download from https://fdc.nal.usda.gov/download-datasets and extract the CSVs.
- Open `Creating_SQLite_From_CSV_Table_Descriptions.ipynb` from the USDADataBase repo and run it to create a SQLite DB from those CSVs.
- Save or move the resulting SQLite file to `data/vendor/USDADataBase/USDA.sqlite` in this project.

## 2) Run the API

Once the SQLite file is in place, start the API as usual. The following endpoints will be available:

- GET /api/usda/search?q=cheddar&limit=20
- GET /api/usda/upc/012345678905
- POST /api/usda/import/123456

Importing by fdc_id will copy the selected USDA food into the app's own database (FoodItem + NutritionFacts). UPC search checks the branded_food table.

## 3) Notes

- The code assumes FoodData Central standard table names: `food`, `branded_food`, `food_nutrient`, and `nutrient`.
- If the notebook produces different table/column names, adjust the queries in `react-with-flask/api/usda_queries.py` accordingly.
- The USDA DB is opened read-only; it will not be modified.