import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import MONGODB_URI, DB_NAME, COLLECTION_NAME
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection
client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def get_simple_stats():
    """Get basic statistics about the car database"""
    # Total cars
    total_cars = await collection.count_documents({})
    print(f"Total cars in database: {total_cars}")
    
    # Cars with source URLs
    cars_with_url = await collection.count_documents({"source_url": {"$exists": True}})
    print(f"Cars with source URL: {cars_with_url}")
    
    # Cars by country
    country_pipeline = [
        {"$group": {"_id": "$country", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    country_results = await collection.aggregate(country_pipeline).to_list(length=None)
    print("\nCars by country:")
    for r in country_results:
        country = r["_id"] or "Unknown"
        count = r["count"]
        print(f"  {country}: {count}")
    
    # Most recent scrape
    recent_pipeline = [
        {"$sort": {"scraped_at": -1}},
        {"$limit": 1},
        {"$project": {"_id": 0, "scraped_at": 1}}
    ]
    recent_results = await collection.aggregate(recent_pipeline).to_list(length=None)
    if recent_results:
        recent_time = recent_results[0]["scraped_at"]
        time_diff = datetime.utcnow() - recent_time
        print(f"\nMost recent scrape: {recent_time} ({time_diff.days} days, {time_diff.seconds // 3600} hours ago)")

if __name__ == "__main__":
    asyncio.run(get_simple_stats())
    print("\nDatabase statistics check complete.") 