import pickle
import numpy as np
import pandas as pd
import traceback

# Load trained models and scalers
model_files = {
    "Diabetes": "./models/Diabetic_NonDiabetic__D_N__model.pkl",
    "BP": "./models/BP_Status__Y_N__model.pkl",
    "Fever": "./models/Fever_Status__Y_N__model.pkl",
    "Pulse": "./models/Pulse_Normal__Y_N__model.pkl"
}

scaler_files = {
    "Diabetes": "./models/Diabetic_NonDiabetic__D_N__scaler.pkl",
    "BP": "./models/BP_Status__Y_N__scaler.pkl",
    "Fever": "./models/Fever_Status__Y_N__scaler.pkl",
    "Pulse": "./models/Pulse_Normal__Y_N__scaler.pkl"
}

models = {}
scalers = {}

# Load models and scalers
try:
    for key in model_files:
        with open(model_files[key], "rb") as f:
            models[key] = pickle.load(f)

    for key in scaler_files:
        with open(scaler_files[key], "rb") as f:
            scalers[key] = pickle.load(f)

    print("✅ Models and scalers loaded successfully.")

except Exception as e:
    print(f"❌ Error loading models/scalers: {e}")
    traceback.print_exc()

# Feature name mapping based on updated frontend keys
feature_mapping = {
    "glucose": "Blood Glucose Level",
    "diastolic": "Diastolic BP",
    "systolic": "Systolic BP",
    "heart_rate": "Heart Rate",
    "temperature": "Body Temperature",
    "spo2": "SPO2"
}

# Prediction function
def predict_health_insight(vitals):
    try:
        print("🔍 Received input data for prediction:", vitals)

        formatted_vitals = {feature_mapping[key]: vitals[key] for key in feature_mapping}
        print(f"Formatted vitals: {formatted_vitals}")
        
        input_df = pd.DataFrame([formatted_vitals])
        print(f"Input DataFrame for prediction: {input_df}")

        predictions = {}

        for key in models:
            scaler = scalers[key]
            model = models[key]
            scaled_input = scaler.transform(input_df.values.reshape(1, -1))
            prediction = model.predict(scaled_input)[0]
            predictions[key] = "Yes" if prediction == 1 else "No"
            print(f"{key} prediction: {predictions[key]}")

        return predictions

    except Exception as e:
        print(f"❌ Prediction error: {e}")
        traceback.print_exc()
        return {
            "Diabetes": "Error: Prediction Failed",
            "BP": "Error: Prediction Failed",
            "Fever": "Error: Prediction Failed",
            "Pulse": "Error: Prediction Failed"
        }
