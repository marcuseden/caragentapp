import asyncio
import logging
import random
import time
from datetime import datetime

# Fix the import path
from src.config import get_proxy_url

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample car data for testing
SAMPLE_CARS = [
    {
        'brand': 'Tesla',
        'model': 'Model 3',
        'year': 2022,
        'cash_price': 349000,
        'mileage': 15000,
        'fuel_type': 'El',
        'country': 'denmark',
        'range_km': 510,
        'battery_capacity': 75,
        'energy_consumption': 160,
        'equipment': ['Autopilot', 'Heated seats', 'Premium sound']
    },
    {
        'brand': 'Volkswagen',
        'model': 'ID.4',
        'year': 2021,
        'cash_price': 299000,
        'mileage': 25000,
        'fuel_type': 'El',
        'country': 'germany',
        'range_km': 450,
        'battery_capacity': 77,
        'energy_consumption': 170,
        'equipment': ['Adaptive cruise control', 'LED headlights', 'Panoramic roof']
    },
    # Add more sample cars as needed
]

async def store_sample_data():
    """Store sample car data in MongoDB"""
    from src.db import MongoDB
    
    db = MongoDB()
    await db.init_db()
    
    # Add timestamp to each car
    for car in SAMPLE_CARS:
        car['scraped_at'] = datetime.utcnow()
    
    count = await db.store_listings(SAMPLE_CARS)
    logger.info(f"Stored {count} sample cars in database")
    
    await db.close()

async def main():
    """Main function to run the test scraper"""
    try:
        logger.info("Starting test scraper")
        
        # Simulate scraping delay
        delay = random.uniform(1, 3)
        logger.info(f"Simulating scraping (waiting {delay:.1f} seconds)")
        await asyncio.sleep(delay)
        
        # Store sample data
        await store_sample_data()
        
        logger.info("Test scraping completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in test scraper: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(main()) 