import asyncio
import aiohttp
import logging
import motor.motor_asyncio
from datetime import datetime
import ssl
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import MONGODB_URI, DB_NAME, COLLECTION_NAME

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# MongoDB connection
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def check_url(session, url, car_id):
    """Check if a URL is accessible"""
    try:
        # Create SSL context that ignores certificate errors
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with session.head(url, headers=HEADERS, timeout=10, ssl=ssl_context) as response:
            status = response.status
            logger.info(f"URL: {url} - Status: {status}")
            return {
                "car_id": car_id,
                "url": url,
                "status": status,
                "is_valid": 200 <= status < 400
            }
    except Exception as e:
        logger.error(f"Error checking URL {url}: {str(e)}")
        return {
            "car_id": car_id,
            "url": url,
            "status": 0,
            "is_valid": False,
            "error": str(e)
        }

async def process_batch(session, cars, batch_size=10):
    """Process a batch of cars to check their URLs"""
    tasks = []
    for car in cars:
        if "source_url" in car and car["source_url"]:
            tasks.append(check_url(session, car["source_url"], str(car["_id"])))
    
    # Run tasks in batches to avoid overwhelming the server
    results = []
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        batch_results = await asyncio.gather(*batch)
        results.extend(batch_results)
        # Add a small delay between batches
        await asyncio.sleep(1)
    
    return results

async def remove_invalid_cars(invalid_car_ids):
    """Remove cars with invalid URLs from the database"""
    if not invalid_car_ids:
        logger.info("No invalid cars to remove")
        return 0
    
    # Convert string IDs to ObjectId
    from bson import ObjectId
    object_ids = [ObjectId(id) for id in invalid_car_ids]
    
    # Remove the cars
    result = await collection.delete_many({"_id": {"$in": object_ids}})
    deleted_count = result.deleted_count
    logger.info(f"Removed {deleted_count} cars with invalid URLs")
    return deleted_count

async def mark_invalid_cars(invalid_car_ids):
    """Mark cars with invalid URLs instead of removing them"""
    if not invalid_car_ids:
        logger.info("No invalid cars to mark")
        return 0
    
    # Convert string IDs to ObjectId
    from bson import ObjectId
    object_ids = [ObjectId(id) for id in invalid_car_ids]
    
    # Mark the cars
    result = await collection.update_many(
        {"_id": {"$in": object_ids}},
        {"$set": {
            "invalid_source_url": True,
            "checked_at": datetime.utcnow()
        }}
    )
    modified_count = result.modified_count
    logger.info(f"Marked {modified_count} cars with invalid URLs")
    return modified_count

async def main(remove=False):
    """Main function to check and clean the database"""
    logger.info("Starting database cleanup")
    start_time = datetime.utcnow()
    
    # Create SSL context for the session
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Create aiohttp session
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Get all cars with source URLs
        cars = await collection.find({"source_url": {"$exists": True}}).to_list(length=None)
        logger.info(f"Found {len(cars)} cars with source URLs")
        
        # Check URLs in batches
        results = await process_batch(session, cars)
        
        # Collect invalid car IDs
        invalid_car_ids = [r["car_id"] for r in results if not r["is_valid"]]
        logger.info(f"Found {len(invalid_car_ids)} cars with invalid URLs")
        
        # Generate a summary
        status_counts = {}
        for r in results:
            status = r["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info("Status code summary:")
        for status, count in sorted(status_counts.items()):
            logger.info(f"  Status {status}: {count} URLs")
        
        # Remove or mark invalid cars
        if remove:
            removed = await remove_invalid_cars(invalid_car_ids)
            logger.info(f"Removed {removed} cars with invalid URLs")
        else:
            marked = await mark_invalid_cars(invalid_car_ids)
            logger.info(f"Marked {marked} cars with invalid URLs")
    
    # Calculate elapsed time
    elapsed = datetime.utcnow() - start_time
    logger.info(f"Database cleanup completed in {elapsed.total_seconds():.2f} seconds")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Clean the database by checking source URLs")
    parser.add_argument("--remove", action="store_true", help="Remove cars with invalid URLs (default is to mark them)")
    args = parser.parse_args()
    
    asyncio.run(main(remove=args.remove)) 