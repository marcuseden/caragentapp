import asyncio
import logging
from db import MongoDB
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URI, DB_NAME, COLLECTION_NAME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_connection():
    try:
        client = AsyncIOMotorClient(MONGODB_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Try to get one document
        count = await collection.count_documents({})
        print(f"Successfully connected to MongoDB. Found {count} documents.")
        
        if count > 0:
            first_doc = await collection.find_one()
            print("\nExample document:")
            print(first_doc)
            
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
    finally:
        client.close()

async def test_mongodb():
    db = MongoDB()
    
    try:
        # Initialize database
        await db.init_db()
        
        # Test storing a sample listing
        test_listing = {
            'brand': 'Test Brand',
            'model': 'Test Model',
            'year': 2024,
            'price': 100000,
            'currency': 'DKK',
            'country': 'denmark',
            'source_url': 'https://test.com',
            'scraped_at': datetime.utcnow()
        }
        
        await db.store_listings([test_listing])
        
        # Verify count
        count = await db.get_listing_count()
        logger.info(f"Total listings in database: {count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return False
    finally:
        await db.close()

async def main():
    logger.info("Testing MongoDB setup...")
    success = await test_mongodb()
    
    if success:
        logger.info("✅ MongoDB test completed successfully!")
    else:
        logger.error("❌ MongoDB test failed!")

if __name__ == "__main__":
    asyncio.run(test_connection()) 