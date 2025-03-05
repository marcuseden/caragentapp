import asyncio
import motor.motor_asyncio
from src.config import MONGODB_URI, DB_NAME, COLLECTION_NAME

async def test_mongodb():
    """Test the MongoDB connection"""
    print(f"Connecting to MongoDB: {MONGODB_URI}")
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Count documents
    count = await collection.count_documents({})
    print(f"Total documents in {DB_NAME}.{COLLECTION_NAME}: {count}")
    
    # Get a sample document
    sample = await collection.find_one({})
    if sample:
        print("Sample document:")
        print(sample)
    else:
        print("No documents found")

if __name__ == "__main__":
    asyncio.run(test_mongodb()) 