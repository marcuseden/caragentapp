import asyncio
import aiohttp
import logging
from datetime import datetime
import ssl
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import MONGODB_URI, DB_NAME, COLLECTION_NAME
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("url_verification.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# MongoDB connection
client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def verify_url(session, car):
    """Verify if a car's source URL is still valid"""
    car_id = car["_id"]
    url = car["source_url"]
    
    try:
        # Create SSL context that ignores certificate errors
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with session.head(url, headers=HEADERS, timeout=10, ssl=ssl_context) as response:
            status = response.status
            is_valid = 200 <= status < 400
            
            # Update the car with verification result
            await collection.update_one(
                {"_id": car_id},
                {"$set": {
                    "url_verified": True,
                    "url_valid": is_valid,
                    "url_status": status,
                    "verified_at": datetime.utcnow()
                }}
            )
            
            return {
                "car_id": str(car_id),
                "url": url,
                "status": status,
                "is_valid": is_valid
            }
    except Exception as e:
        # Update the car with verification error
        await collection.update_one(
            {"_id": car_id},
            {"$set": {
                "url_verified": True,
                "url_valid": False,
                "url_error": str(e),
                "verified_at": datetime.utcnow()
            }}
        )
        
        logger.error(f"Error verifying URL {url}: {str(e)}")
        return {
            "car_id": str(car_id),
            "url": url,
            "status": 0,
            "is_valid": False,
            "error": str(e)
        }

async def process_batch(session, cars, batch_size=20):
    """Process a batch of cars to verify their URLs"""
    tasks = []
    for car in cars:
        tasks.append(verify_url(session, car))
    
    # Run tasks in batches to avoid overwhelming servers
    results = []
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        batch_results = await asyncio.gather(*batch)
        results.extend(batch_results)
        
        # Log progress
        logger.info(f"Verified {min(i+batch_size, len(tasks))}/{len(tasks)} URLs")
        
        # Add a small delay between batches
        await asyncio.sleep(2)
    
    return results

async def main():
    """Main function to verify all source URLs"""
    logger.info("Starting URL verification")
    start_time = datetime.utcnow()
    
    # Create SSL context for the session
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Create aiohttp session with SSL context
    connector = aiohttp.TCPConnector(ssl=ssl_context, limit=20)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Get all cars with source URLs that haven't been verified
        query = {
            "source_url": {"$exists": True},
            "$or": [
                {"url_verified": {"$exists": False}},
                {"url_verified": False}
            ]
        }
        
        cars = await collection.find(query).to_list(length=None)
        logger.info(f"Found {len(cars)} cars with unverified source URLs")
        
        if not cars:
            logger.info("No cars to verify")
            return
        
        # Process cars in batches
        results = await process_batch(session, cars)
        
        # Generate summary
        valid_count = sum(1 for r in results if r["is_valid"])
        invalid_count = len(results) - valid_count
        
        logger.info(f"URL verification completed:")
        logger.info(f"  Total URLs: {len(results)}")
        logger.info(f"  Valid URLs: {valid_count} ({valid_count/len(results)*100:.1f}%)")
        logger.info(f"  Invalid URLs: {invalid_count} ({invalid_count/len(results)*100:.1f}%)")
        
        # Status code summary
        status_counts = {}
        for r in results:
            status = r["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info("Status code summary:")
        for status, count in sorted(status_counts.items()):
            logger.info(f"  Status {status}: {count} URLs")
    
    # Calculate elapsed time
    elapsed = datetime.utcnow() - start_time
    logger.info(f"URL verification completed in {elapsed.total_seconds():.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main()) 