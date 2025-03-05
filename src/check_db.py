import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URI, DB_NAME, COLLECTION_NAME

async def check_db():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    count = await collection.count_documents({})
    print(f"Found {count} documents in database")
    
    if count > 0:
        first_doc = await collection.find_one()
        print("\nFirst document:")
        print(first_doc)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_db()) 