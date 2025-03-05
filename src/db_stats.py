import asyncio
import logging
import sys
import os
from datetime import datetime
from tabulate import tabulate

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import MONGODB_URI, DB_NAME, COLLECTION_NAME
from motor.motor_asyncio import AsyncIOMotorClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def get_database_stats():
    """Get comprehensive statistics about the car database"""
    stats = {}
    
    # Total cars
    stats["total_cars"] = await collection.count_documents({})
    
    # Cars by country
    country_pipeline = [
        {"$group": {"_id": "$country", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    country_results = await collection.aggregate(country_pipeline).to_list(length=None)
    stats["cars_by_country"] = {r["_id"] or "Unknown": r["count"] for r in country_results}
    
    # Cars by brand (top 10)
    brand_pipeline = [
        {"$group": {"_id": "$brand", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    brand_results = await collection.aggregate(brand_pipeline).to_list(length=None)
    stats["cars_by_brand"] = {r["_id"] or "Unknown": r["count"] for r in brand_results}
    
    # Cars by fuel type
    fuel_pipeline = [
        {"$group": {"_id": "$fuel_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    fuel_results = await collection.aggregate(fuel_pipeline).to_list(length=None)
    stats["cars_by_fuel_type"] = {r["_id"] or "Unknown": r["count"] for r in fuel_results}
    
    # URL statistics
    stats["cars_with_source_url"] = await collection.count_documents({"source_url": {"$exists": True}})
    stats["cars_with_verified_url"] = await collection.count_documents({"url_verified": True})
    stats["cars_with_valid_url"] = await collection.count_documents({"url_valid": True})
    stats["cars_with_invalid_url"] = await collection.count_documents({"url_valid": False})
    
    # URL status codes
    status_pipeline = [
        {"$match": {"url_status": {"$exists": True}}},
        {"$group": {"_id": "$url_status", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    status_results = await collection.aggregate(status_pipeline).to_list(length=None)
    stats["url_status_codes"] = {r["_id"]: r["count"] for r in status_results}
    
    # Price statistics
    price_pipeline = [
        {"$match": {"cash_price": {"$exists": True, "$gt": 0}}},
        {"$group": {
            "_id": None,
            "avg_price": {"$avg": "$cash_price"},
            "min_price": {"$min": "$cash_price"},
            "max_price": {"$max": "$cash_price"},
            "count": {"$sum": 1}
        }}
    ]
    price_results = await collection.aggregate(price_pipeline).to_list(length=None)
    if price_results:
        stats["price_stats"] = {
            "average": int(price_results[0]["avg_price"]),
            "minimum": price_results[0]["min_price"],
            "maximum": price_results[0]["max_price"],
            "count": price_results[0]["count"]
        }
    
    # Recent scraping activity
    recent_pipeline = [
        {"$sort": {"scraped_at": -1}},
        {"$limit": 1},
        {"$project": {"_id": 0, "scraped_at": 1}}
    ]
    recent_results = await collection.aggregate(recent_pipeline).to_list(length=None)
    if recent_results:
        stats["most_recent_scrape"] = recent_results[0]["scraped_at"]
    
    return stats

def format_stats(stats):
    """Format statistics for display"""
    output = []
    
    # General stats
    output.append("\n=== GENERAL STATISTICS ===")
    general_table = [
        ["Total Cars", stats["total_cars"]],
        ["Cars with Source URL", stats["cars_with_source_url"]],
        ["Cars with Verified URL", stats["cars_with_verified_url"]],
        ["Cars with Valid URL", stats["cars_with_valid_url"]],
        ["Cars with Invalid URL", stats["cars_with_invalid_url"]]
    ]
    output.append(tabulate(general_table, tablefmt="simple"))
    
    # Most recent scrape
    if "most_recent_scrape" in stats:
        recent_time = stats["most_recent_scrape"]
        time_diff = datetime.utcnow() - recent_time
        output.append(f"\nMost recent scrape: {recent_time} ({time_diff.days} days, {time_diff.seconds // 3600} hours ago)")
    
    # Cars by country
    output.append("\n=== CARS BY COUNTRY ===")
    country_table = [[country, count] for country, count in stats["cars_by_country"].items()]
    output.append(tabulate(country_table, headers=["Country", "Count"], tablefmt="simple"))
    
    # Cars by brand
    output.append("\n=== TOP 10 BRANDS ===")
    brand_table = [[brand, count] for brand, count in stats["cars_by_brand"].items()]
    output.append(tabulate(brand_table, headers=["Brand", "Count"], tablefmt="simple"))
    
    # Cars by fuel type
    output.append("\n=== CARS BY FUEL TYPE ===")
    fuel_table = [[fuel_type or "Unknown", count] for fuel_type, count in stats["cars_by_fuel_type"].items()]
    output.append(tabulate(fuel_table, headers=["Fuel Type", "Count"], tablefmt="simple"))
    
    # URL status codes
    if stats["url_status_codes"]:
        output.append("\n=== URL STATUS CODES ===")
        status_table = [[code, count] for code, count in stats["url_status_codes"].items()]
        output.append(tabulate(status_table, headers=["Status Code", "Count"], tablefmt="simple"))
    
    # Price statistics
    if "price_stats" in stats:
        output.append("\n=== PRICE STATISTICS ===")
        price_table = [
            ["Average Price", f"{stats['price_stats']['average']:,} DKK"],
            ["Minimum Price", f"{stats['price_stats']['minimum']:,} DKK"],
            ["Maximum Price", f"{stats['price_stats']['maximum']:,} DKK"],
            ["Cars with Price", stats['price_stats']['count']]
        ]
        output.append(tabulate(price_table, tablefmt="simple"))
    
    return "\n".join(output)

async def main():
    """Main function to get and display database statistics"""
    try:
        logger.info("Fetching database statistics...")
        stats = await get_database_stats()
        
        # Format and display statistics
        formatted_stats = format_stats(stats)
        print(formatted_stats)
        
        # Save to file
        with open("db_stats.txt", "w") as f:
            f.write(formatted_stats)
        logger.info("Statistics saved to db_stats.txt")
        
    except Exception as e:
        logger.error(f"Error getting database statistics: {str(e)}")
    finally:
        # Close the MongoDB connection
        client.close()

if __name__ == "__main__":
    # Check if tabulate is installed
    try:
        from tabulate import tabulate
    except ImportError:
        print("The 'tabulate' package is required. Install it with: pip install tabulate")
        sys.exit(1)
        
    asyncio.run(main()) 