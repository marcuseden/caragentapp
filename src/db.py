import motor.motor_asyncio
import logging
from datetime import datetime
from config import MONGODB_URI, DB_NAME, COLLECTION_NAME

logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        
    async def init_db(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        
    async def store_listings(self, listings):
        if not listings:
            return 0
            
        # Add timestamp to each listing
        for listing in listings:
            if 'scraped_at' not in listing:
                listing['scraped_at'] = datetime.utcnow()
        
        # Insert listings
        result = await self.collection.insert_many(listings)
        return len(result.inserted_ids)
        
    async def get_listing_count(self):
        return await self.collection.count_documents({})
        
    async def close(self):
        if self.client:
            self.client.close() 