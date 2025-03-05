from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import logging
from datetime import datetime
import motor.motor_asyncio
import aiohttp
import traceback

# Import configuration
from config import MONGODB_URI, DB_NAME, COLLECTION_NAME
from currency_service import get_currency_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin_app = FastAPI()

# Get the absolute path to the templates directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(BASE_DIR, "templates")

# Setup templates
templates = Jinja2Templates(directory=templates_dir)

# MongoDB connection
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

@admin_app.get("/", response_class=HTMLResponse)
async def admin_home(request: Request):
    """Admin home page"""
    return templates.TemplateResponse("admin.html", {"request": request})

@admin_app.get("/stats")
async def get_admin_stats():
    """Get database statistics for the admin page"""
    try:
        # Get total cars count
        total_cars = await collection.count_documents({})
        
        # Get count of cars with source URLs
        cars_with_url = await collection.count_documents({
            "source_url": {"$exists": True, "$ne": None, "$ne": ""},
            "invalid_source_url": {"$ne": True}
        })
        
        # Get count of cars without source URLs
        cars_without_url = await collection.count_documents({
            "$or": [
                {"source_url": {"$exists": False}},
                {"source_url": None},
                {"source_url": ""},
                {"invalid_source_url": True}
            ]
        })
        
        # Get currency service status
        currency_service = await get_currency_service()
        currency_status = {
            "status": "ok",
            "last_updated": currency_service.last_updated.isoformat() if hasattr(currency_service, 'last_updated') else None,
            "using_fallback": currency_service.using_fallback if hasattr(currency_service, 'using_fallback') else True
        }
        
        return {
            "total_cars": total_cars,
            "cars_with_url": cars_with_url,
            "cars_without_url": cars_without_url,
            "currency_status": currency_status
        }
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.post("/remove-unverified")
async def remove_unverified_cars():
    """Remove cars without verified source URLs from the database"""
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
            return {"message": "No cars to remove", "new_total": await collection.count_documents({})}
        
        # Delete the cars
        result = await collection.delete_many(query)
        new_total = await collection.count_documents({})
        
        return {
            "message": f"Successfully removed {result.deleted_count} cars",
            "deleted_count": result.deleted_count,
            "new_total": new_total
        }
    except Exception as e:
        logger.error(f"Error removing unverified cars: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.post("/update-rates")
async def update_exchange_rates():
    """Force an update of the currency exchange rates"""
    try:
        # Get the currency service
        currency_service = await get_currency_service()
        
        # Force an update
        await currency_service.update_rates(force=True)
        
        return {
            "message": "Successfully updated exchange rates",
            "last_updated": currency_service.last_updated.isoformat(),
            "using_fallback": currency_service.using_fallback
        }
    except Exception as e:
        logger.error(f"Error updating exchange rates: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.post("/remove-invalid-urls")
async def remove_invalid_url_cars():
    """Remove cars with invalid source URLs from the database"""
    try:
        # Find cars with invalid source URLs
        query = {"invalid_source_url": True}
        
        # Count how many cars match the criteria
        count = await collection.count_documents(query)
        logger.info(f"Found {count} cars with invalid source URLs")
        
        if count == 0:
            return {"message": "No cars with invalid URLs to remove", "new_total": await collection.count_documents({})}
        
        # Delete the cars
        result = await collection.delete_many(query)
        new_total = await collection.count_documents({})
        
        return {
            "message": f"Successfully removed {result.deleted_count} cars with invalid URLs",
            "deleted_count": result.deleted_count,
            "new_total": new_total
        }
    except Exception as e:
        logger.error(f"Error removing cars with invalid URLs: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.post("/check-invalid-urls")
async def check_invalid_urls():
    """Check for cars with invalid (404) source URLs and mark them"""
    try:
        # Find cars with source URLs that haven't been checked yet
        query = {
            "source_url": {"$exists": True, "$ne": None, "$ne": ""},
            "$or": [
                {"invalid_source_url": {"$exists": False}},
                {"last_url_check": {"$exists": False}}
            ]
        }
        
        # Count how many cars match the criteria
        count = await collection.count_documents(query)
        logger.info(f"Found {count} cars with unchecked source URLs")
        
        if count == 0:
            return {"message": "No cars to check", "checked": 0, "invalid": 0}
        
        # Limit to 100 cars per check to avoid overloading
        cars = await collection.find(query).limit(100).to_list(length=None)
        
        # Check each URL
        invalid_count = 0
        async with aiohttp.ClientSession() as session:
            for car in cars:
                car_id = car["_id"]
                url = car["source_url"]
                
                try:
                    # Try to fetch the URL with a timeout
                    async with session.head(url, timeout=10, allow_redirects=True) as response:
                        is_invalid = response.status == 404
                        
                        # Update the car with the check result
                        await collection.update_one(
                            {"_id": car_id},
                            {"$set": {
                                "invalid_source_url": is_invalid,
                                "last_url_check": datetime.utcnow()
                            }}
                        )
                        
                        if is_invalid:
                            invalid_count += 1
                            logger.info(f"Marked car {car_id} with invalid URL: {url}")
                
                except Exception as e:
                    # If we can't connect, mark as potentially invalid
                    logger.warning(f"Error checking URL {url} for car {car_id}: {str(e)}")
                    await collection.update_one(
                        {"_id": car_id},
                        {"$set": {
                            "url_check_error": str(e),
                            "last_url_check": datetime.utcnow()
                        }}
                    )
        
        # Get updated counts
        total_invalid = await collection.count_documents({"invalid_source_url": True})
        
        return {
            "message": f"Checked {len(cars)} cars, found {invalid_count} with invalid URLs",
            "checked": len(cars),
            "invalid": invalid_count,
            "total_invalid": total_invalid
        }
    except Exception as e:
        logger.error(f"Error checking invalid URLs: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@admin_app.get("/test", response_class=HTMLResponse)
async def admin_test(request: Request):
    """Admin test page"""
    return templates.TemplateResponse("admin_test.html", {"request": request})

@admin_app.get("/test-api", response_class=HTMLResponse)
async def admin_api_test(request: Request):
    """Admin API test page"""
    return templates.TemplateResponse("admin_api_test.html", {"request": request})

@admin_app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "service": "admin"}

@admin_app.post("/scrape-cars")
async def scrape_cars(request: Request):
    """Trigger the car scraper to fetch new cars"""
    try:
        # Get the request body
        data = await request.json()
        
        # Get the parameters from the request
        listing_urls = data.get('urls', [])
        max_cars = data.get('max_cars', 1000)
        min_delay = data.get('min_delay', 1.0)
        max_delay = data.get('max_delay', 3.0)
        max_images = data.get('max_images', 10)
        skip_sold = data.get('skip_sold', True)
        download_images = data.get('download_images', True)
        
        if not listing_urls:
            raise HTTPException(status_code=400, detail="No listing URLs provided")
        
        # Import the car scraper
        from car_scraper import CarScraper
        
        # Create and run the scraper
        scraper = CarScraper(
            max_cars=max_cars,
            delay_range=(min_delay, max_delay),
            max_images=max_images,
            skip_sold=skip_sold,
            download_images=download_images
        )
        
        cars_saved, images_saved = await scraper.scrape_cars(listing_urls)
        
        return {
            "message": f"Scraping complete. Saved {cars_saved} new cars and {images_saved} images.",
            "cars_saved": cars_saved,
            "images_saved": images_saved
        }
    
    except Exception as e:
        logger.error(f"Error scraping cars: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) 