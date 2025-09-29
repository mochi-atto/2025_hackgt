# 🌿 basil

basil is an intelligent recipe generation app that helps you make the most of your food inventory. It prioritizes ingredients that are about to expire, allows you to specify your mealtime preferences, and generates customized recipes based on what you have on hand.

## 🚀 Features

- **Smart Inventory Management:** Track your groceries and their expiration dates
- **Intelligent Recipe Generation:** AI-powered suggestions based on what you have on hand
- **Expiration Prioritization:** Recipes that use items that will expire soon
- **Customized Meal Planning:** Specify preferences from quick 15-minute lunches to 4-course dinners
- **Nutrition Tracking:** Get detailed nutritional information for recipes
- **Secure Authentication:** Amazon Cognito integration for user management

## 🔧 Technologies

### Frontend
- **React 19** with Router for single-page application architecture
- **Vite** for fast development and optimized builds
- **AWS Amplify & Cognito** for user authentication
- **Marked** for markdown parsing of recipe content

### Backend
- **Flask** serving a RESTful API
- **SQLite** with **SQLAlchemy** ORM for database operations
- **Python 3** with modern async patterns
- **Gunicorn** for production deployment

### AI Integration
- **Custom AI Client** with **Mosaic/OpenAI** for recipe generation
- **Structured JSON Response Parsing** for consistent nutrition data
- **USDA Food Database** integration for accurate nutrition information
- **Smart prompting system** to enforce JSON-formatted nutritional outputs

## 🏗️ Architecture

basil is built as a full-stack application with:

1. **React Frontend:** Modern React application with component-based architecture, routing, and state management
2. **Flask Backend API:** RESTful API with endpoints for food inventory, favorites, recipe generation, and AI integration
3. **SQLite Database:** Efficiently stores user data, food inventory, nutrition facts, and favorite recipes
4. **AI Integration Layer:** Custom Mosaic/OpenAI client with carefully crafted prompts for recipe generation
5. **USDA Data Layer:** Processes millions of USDA food data points for accurate nutritional information

## 💻 Getting Started

### Prerequisites
- Node.js 18+ and npm
- Python 3.9+
- OpenAI API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd 2025_hackgt/react-with-flask
   ```

2. **Set up the frontend**
   ```bash
   npm install
   ```

3. **Set up the backend**
   ```bash
   cd api
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Download USDA Food Data (Required for nutrition information)**
   
   The app requires USDA FoodData Central CSV files to provide accurate nutrition data:
   
   a. Download the CSV files from [USDA FoodData Central](https://fdc.nal.usda.gov/download-datasets.html)
   b. Extract the CSV files and place them in `react-with-flask/data/vendor/FoodData_Central_csv_2024-04-18/`
   
   Required files:
   - `food.csv` - Main food items database
   - `branded_food.csv` - Branded food products
   - `nutrient.csv` - Nutrient definitions
   - `food_nutrient.csv` - Food-nutrient relationships (optional for basic functionality)

5. **Build the USDA Database**
   ```bash
   cd api
   python build_simple_usda.py
   ```
   
   This will:
   - Process millions of USDA food records
   - Create a SQLite database with searchable food items
   - Build indexes for fast food search and UPC lookup
   - Takes ~5-10 minutes depending on your system

6. **Create a .env file in the project root with your API keys**
   ```
   OPENAI_KEY=your_openai_key_here
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```

### Running the Development Environment

1. **Start the Flask API server**
   ```bash
   npm run api
   ```
   
   The API will be available at `http://localhost:5001`

2. **Start the React development server** (in a new terminal)
   ```bash
   npm run dev
   ```
   
   The frontend will be available at `http://localhost:5173`

3. **Access the application at [http://localhost:5173](http://localhost:5173)**

### First Time Setup Verification

After completing the setup, verify everything works:

1. **Test the USDA database**: The food search should return results
2. **Test AI integration**: Try generating a recipe (requires OpenAI API key)
3. **Test authentication**: Sign up/login should work with AWS Cognito

## 🌟 Key Features in Detail

### Smart Expiration Management
basil uses intelligent algorithms to calculate expiration dates based on food type:
- Very perishable items (lettuce, berries, fish): 1-3 days
- Short-term perishables (broccoli, milk, fresh meat): 3-7 days
- Medium-term items (apples, cheese, eggs): 1-2 weeks
- Long-term items (potatoes, whole grain bread): 3-4 weeks
- Pantry items (rice, pasta, canned goods): 6+ months

### AI-Powered Recipe Generation
The AI system considers:
- Available ingredients in your inventory
- Items approaching expiration (prioritized)
- Your specified meal preferences and time constraints
- Nutritional balance and dietary requirements
- Realistic preparation methods and techniques

### USDA Integration
Direct integration with USDA food database provides:
- Accurate nutritional information for thousands of foods
- Standardized serving sizes and measurements
- Comprehensive macro and micronutrient data
- Support for both branded and generic food items

## 🛠️ Development Challenges

- **Data Processing:** Converting millions of data points from USDA CSV files into a queryable SQLite database format
- **API Security:** Implementing secure Mosaic/OpenAI client integration while protecting API keys
- **AI Consistency:** Extensive testing with different models and prompts to achieve consistent, accurate recipe outputs
- **User Experience:** Creating an intuitive interface accessible to users regardless of technical expertise
- **Real-time Features:** Implementing responsive inventory management and recipe generation

## 📁 Project Structure

```
2025_hackgt/
└── react-with-flask/
    ├── src/                    # React frontend source
    │   ├── dashboard.jsx       # Main dashboard interface
    │   ├── landing.jsx        # Landing page
    │   ├── login.jsx          # Authentication components
    │   └── aws-config.js      # AWS Cognito configuration
    ├── api/                   # Flask backend
    │   ├── api.py            # Main Flask application
    │   ├── models.py         # SQLAlchemy database models
    │   ├── mosaic_nutrition_ai.py # AI integration layer
    │   ├── usda_queries.py   # USDA database operations
    │   ├── build_simple_usda.py # USDA database builder
    │   └── requirements.txt  # Python dependencies
    ├── data/                 # Database files and USDA data
    │   └── vendor/           # USDA CSV files and SQLite DB
    └── dist/                 # Production build output
```

## 🚀 Deployment

The application is configured for deployment on platforms like Render:

1. **Frontend:** Static site deployment with Vite build
2. **Backend:** Python Flask app with Gunicorn WSGI server
3. **Database:** SQLite for development, PostgreSQL for production
4. **Environment:** Configurable CORS origins and API endpoints

## 🏆 Acknowledgments

- Built during **HackGT 2025**
- **USDA Food Database** for comprehensive nutrition information
- **Databricks Mosaic AI** for structured recipe generation capabilities
- **Amazon Web Services** for authentication and cloud infrastructure
- **OpenAI** for natural language processing and recipe generation

---

*basil - Making the most of what you have, one recipe at a time.*
