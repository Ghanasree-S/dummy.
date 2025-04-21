import paho.mqtt.client as mqtt
import pymongo
import json
from datetime import datetime, timedelta
import pytz
import time

# --- MongoDB Setup ---
MONGO_URI = "mongodb+srv://ghanasreesk24:vitals@vitals.55nbs.mongodb.net/?retryWrites=true&w=majority&appName=Vitals"

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client["health_vitals_db"]
    pill_collection = db["pills_in_box"]
    medication_collection = db["medications"]
    history_collection = db["hist"]
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

# --- Pill Count Calculation ---
def calculate_pill_count(dosage, start_date, end_date):
    today = datetime.now().date()
    start = max(start_date.date(), today)
    days = (end_date.date() - start).days + 1
    return max(int(dosage) * days, 0)

# --- Pillbox Initialization ---
def initialize_pillbox():
    pill_collection.delete_many({})
    print("📦 Initializing pillbox with medications...")

    medications = medication_collection.find({
        "type": {"$in": ["Capsule", "Tablet"]}
    }).limit(4)

    for idx, med in enumerate(medications, start=1):
        try:
            pill_name = med.get("pillName")
            dosage = int(med.get("dosage", 0))
            start_date = med.get("startDate")
            end_date = med.get("endDate")
            reminder_time = med.get("reminderTime")

            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date)

            pill_count = calculate_pill_count(dosage, start_date, end_date)

            pill_doc = {
                "pill_slot": idx,
                "pill_name": pill_name,
                "pill_count": pill_count,
                "startDate": start_date,
                "endDate": end_date,
                "reminderTime": reminder_time,
                "Dose_Period": None,
                "Time_Pill_Taken": None,
                "Avg_Time_Deviation (mins)": 0
            }

            pill_collection.insert_one(pill_doc)
            print(f"✅ Slot {idx}: {pill_name} with {pill_count} pills initialized.")
        except Exception as e:
            print(f"❌ Error initializing slot {idx}: {e}")

# --- Helper Functions ---
def send_schedule_to_mqtt(slot, dosage, reminder_time):
    topic = f"pillbox/schedule/{slot}"
    payload = {
        "dosage": dosage,
        "reminderTime": reminder_time
    }
    mqtt_client.publish(topic, json.dumps(payload))  # ✅ FIXED
    print(f"📤 Sent to {topic}: {payload}")


def get_medication_by_name(pill_name):
    return medication_collection.find_one({"pillName": pill_name})

# --- Fetch Pills and Push Schedule ---
def push_pill_schedule():
    print("📋 Fetching pills from DB and pushing schedule to MQTT...")

    pills = pill_collection.find()
    for pill in pills:
        pill_slot = pill.get("pill_slot")
        pill_name = pill.get("pill_name")
        reminder_time = pill.get("reminderTime")

        if not pill_slot or not pill_name or not reminder_time:
            print(f"⚠ Skipping invalid pill data: {pill}")
            continue

        med_data = get_medication_by_name(pill_name)
        if not med_data:
            print(f"⚠ No medication details found for '{pill_name}'")
            continue

        dosage = med_data.get("dosage", 1)
        print(f"🟢 Preparing Slot {pill_slot}: {pill_name}, Dosage: {dosage}, Time: {reminder_time}")
        send_schedule_to_mqtt(pill_slot, dosage, reminder_time)

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

        # --- Pill Intake ---
        if topic.startswith("pillbox/partition"):
            pill_slot = int(payload.get("partition"))
            pill_doc = pill_collection.find_one({"pill_slot": pill_slot})

            if not pill_doc or pill_doc.get("pill_count", 0) <= 0:
                print(f"⚠ No pills left or slot not found for slot {pill_slot}.")
                return

            reminder_time = pill_doc.get("reminderTime", "00:00 AM")
            try:
                scheduled_dt = datetime.strptime(reminder_time, "%I:%M %p")
                scheduled_minutes = scheduled_dt.hour * 60 + scheduled_dt.minute
            except Exception as e:
                print(f"⚠ Invalid reminderTime format: {reminder_time}")
                scheduled_minutes = hour * 60 + local_time.minute

            current_minutes = hour * 60 + local_time.minute
            deviation = abs(current_minutes - scheduled_minutes)
            time_taken = local_time.strftime("%H:%M")

            pill_collection.update_one(
                {"pill_slot": pill_slot},
                {
                    "$inc": {"pill_count": -1},
                    "$set": {
                        "Time_Pill_Taken": time_taken,
                        "Dose_Period": dose_period,
                        "Avg_Time_Deviation (mins)": deviation
                    }
                }
            )

            # --- Update History Collection ---
            week_ago = date_only - timedelta(days=7)
            records = history_collection.find({
                "User_ID": USER_ID,
                "Date": {"$gte": week_ago}
            })
            deviations = [doc.get("Avg_Time_Deviation (mins)", 0) for doc in records]
            avg_deviation = round(sum(deviations + [deviation]) / (len(deviations) + 1), 2)

            last_missed = history_collection.find_one(
                {"User_ID": USER_ID, "Missed_Dose": "Yes"},
                sort=[("Date", pymongo.DESCENDING)]
            )
            days_since_last_missed = (date_only.date() - last_missed["Date"].date()).days if last_missed else 0

            total_missed_week = history_collection.count_documents({
                "User_ID": USER_ID,
                "Date": {"$gte": week_ago},
                "Missed_Dose": "Yes"
            })

            # --- Update Outcome for Previous Dose ---
            previous_period = {"M": "N", "A": "M", "N": "A"}
            last_record = history_collection.find_one(
                {"User_ID": USER_ID, "Dose_Period": previous_period[dose_period]},
                sort=[("Date", pymongo.DESCENDING)]
            )
            if last_record:
                history_collection.update_one(
                    {"_id": last_record["_id"]},
                    {"$set": {"Outcome (Missed_Next_Dose)": "No"}}
                )

            history_collection.insert_one({
                "User_ID": USER_ID,
                "Date": date_only,
                "Dose_Period": dose_period,
                "Time_Pill_Taken": time_taken,
                "Scheduled_Time": reminder_time,
                "Missed_Dose": "No",
                "Days_Since_Last_Missed": days_since_last_missed,
                "Total_Missed_This_Week": total_missed_week,
                "Avg_Time_Deviation (mins)": avg_deviation,
                "Outcome (Missed_Next_Dose)": "Yes"
            })

            print(f"📘 ✅ Logged {pill_doc['pill_name']} | Slot {pill_slot} | Deviation: {deviation} mins")

    except Exception as e:
        print("❌ Error in message handler:", e)


# --- MQTT Setup ---
mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

try:
    mqtt_client.connect("localhost", 1883)
    mqtt_client.loop_start()
except Exception as e:
    print("❌ MQTT Connection Failed:", e)
    exit(1)

# --- Start ---
initialize_pillbox()
push_pill_schedule()

topics = [
    "pillbox/partition1", "pillbox/partition2", "pillbox/partition3", "pillbox/partition4",
]

for topic in topics:
    mqtt_client.subscribe((topic, 0))
    print(f"📣 Subscribed to {topic}")


print("🟢 MQTT to MongoDB bridge is running...")
mqtt_client.loop_forever()