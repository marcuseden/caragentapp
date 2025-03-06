import motor.motor_asyncio
import logging
import os
from datetime import datetime
from bson import ObjectId

# MongoDB configuration
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "car_database")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "cars")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection - lazy initialization
client = None
db = None
collection = None

async def get_db_collection():
    """Get MongoDB collection with lazy initialization"""
    global client, db, collection
    if client is None:
        logger.info("Initializing MongoDB connection")
        try:
            # Initialize the connection only when needed
            client = motor.motor_asyncio.AsyncIOMotorClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            db = client[DB_NAME]
            collection = db[COLLECTION_NAME]
            logger.info("MongoDB connection initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing MongoDB connection: {str(e)}")
            raise
    return collection

async def get_cars(limit=10, skip=0, filters=None):
    """Get cars from the database with pagination and filtering"""
    collection = await get_db_collection()
    query = filters or {}
    
    try:
        # Get cars with pagination
        cars = await collection.find(query).sort("_id", -1).skip(skip).limit(limit).to_list(length=None)
        total = await collection.count_documents(query)
        
        # Convert ObjectId to string for JSON serialization
        for car in cars:
            car["_id"] = str(car["_id"])
        
        return cars, total
    except Exception as e:
        logger.error(f"Error getting cars: {str(e)}")
        return [], 0

async def get_car_by_id(car_id):
    """Get a single car by ID"""
    collection = await get_db_collection()
    try:
        car = await collection.find_one({"_id": ObjectId(car_id)})
        if car:
            car["_id"] = str(car["_id"])
        return car
    except Exception as e:
        logger.error(f"Error getting car by ID: {str(e)}")
        return None

async def save_car(car_data):
    """Save a car to the database"""
    collection = await get_db_collection()
    try:
        # Add timestamp if not present
        if "scraped_at" not in car_data:
            car_data["scraped_at"] = datetime.utcnow().isoformat()
            
        result = await collection.insert_one(car_data)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Error saving car: {str(e)}")
        raise 