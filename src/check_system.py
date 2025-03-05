import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.currency_service import get_currency_service
from src.config import MONGODB_URI, DB_NAME, COLLECTION_NAME
from motor.motor_asyncio import AsyncIOMotorClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def check_database():
    """Check database statistics"""
    print("\n=== DATABASE STATISTICS ===")
    
    # Count total cars
    total_cars = await collection.count_documents({})
    print(f"Total cars in database: {total_cars:,}")
    
    # Count cars with source URLs
    cars_with_url = await collection.count_documents({"source_url": {"$exists": True}})
    print(f"Cars with source URL: {cars_with_url:,} ({cars_with_url/total_cars*100:.1f}% of total)")
    
    # Count cars by country
    country_pipeline = [
        {"$group": {"_id": "$country", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    country_results = await collection.aggregate(country_pipeline).to_list(length=None)
    
    print("\nCars by country:")
    for r in country_results:
        country = r["_id"] or "Unknown"
        count = r["count"]
        print(f"  {country.ljust(10)}: {count:,}")
    
    # Get price statistics
    price_pipeline = [
        {"$match": {"cash_price": {"$exists": True, "$gt": 0}}},
        {"$group": {
            "_id": None,
            "avg": {"$avg": "$cash_price"},
            "min": {"$min": "$cash_price"},
            "max": {"$max": "$cash_price"},
            "count": {"$sum": 1}
        }}
    ]
    price_results = await collection.aggregate(price_pipeline).to_list(length=None)
    
    if price_results:
        print("\nPrice statistics (DKK):")
        r = price_results[0]
        print(f"  Average: {r['avg']:,.0f}")
        print(f"  Minimum: {r['min']:,.0f}")
        print(f"  Maximum: {r['max']:,.0f}")
        print(f"  Cars with price: {r['count']:,}")

async def check_currency_service():
    """Check currency service"""
    print("\n=== CURRENCY SERVICE ===")
    
    # Get currency service
    service = await get_currency_service()
    
    print(f"Exchange rates last updated: {service.last_updated}")
    
    # Show SEK rate
    sek_rate = service.rates.get('SEK', 0)
    print(f"Current DKK to SEK rate: {sek_rate:.4f}")
    
    # Test conversion
    test_amount = 10000
    sek_amount = service.convert(test_amount, 'DKK', 'SEK')
    print(f"Example: {test_amount:,} DKK = {sek_amount:,.2f} SEK")

async def main():
    """Run all checks"""
    print("=== SYSTEM CHECK ===")
    print(f"Time: {datetime.now()}")
    
    try:
        await check_currency_service()
        await check_database()
        print("\nSystem check completed successfully!")
    except Exception as e:
        logger.error(f"Error during system check: {str(e)}")
    finally:
        # Close MongoDB connection
        client.close()

if __name__ == "__main__":
    asyncio.run(main()) 