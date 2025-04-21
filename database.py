from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection string (replace with your actual URL)
MONGO_URL = "mongodb+srv://ghanasreesk24:vitals@vitals.55nbs.mongodb.net/?retryWrites=true&w=majority&appName=Vitals"

# Initialize the MongoDB client
client = AsyncIOMotorClient(MONGO_URL)

# Access the database and collection
db = client["health_vitals_db"]  # Database name
health_vitals_collection = db["health_vitals_collection"]  # Collection name
