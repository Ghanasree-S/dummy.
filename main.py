from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router  # Your route file with vitals prediction and latest vitals
from pymongo import MongoClient
from bson.json_util import dumps
from fastapi.responses import JSONResponse
from datetime import datetime
import pytz

# -------------------------------
# 🔗 MongoDB Setup
# -------------------------------
MONGO_URI = "mongodb+srv://ghanasreesk24:vitals@vitals.55nbs.mongodb.net/?retryWrites=true&w=majority&appName=Vitals"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Validate connection
    print("✅ MongoDB connected successfully.")
except Exception as e:
    print("❌ MongoDB connection failed:", e)

# Database & Collections
db = client["health_vitals_db"]
temp_collection = db["temp"]
oximeter_collection = db["oximeter"]

# -------------------------------
# 🚀 FastAPI App Initialization
# -------------------------------
app = FastAPI(
    title="Health Vitals API",
    description="API for submitting health vitals and predicting potential health conditions",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routes (from routes.py)
app.include_router(router)

# -------------------------------
# 🏠 Root Endpoint
# -------------------------------
@app.get("/")
async def root():
    return {"message": "🚀 Welcome to the Health Vitals API!"}

# -------------------------------
# 🔄 Latest Sensor Vitals Endpoint (for Flutter)
# -------------------------------
@app.get("/api/vitals/latest")
async def get_latest_vitals():
    try:
        # Fetch latest temperature
        temperature_doc = temp_collection.find_one(sort=[("timestamp", -1)])
        temperature = temperature_doc.get("Temperature_C") if temperature_doc else None

        # Fetch latest heart rate
        heart_doc = oximeter_collection.find_one({"Type": "Heart Rate"}, sort=[("timestamp", -1)])
        heart_rate = heart_doc.get("Value") if heart_doc else None

        # Fetch latest SPO2
        spo2_doc = oximeter_collection.find_one({"Type": "SPO2"}, sort=[("timestamp", -1)])
        spo2 = spo2_doc.get("Value") if spo2_doc else None

        # If none of the values are available
        if not any([temperature, heart_rate, spo2]):
            return JSONResponse(status_code=404, content={"error": "No vitals data found."})

        # Return response
        return {
            "temperature": temperature,
            "heart_rate": heart_rate,
            "spo2": spo2
        }

    except Exception as e:
        print("❌ Error in /api/vitals/latest:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
