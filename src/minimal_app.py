from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import motor.motor_asyncio
import os
import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection - lazy initialization
client = None
db = None
collection = None

# MongoDB configuration
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "car_database")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "cars")

async def get_db_collection():
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

# Helper function to generate navigation HTML
def get_nav_html():
    return """
    <nav class="bg-gray-800 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <a href="/" class="text-xl font-bold">CarAgentApp</a>
            <div class="space-x-4">
                <a href="/" class="hover:text-gray-300">Home</a>
                <a href="/stats" class="hover:text-gray-300">Stats</a>
                <a href="/health" class="hover:text-gray-300">Health</a>
            </div>
        </div>
    </nav>
    """

# Helper function to generate a page wrapper
def get_page_html(title, content):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} | CarAgentApp</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col">
        {get_nav_html()}
        
        <div class="flex-grow">
            {content}
        </div>
        
        <footer class="bg-gray-800 text-white py-6 mt-12">
            <div class="container mx-auto px-4">
                <div class="flex flex-col md:flex-row justify-between items-center">
                    <div class="mb-4 md:mb-0">
                        <p>&copy; 2023 CarAgentApp. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </footer>
    </body>
    </html>
    """

@app.get("/", response_class=HTMLResponse)
async def home_view(request: Request):
    """Home page view"""
    content = """
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-6">CarAgentApp</h1>
        
        <div class="bg-white p-6 rounded-lg shadow-md">
            <p class="mb-4">Welcome to CarAgentApp!</p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <a href="/stats" class="p-4 bg-blue-50 rounded-lg hover:bg-blue-100">
                    <h2 class="text-lg font-semibold text-blue-800">View Statistics</h2>
                    <p class="text-sm text-gray-600">See database statistics and metrics</p>
                </a>
                <a href="/health" class="p-4 bg-purple-50 rounded-lg hover:bg-purple-100">
                    <h2 class="text-lg font-semibold text-purple-800">Health Check</h2>
                    <p class="text-sm text-gray-600">Check application health</p>
                </a>
            </div>
        </div>
    </div>
    """
    
    return HTMLResponse(get_page_html("Home", content))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok", 
        "environment": os.environ.get("VERCEL_ENV", "unknown"),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/stats", response_class=HTMLResponse)
async def stats_view(request: Request):
    """Stats view"""
    try:
        # Create the content for the stats page
        content = """
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-6">Database Statistics</h1>
            
            <div id="loading" class="bg-white p-6 rounded-lg shadow-md">
                <p class="text-center text-gray-500">Loading statistics...</p>
            </div>
            
            <div id="stats-container" class="bg-white p-6 rounded-lg shadow-md hidden">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="p-4 bg-blue-50 rounded-lg">
                        <h2 class="text-lg font-semibold text-blue-800">Total Cars</h2>
                        <p id="total-cars" class="text-3xl font-bold">0</p>
                    </div>
                    <div class="p-4 bg-green-50 rounded-lg">
                        <h2 class="text-lg font-semibold text-green-800">Cars with URL</h2>
                        <p id="cars-with-url" class="text-3xl font-bold">0</p>
                    </div>
                    <div class="p-4 bg-yellow-50 rounded-lg">
                        <h2 class="text-lg font-semibold text-yellow-800">Cars without URL</h2>
                        <p id="cars-without-url" class="text-3xl font-bold">0</p>
                    </div>
                </div>
            </div>
            
            <div id="error-container" class="bg-white p-6 rounded-lg shadow-md hidden">
                <p id="error-message" class="text-red-500">Error loading statistics.</p>
                <div class="mt-4">
                    <button id="try-test-api" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Try Test API
                    </button>
                </div>
            </div>
        </div>
        
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const loadingContainer = document.getElementById('loading');
                const statsContainer = document.getElementById('stats-container');
                const errorContainer = document.getElementById('error-container');
                const errorMessage = document.getElementById('error-message');
                const tryTestApiBtn = document.getElementById('try-test-api');
                
                async function loadStats() {
                    try {
                        const response = await fetch('/api/test-stats');
                        
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        
                        const data = await response.json();
                        
                        // Update the stats
                        document.getElementById('total-cars').textContent = data.total_cars.toLocaleString();
                        document.getElementById('cars-with-url').textContent = data.cars_with_url.toLocaleString();
                        document.getElementById('cars-without-url').textContent = data.cars_without_url.toLocaleString();
                        
                        // Hide loading, show stats
                        loadingContainer.classList.add('hidden');
                        statsContainer.classList.remove('hidden');
                    } catch (error) {
                        console.error('Error loading stats:', error);
                        errorMessage.textContent = `Error loading statistics: ${error.message}`;
                        
                        // Hide loading, show error
                        loadingContainer.classList.add('hidden');
                        errorContainer.classList.remove('hidden');
                    }
                }
                
                // Try loading stats
                loadStats();
                
                // Add event listener for the test API button
                tryTestApiBtn.addEventListener('click', async function() {
                    try {
                        tryTestApiBtn.disabled = true;
                        tryTestApiBtn.textContent = 'Loading...';
                        
                        const response = await fetch('/api/test-stats');
                        
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        
                        const data = await response.json();
                        
                        // Update the stats with test data
                        document.getElementById('total-cars').textContent = data.total_cars.toLocaleString();
                        document.getElementById('cars-with-url').textContent = data.cars_with_url.toLocaleString();
                        document.getElementById('cars-without-url').textContent = data.cars_without_url.toLocaleString();
                        
                        // Show the stats container
                        errorContainer.classList.add('hidden');
                        statsContainer.classList.remove('hidden');
                    } catch (error) {
                        console.error('Error loading test stats:', error);
                        errorMessage.textContent = `Error loading test statistics: ${error.message}`;
                    } finally {
                        tryTestApiBtn.disabled = false;
                        tryTestApiBtn.textContent = 'Try Test API';
                    }
                });
            });
        </script>
        """
        
        return HTMLResponse(get_page_html("Database Stats", content))
    except Exception as e:
        logger.error(f"Error rendering stats: {str(e)}")
        content = """
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-6">Database Statistics</h1>
            <div class="bg-white p-6 rounded-lg shadow-md">
                <p class="text-red-500">Error loading statistics. Please try again later.</p>
            </div>
        </div>
        """
        return HTMLResponse(get_page_html("Database Stats", content))

@app.get("/api/test-stats")
async def test_stats_api():
    """Test stats API endpoint"""
    return {
        "message": "Stats API is working",
        "total_cars": 100,
        "cars_with_url": 75,
        "cars_without_url": 25,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests to help debug routing issues"""
    path = request.url.path
    logger.info(f"Request path: {path}")
    
    try:
        response = await call_next(request)
        logger.info(f"Response status for {path}: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing request {path}: {str(e)}")
        raise

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 