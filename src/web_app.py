from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import motor.motor_asyncio
import os
import logging
from datetime import datetime
from bson import ObjectId

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import MONGODB_URI, DB_NAME, COLLECTION_NAME
from src.manufacturer_db import get_manufacturer_specs
from src.currency_service import get_currency_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Get the absolute path to the static and templates directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

# Mount static files directory
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates
templates = Jinja2Templates(directory=templates_dir)

# MongoDB connection
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def format_number(value, suffix=''):
    """Format number with thousand separators and optional suffix"""
    if isinstance(value, (int, float)):
        return f"{value:,}{suffix}"
    return 'N/A'

def format_currency(value, currency='DKK'):
    """Format currency with thousand separators and currency code"""
    if isinstance(value, (int, float)):
        return f"{value:,.0f} {currency}"
    return 'N/A'

@app.get("/", response_class=HTMLResponse)
async def list_view(request: Request):
    return templates.TemplateResponse("list.html", {"request": request})

@app.get("/car/{car_id}", response_class=HTMLResponse)
async def detail_view(request: Request, car_id: str):
    return templates.TemplateResponse("detail.html", {"request": request, "car_id": car_id})

@app.get("/api/cars")
async def get_cars():
    logger.info("Getting all cars")
    try:
        # Filter out cars with invalid source URLs
        query = {
            "$or": [
                {"invalid_source_url": {"$exists": False}},
                {"invalid_source_url": False}
            ]
        }
        
        cars = await collection.find(query).sort("scraped_at", -1).to_list(length=None)
        logger.info(f"Found {len(cars)} valid cars")
        
        # Get currency service for conversion
        currency_service = await get_currency_service()
        
        result = []
        for car in cars:
            # Get price in DKK
            price_dkk = car.get("cash_price", 0)
            
            # Convert to SEK
            price_sek = currency_service.convert(price_dkk, "DKK", "SEK")
            
            result.append({
                "id": str(car["_id"]),
                "brand": car.get("brand", "Unknown"),
                "model": car.get("model", ""),
                "year": car.get("year", "N/A"),
                "mileage": format_number(car.get("mileage"), " km"),
                "price": format_number(price_dkk, " DKK"),
                "price_sek": format_currency(price_sek, "SEK"),
                "original_price": {
                    "value": price_dkk,
                    "currency": "DKK"
                },
                "country": car.get("country", "N/A")
            })
        
        logger.info(f"Returning {len(result)} formatted cars")
        return result
    except Exception as e:
        logger.error(f"Error getting cars: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/car/{car_id}")
async def get_car(car_id: str):
    try:
        car = await collection.find_one({"_id": ObjectId(car_id)})
        if car:
            car["_id"] = str(car["_id"])
            car["scraped_at"] = car["scraped_at"].isoformat()
            
            # Format numeric values
            if "cash_price" in car:
                # Get currency service for conversion
                currency_service = await get_currency_service()
                
                # Original price in DKK
                price_dkk = car["cash_price"]
                car["cash_price_formatted"] = format_number(price_dkk, " DKK")
                
                # Price in SEK
                price_sek = currency_service.convert(price_dkk, "DKK", "SEK")
                car["cash_price_sek"] = format_currency(price_sek, "SEK")
                
                # Add exchange rate info
                car["exchange_rate"] = currency_service.get_formatted_rate("DKK", "SEK")
                
            if "mileage" in car:
                car["mileage_formatted"] = format_number(car["mileage"], " km")
                
            # Handle invalid source URLs
            if "invalid_source_url" in car and car["invalid_source_url"]:
                car["source_url"] = None
                car["source_url_invalid"] = True
            
            # Check if we need to supplement with manufacturer data
            missing_fields = 0
            important_fields = ['transmission', 'body_type', 'engine_size', 'power']
            for field in important_fields:
                if field not in car or not car[field]:
                    missing_fields += 1
            
            # If more than 2 important fields are missing, try to get manufacturer data
            if missing_fields >= 2 and 'brand' in car and 'model' in car:
                mfg_specs = get_manufacturer_specs(car['brand'], car['model'])
                if mfg_specs:
                    # Add manufacturer data for missing fields
                    for key, value in mfg_specs.items():
                        if key not in car or not car[key]:
                            car[key] = value
                    car['manufacturer_data_added'] = True
                
            return car
        raise HTTPException(status_code=404, detail="Car not found")
    except Exception as e:
        logger.error(f"Error getting car {car_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/cars/count")
async def get_car_count():
    count = await collection.count_documents({})
    return {"total": count}

@app.get("/api/cars/similar")
async def get_similar_cars(brand: str, model: str, id: str):
    """Get similar cars (same brand and model) in different countries"""
    try:
        # Exclude the current car
        query = {
            "brand": brand,
            "model": model,
            "_id": {"$ne": ObjectId(id)}
        }
        
        similar_cars = await collection.find(query).limit(6).to_list(length=None)
        
        # Get currency service for conversion
        currency_service = await get_currency_service()
        
        # Format the results
        for car in similar_cars:
            car["_id"] = str(car["_id"])
            car["scraped_at"] = car["scraped_at"].isoformat()
            
            # Add SEK price
            if "cash_price" in car:
                price_dkk = car["cash_price"]
                price_sek = currency_service.convert(price_dkk, "DKK", "SEK")
                car["cash_price_sek"] = format_currency(price_sek, "SEK")
        
        return similar_cars
    except Exception as e:
        logger.error(f"Error getting similar cars: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/source-urls")
async def debug_source_urls():
    """Debug endpoint to check source URLs in the database"""
    try:
        # Get 10 random cars
        sample_cars = await collection.find().limit(10).to_list(length=None)
        
        result = []
        for car in sample_cars:
            result.append({
                "id": str(car["_id"]),
                "brand": car.get("brand", "Unknown"),
                "model": car.get("model", ""),
                "has_source_url": "source_url" in car,
                "source_url": car.get("source_url", None)
            })
        
        # Also get counts
        total_cars = await collection.count_documents({})
        cars_with_url = await collection.count_documents({"source_url": {"$exists": True}})
        
        return {
            "total_cars": total_cars,
            "cars_with_url": cars_with_url,
            "percentage_with_url": round((cars_with_url / total_cars) * 100, 2) if total_cars > 0 else 0,
            "sample": result
        }
    except Exception as e:
        logger.error(f"Error checking source URLs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/currency/status")
async def get_currency_status():
    """Get the status of the currency service"""
    try:
        currency_service = await get_currency_service()
        
        # Get available currencies
        available_currencies = list(currency_service.rates.keys()) if hasattr(currency_service, 'rates') else []
        
        # Get example rates
        example_rates = {}
        if hasattr(currency_service, 'rates') and 'DKK' in currency_service.rates:
            for currency in ['SEK', 'EUR', 'USD']:
                if currency in currency_service.rates['DKK']:
                    example_rates[currency] = currency_service.rates['DKK'][currency]
        
        return {
            "status": "ok",
            "service_info": {
                "last_updated": currency_service.last_updated.isoformat() if hasattr(currency_service, 'last_updated') else None,
                "using_fallback": currency_service.using_fallback if hasattr(currency_service, 'using_fallback') else True,
                "available_currencies": available_currencies,
                "example_rates": example_rates
            }
        }
    except Exception as e:
        logger.error(f"Error getting currency status: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/admin", response_class=HTMLResponse)
async def admin_view(request: Request):
    """Admin page for database management"""
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/currency-test", response_class=HTMLResponse)
async def currency_test_view(request: Request):
    """Currency test page"""
    return templates.TemplateResponse("currency_test.html", {"request": request})

@app.get("/test", response_class=HTMLResponse)
async def test_view(request: Request):
    """Test page"""
    return HTMLResponse("<html><body><h1>Test Page Works!</h1></body></html>")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Initialize currency service
    await get_currency_service()
    logger.info("Currency service initialized")

@app.get("/api/car/{car_id}/complete")
async def get_complete_car_info(car_id: str):
    """Get complete car information including contact details and images"""
    try:
        # First, get the basic car info
        car = await collection.find_one({"_id": ObjectId(car_id)})
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        
        # Format the car ID
        car["_id"] = str(car["_id"])
        
        # Check if we have a valid source URL
        if not car.get("source_url") or car.get("invalid_source_url"):
            return {
                "success": False,
                "message": "No valid source URL available for this car",
                "car": car
            }
        
        # Import the appropriate scraper based on the car's country
        country = car.get("country", "").lower()
        source_url = car.get("source_url")
        
        try:
            # Dynamically import the appropriate scraper
            if country == "denmark":
                from src.scrapers.denmark import fetch_complete_car_info
            elif country == "sweden":
                from src.scrapers.sweden import fetch_complete_car_info
            elif country == "germany":
                from src.scrapers.germany import fetch_complete_car_info
            else:
                return {
                    "success": False,
                    "message": f"No scraper available for country: {country}",
                    "car": car
                }
            
            # Fetch complete information
            logger.info(f"Fetching complete info for car {car_id} from {source_url}")
            complete_info = await fetch_complete_car_info(source_url)
            
            if not complete_info:
                return {
                    "success": False,
                    "message": "Failed to fetch complete information",
                    "car": car
                }
            
            # Merge the complete info with the existing car data
            car.update(complete_info)
            
            # Update the car in the database with the complete info
            await collection.update_one(
                {"_id": ObjectId(car_id)},
                {"$set": {
                    "complete_info": complete_info,
                    "last_complete_fetch": datetime.utcnow()
                }}
            )
            
            return {
                "success": True,
                "message": "Successfully fetched complete car information",
                "car": car
            }
            
        except ImportError as e:
            logger.error(f"Error importing scraper for {country}: {str(e)}")
            return {
                "success": False,
                "message": f"Scraper not implemented for {country}",
                "car": car
            }
        except Exception as e:
            logger.error(f"Error fetching complete car info: {str(e)}")
            return {
                "success": False,
                "message": f"Error fetching complete information: {str(e)}",
                "car": car
            }
            
    except Exception as e:
        logger.error(f"Error getting complete car info for {car_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/stats")
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/remove-unverified")
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/update-rates")
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/remove-invalid-urls")
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
        raise HTTPException(status_code=500, detail=str(e)) 