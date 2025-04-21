import paho.mqtt.client as mqtt
import pymongo
import json
from datetime import datetime, timedelta
import pytz

# --- MongoDB Setup ---
MONGO_URI = "mongodb+srv://ghanasreesk24:vitals@vitals.55nbs.mongodb.net/?retryWrites=true&w=majority&appName=Vitals"

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client["health_vitals_db"]
    temp_collection = db["temperature"]
    oximeter_collection = db["oximeter"]
    mongo_client.server_info()
    print("✅ Connected to MongoDB Atlas")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    exit(1)

# --- Constants ---
USER_ID = 1
TIMEZONE = "Asia/Kolkata"
STABLE_THRESHOLD = 3

# --- Stability Tracking ---
last_temp = None
stable_count = 0

# --- Dose Period ---
def get_dose_period(hour):
    if 5 <= hour < 12:
        return "M"
    elif 12 <= hour < 18:
        return "A"
    else:
        return "N"

# --- MQTT Callback ---
def on_message(client, userdata, msg):
    global last_temp, stable_count

    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        print(f"📥 Received on {topic}: {payload}")

        local_time = datetime.now(pytz.timezone(TIMEZONE))
        date_only = datetime(local_time.year, local_time.month, local_time.day)
        hour = local_time.hour
        dose_period = get_dose_period(hour)

        # --- Temperature ---
        if topic == "pillbox/temperature":
            temp_val = payload.get("temperature")
            if temp_val is None:
                return

            if last_temp is not None and abs(temp_val - last_temp) < 0.2:
                stable_count += 1
            else:
                stable_count = 0
            last_temp = temp_val

            if stable_count >= STABLE_THRESHOLD:
                temp_record = {
                    "User_ID": USER_ID,
                    "Temperature_C": temp_val,
                    "DateTime": local_time,
                    "timestamp": local_time
                }
                temp_collection.insert_one(temp_record)
                print(f"🌡 ✅ Stable Temperature Stored: {temp_val}°C")
                stable_count = 0
            return

        # --- Oximeter ---
        if topic == "pillbox/oximeter":
            heart_rate = payload.get("heart_rate")
            spo2 = payload.get("spo2")

            if heart_rate:
                oximeter_collection.insert_one({
                    "User_ID": USER_ID,
                    "Type": "Heart Rate",
                    "Value": heart_rate,
                    "DateTime": local_time,
                    "timestamp": local_time
                })
            if spo2:
                oximeter_collection.insert_one({
                    "User_ID": USER_ID,
                    "Type": "SPO2",
                    "Value": spo2,
                    "DateTime": local_time,
                    "timestamp": local_time
                })
            return


    except Exception as e:
        print("❌ Error in message handler:", e)

# --- MQTT Setup ---
client = mqtt.Client()
client.on_message = on_message

try:
    client.connect("localhost", 1883)
except Exception as e:
    print("❌ MQTT Connection Failed:", e)
    exit(1)

# --- Start ---

topics = [
    "pillbox/temperature", "pillbox/oximeter"
]
for topic in topics:
    client.subscribe(topic)

print("🟢 MQTT to MongoDB bridge is running...")
client.loop_forever()
