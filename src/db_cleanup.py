import asyncio
import logging
import sys
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import MONGODB_URI, DB_NAME, COLLECTION_NAME

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def remove_unverified_cars(dry_run=True):
    """
    Remove cars without verified source URLs from the database
    
    Args:
        dry_run (bool): If True, only show what would be deleted without actually deleting
    """
    try:
        # Find cars without source URLs or with invalid source URLs
        query = {
            "$or": [
                {"source_url": {"$exists": False}},
                {"source_url": None},
                {"source_url": ""},
                {"invalid_source_url": True}
            ]
        }
        
        # Count how many cars match the criteria
        count = await collection.count_documents(query)
        logger.info(f"Found {count} cars without verified source URLs")
        
        if count == 0:
            logger.info("No cars to remove")
            return
        
        # Get a sample of cars that would be deleted
        sample = await collection.find(query).limit(5).to_list(length=None)
        logger.info("Sample of cars that would be removed:")
        for car in sample:
            logger.info(f"  {car.get('_id')}: {car.get('brand')} {car.get('model')} ({car.get('year')})")
        
        if dry_run:
            logger.info(f"DRY RUN: Would remove {count} cars")
        else:
            # Actually delete the cars
            result = await collection.delete_many(query)
            logger.info(f"Removed {result.deleted_count} cars from the database")
            
            # Log the new total count
            new_count = await collection.count_documents({})
            logger.info(f"Database now contains {new_count} cars")
    
    except Exception as e:
        logger.error(f"Error removing unverified cars: {str(e)}")
    finally:
        # Close the MongoDB connection
        client.close()

async def main():
    """Main function to run the cleanup"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up the car database by removing unverified listings')
    parser.add_argument('--execute', action='store_true', help='Actually delete the cars (default is dry run)')
    args = parser.parse_args()
    
    if args.execute:
        logger.warning("EXECUTING ACTUAL DELETION - THIS CANNOT BE UNDONE")
        await remove_unverified_cars(dry_run=False)
    else:
        logger.info("Running in DRY RUN mode - no cars will be deleted")
        await remove_unverified_cars(dry_run=True)

if __name__ == "__main__":
    asyncio.run(main()) 