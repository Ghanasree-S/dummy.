from fastapi import APIRouter, HTTPException
from typing import Dict
from models import HealthVitals  # If used elsewhere
from database import health_vitals_collection, db
from predict import predict_health_insight
from datetime import datetime
import traceback

router = APIRouter()

# ----------------------------------------
# 🔄 Save & Predict Health Vitals
# ----------------------------------------
@router.post("/predictVitals")
async def predict_vitals(vitals: Dict[str, float]):
    try:
        print("🔍 Received input data for prediction:", vitals)

        required_keys = ['glucose', 'diastolic', 'systolic', 'heart_rate', 'temperature', 'spo2']
        missing_keys = [key for key in required_keys if key not in vitals]

        if missing_keys:
            raise HTTPException(status_code=400, detail=f"Missing required input fields: {missing_keys}")

        # Ensure numeric values
        for key in required_keys:
            value = vitals[key]
            if not isinstance(value, (int, float)):
                raise HTTPException(status_code=400, detail=f"Invalid data type for {key}. Expected a number.")
            vitals[key] = float(value)

        # Add timestamp
        vitals["timestamp"] = datetime.utcnow()

        # Save to MongoDB
        result = await health_vitals_collection.insert_one(vitals)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to save health vitals to the database")

        print("✅ Health vitals saved to DB")

        # Run prediction
        predictions = predict_health_insight(vitals)

        return {
            "message": "Health vitals saved to DB",
            "predictions": predictions
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error during prediction: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error during prediction: {e}")


# ----------------------------------------
# ✅ Get Latest Sensor Vitals (Temp, HR, SPO2)
# ----------------------------------------
@router.get("/latestVitals")
async def get_latest_vitals():
    try:
        temp_doc = await db["temp"].find_one(sort=[("timestamp", -1)])
        print("🌡 Latest temp doc:", temp_doc)

        hr_doc = await db["oximeter"].find_one({"Type": "Heart Rate"}, sort=[("timestamp", -1)])
        print("❤️ Latest HR doc:", hr_doc)

        spo2_doc = await db["oximeter"].find_one({"Type": "SPO2"}, sort=[("timestamp", -1)])
        print("🩸 Latest SPO2 doc:", spo2_doc)

        temperature = temp_doc.get("Temperature_C") if temp_doc else None
        heart_rate = hr_doc.get("Value") if hr_doc else None
        spo2 = spo2_doc.get("Value") if spo2_doc else None

        if not any([temperature, heart_rate, spo2]):
            raise HTTPException(status_code=404, detail="No vitals found")

        return {
            "temperature": temperature,
            "heart_rate": heart_rate,
            "spo2": spo2,
        }

    except Exception as e:
        print("❌ Error fetching latest vitals:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error fetching latest vitals")
