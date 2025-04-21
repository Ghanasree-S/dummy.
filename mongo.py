import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb+srv://ghanasreesk24:vitals@vitals.55nbs.mongodb.net/?retryWrites=true&w=majority&appName=Vitals"

async def test_connection():
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client["health_vitals_db"]
        await db.command("ping")  # Ensure async execution
        print("MongoDB connection successful!")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())  # Ensures safe execution in main block
