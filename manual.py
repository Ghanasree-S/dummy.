from pymongo import MongoClient
from datetime import datetime

MONGO_URI = "mongodb+srv://ghanasreesk24:vitals@vitals.55nbs.mongodb.net/?retryWrites=true&w=majority&appName=Vitals"
client = MongoClient(MONGO_URI)
db = client["health_vitals_db"]
oximeter_collection = db["oximeter"]

now = datetime.utcnow()

# Insert heart rate
oximeter_collection.insert_one({
    "User_ID": 1,
    "Type": "Heart Rate",
    "Value": 99,
    "timestamp": now
})

# Insert SPO2
oximeter_collection.insert_one({
    "User_ID": 1,
    "Type": "SPO2",
    "Value": 99,
    "timestamp": now
})

print("✅ Inserted HR & SPO2 data.")
