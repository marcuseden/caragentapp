from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import motor.motor_asyncio
import os
import logging
from datetime import datetime
from bson import ObjectId
import asyncio
import subprocess
import sys
from fastapi.middleware.cors import CORSMiddleware

# Import configuration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import MONGODB_URI, DB_NAME, COLLECTION_NAME, URLS
from src.manufacturer_db import get_manufacturer_specs
from src.currency_service import get_currency_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add this to debug API routes
@app.get("/debug-routes")
async def debug_routes():
    """Debug endpoint to list all registered routes"""
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": route.methods if hasattr(route, "methods") else None
        })
    return {"routes": routes}

# Get the absolute path to the static and templates directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

# Mount static files directory
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates
logger.info(f"Templates directory: {templates_dir}")
logger.info(f"Templates directory exists: {os.path.exists(templates_dir)}")
templates = Jinja2Templates(directory=templates_dir)

# Check if template files exist
opportunities_template = os.path.join(templates_dir, "opportunities.html")
scraper_template = os.path.join(templates_dir, "scraper.html")
logger.info(f"Opportunities template exists: {os.path.exists(opportunities_template)}")
logger.info(f"Scraper template exists: {os.path.exists(scraper_template)}")

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

# Helper function to generate navigation HTML
def get_nav_html():
    return """
    <nav class="bg-gray-800 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <a href="/" class="text-xl font-bold">CarAgentApp</a>
            <div class="space-x-4">
                <a href="/" class="hover:text-gray-300">Home</a>
                <a href="/stats" class="hover:text-gray-300">Stats</a>
                <a href="/scrape" class="hover:text-gray-300">Scraper</a>
                <a href="/admin" class="hover:text-gray-300">Admin</a>
                <a href="/test-page" class="hover:text-gray-300">Test Page</a>
                <a href="/api-test" class="hover:text-gray-300">API Test</a>
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
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
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
    try:
        # Get some recent cars from the database
        cars = await collection.find().sort("_id", -1).limit(12).to_list(length=None)
        
        # Format the cars for display
        car_html = ""
        for car in cars:
            car_id = str(car.get("_id", ""))
            brand = car.get("brand", "Unknown")
            model = car.get("model", "")
            year = car.get("year", "")
            price = format_currency(car.get("cash_price", 0))
            
            car_html += f"""
            <div class="bg-white rounded-lg shadow-md overflow-hidden">
                <div class="p-4">
                    <h3 class="text-lg font-semibold">{brand} {model}</h3>
                    <div class="mt-2 flex justify-between">
                        <span class="text-gray-600">{year}</span>
                        <span class="font-bold">{price}</span>
                    </div>
                    <div class="mt-3">
                        <a href="/car/{car_id}" class="text-blue-600 hover:text-blue-800">View Details</a>
                    </div>
                </div>
            </div>
            """
        
        # Create the content for the home page
        content = f"""
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-6">Car Listings</h1>
            
            <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {car_html if cars else '<p class="col-span-full text-center text-gray-500">No cars found in the database.</p>'}
            </div>
        </div>
        """
        
        return HTMLResponse(get_page_html("Car Listings", content))
    except Exception as e:
        logger.error(f"Error rendering home page: {str(e)}")
        content = """
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-6">Car Listings</h1>
            <div class="bg-white p-6 rounded-lg shadow-md">
                <p class="text-red-500">Error loading car listings. Please try again later.</p>
            </div>
        </div>
        """
        return HTMLResponse(get_page_html("Car Listings", content))

@app.get("/car/{car_id}", response_class=HTMLResponse)
async def car_detail_view(request: Request, car_id: str):
    """Car detail view"""
    try:
        # Get the car from the database
        from bson import ObjectId
        car = await collection.find_one({"_id": ObjectId(car_id)})
        
        if not car:
            content = """
            <div class="container mx-auto px-4 py-8">
                <h1 class="text-3xl font-bold mb-6">Car Not Found</h1>
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <p>The car you're looking for doesn't exist or has been removed.</p>
                    <a href="/" class="mt-4 inline-block text-blue-600 hover:text-blue-800">Back to Listings</a>
                </div>
            </div>
            """
            return HTMLResponse(get_page_html("Car Not Found", content))
        
        # Format the car details
        brand = car.get("brand", "Unknown")
        model = car.get("model", "")
        year = car.get("year", "")
        price = format_currency(car.get("cash_price", 0))
        mileage = format_number(car.get("mileage", 0), " km")
        source_url = car.get("source_url", "")
        
        # Create the content for the car detail page
        content = f"""
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-6">{brand} {model} ({year})</h1>
            
            <div class="bg-white p-6 rounded-lg shadow-md">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h2 class="text-xl font-semibold mb-4">Car Details</h2>
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span class="text-gray-600">Brand:</span>
                                <span class="font-medium">{brand}</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-gray-600">Model:</span>
                                <span class="font-medium">{model}</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-gray-600">Year:</span>
                                <span class="font-medium">{year}</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-gray-600">Mileage:</span>
                                <span class="font-medium">{mileage}</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-gray-600">Price:</span>
                                <span class="font-bold text-green-600">{price}</span>
                            </div>
                        </div>
                        
                        {f'<div class="mt-6"><a href="{source_url}" target="_blank" class="text-blue-600 hover:text-blue-800">View Original Listing</a></div>' if source_url else ''}
                    </div>
                    
                    <div>
                        <h2 class="text-xl font-semibold mb-4">Additional Information</h2>
                        <p class="text-gray-600">This car was added to our database on {car.get('created_at', datetime.now()).strftime('%Y-%m-%d')}.</p>
                    </div>
                </div>
            </div>
            
            <div class="mt-6">
                <a href="/" class="text-blue-600 hover:text-blue-800">Back to Listings</a>
            </div>
        </div>
        """
        
        return HTMLResponse(get_page_html(f"{brand} {model}", content))
    except Exception as e:
        logger.error(f"Error rendering car detail: {str(e)}")
        content = """
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-6">Error</h1>
            <div class="bg-white p-6 rounded-lg shadow-md">
                <p class="text-red-500">Error loading car details. Please try again later.</p>
                <a href="/" class="mt-4 inline-block text-blue-600 hover:text-blue-800">Back to Listings</a>
            </div>
        </div>
        """
        return HTMLResponse(get_page_html("Error", content))

@app.get("/admin", response_class=HTMLResponse)
async def admin_view(request: Request):
    """Admin view for database management"""
    content = """
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-6">Admin Dashboard</h1>
        
        <!-- Database Stats Card -->
        <div class="bg-white p-6 rounded-lg shadow-md mb-8">
            <h2 class="text-xl font-semibold mb-4">Database Statistics</h2>
            <div id="stats-loading" class="p-4 bg-gray-50 rounded-lg">
                <p class="text-center text-gray-500">Loading statistics...</p>
            </div>
            <div id="stats-container" class="hidden">
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
        </div>
        
        <!-- Database Actions Card -->
        <div class="bg-white p-6 rounded-lg shadow-md mb-8">
            <h2 class="text-xl font-semibold mb-4">Database Actions</h2>
            
            <div class="space-y-6">
                <!-- Remove Invalid URLs -->
                <div>
                    <h3 class="font-medium mb-2">Remove Cars with Invalid URLs</h3>
                    <p class="text-gray-600 mb-4">This will permanently delete all cars marked with invalid source URLs.</p>
                    
                    <div class="flex items-center mb-2">
                        <input type="checkbox" id="confirmRemove" class="mr-2">
                        <label for="confirmRemove" class="text-sm text-gray-700">I understand this action cannot be undone</label>
                    </div>
                    
                    <button id="removeInvalidBtn" disabled class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed">
                        Remove Invalid URLs
                    </button>
                    <span id="removeStatus" class="ml-2 text-sm"></span>
                </div>
                
                <!-- Test MongoDB Connection -->
                <div>
                    <h3 class="font-medium mb-2">Test MongoDB Connection</h3>
                    <p class="text-gray-600 mb-4">Test the connection to MongoDB Atlas.</p>
                    
                    <button id="testMongoBtn" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Test MongoDB Connection
                    </button>
                    <span id="testMongoStatus" class="ml-2 text-sm"></span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', async function() {
            // Elements
            const statsLoading = document.getElementById('stats-loading');
            const statsContainer = document.getElementById('stats-container');
            const confirmRemoveEl = document.getElementById('confirmRemove');
            const removeInvalidBtn = document.getElementById('removeInvalidBtn');
            const removeStatus = document.getElementById('removeStatus');
            const testMongoBtn = document.getElementById('testMongoBtn');
            const testMongoStatus = document.getElementById('testMongoStatus');
            
            // Load stats
            async function loadStats() {
                try {
                    const response = await fetch('/api/stats');
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    // Update the stats
                    document.getElementById('total-cars').textContent = data.total_cars.toLocaleString();
                    document.getElementById('cars-with-url').textContent = data.cars_with_url.toLocaleString();
                    document.getElementById('cars-without-url').textContent = data.cars_without_url.toLocaleString();
                    
                    // Show the stats container
                    statsLoading.classList.add('hidden');
                    statsContainer.classList.remove('hidden');
                } catch (error) {
                    console.error('Error loading stats:', error);
                    statsLoading.innerHTML = `<p class="text-center text-red-500">Error loading statistics: ${error.message}</p>`;
                }
            }
            
            // Load stats on page load
            loadStats();
            
            // Handle confirm checkbox
            confirmRemoveEl.addEventListener('change', function() {
                removeInvalidBtn.disabled = !this.checked;
            });
            
            // Handle remove invalid URLs button
            removeInvalidBtn.addEventListener('click', async function() {
                try {
                    removeInvalidBtn.disabled = true;
                    removeInvalidBtn.innerHTML = 'Removing...';
                    removeStatus.className = 'ml-2 text-sm text-blue-600';
                    removeStatus.textContent = 'Removing invalid URLs...';
                    
                    const response = await fetch('/api/admin/remove-invalid-urls', {
                        method: 'POST'
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    removeStatus.className = 'ml-2 text-sm text-green-600';
                    removeStatus.textContent = data.message;
                    
                    // Update stats
                    loadStats();
                } catch (error) {
                    console.error('Error removing invalid URLs:', error);
                    removeStatus.className = 'ml-2 text-sm text-red-600';
                    removeStatus.textContent = `Error: ${error.message}`;
                } finally {
                    removeInvalidBtn.disabled = false;
                    removeInvalidBtn.innerHTML = 'Remove Invalid URLs';
                }
            });
            
            // Test MongoDB connection
            if (testMongoBtn) {
                testMongoBtn.addEventListener('click', async function() {
                    try {
                        testMongoBtn.disabled = true;
                        testMongoBtn.innerHTML = 'Testing...';
                        testMongoStatus.className = 'ml-2 text-sm text-blue-600';
                        testMongoStatus.textContent = 'Testing connection...';
                        
                        const response = await fetch('/api/test-mongodb');
                        const data = await response.json();
                        
                        if (data.success) {
                            testMongoStatus.className = 'ml-2 text-sm text-green-600';
                            testMongoStatus.textContent = `Success! ${data.message}. Total documents: ${data.total_documents}`;
                        } else {
                            testMongoStatus.className = 'ml-2 text-sm text-red-600';
                            testMongoStatus.textContent = `Error: ${data.message}`;
                        }
                    } catch (error) {
                        console.error('Error testing MongoDB connection:', error);
                        testMongoStatus.className = 'ml-2 text-sm text-red-600';
                        testMongoStatus.textContent = `Error: ${error.message}`;
                    } finally {
                        testMongoBtn.disabled = false;
                        testMongoBtn.innerHTML = 'Test MongoDB Connection';
                    }
                });
            }
        });
    </script>
    """
    
    return HTMLResponse(get_page_html("Admin Dashboard", content))

@app.get("/stats", response_class=HTMLResponse)
async def stats_view(request: Request):
    """Stats view for database statistics"""
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
                
                <div class="mt-6 p-4 bg-gray-50 rounded-lg">
                    <h2 class="text-lg font-semibold text-gray-800 mb-2">Currency Service Status</h2>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="flex justify-between">
                            <span class="text-gray-600">Status:</span>
                            <span id="currency-status" class="font-medium">-</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Last Updated:</span>
                            <span id="currency-last-updated" class="font-medium">-</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Using Fallback:</span>
                            <span id="currency-fallback" class="font-medium">-</span>
                        </div>
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
            document.addEventListener('DOMContentLoaded', async function() {
                const loadingEl = document.getElementById('loading');
                const statsContainer = document.getElementById('stats-container');
                const errorContainer = document.getElementById('error-container');
                const errorMessage = document.getElementById('error-message');
                const tryTestApiBtn = document.getElementById('try-test-api');
                
                async function loadStats() {
                    try {
                        const response = await fetch('/api/stats');
                        
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        
                        const data = await response.json();
                        
                        // Update the stats
                        document.getElementById('total-cars').textContent = data.total_cars.toLocaleString();
                        document.getElementById('cars-with-url').textContent = data.cars_with_url.toLocaleString();
                        document.getElementById('cars-without-url').textContent = data.cars_without_url.toLocaleString();
                        
                        // Update currency service status
                        document.getElementById('currency-status').textContent = data.currency_status.status;
                        document.getElementById('currency-last-updated').textContent = data.currency_status.last_updated || 'Never';
                        document.getElementById('currency-fallback').textContent = data.currency_status.using_fallback ? 'Yes' : 'No';
                        
                        // Show the stats container
                        loadingEl.classList.add('hidden');
                        statsContainer.classList.remove('hidden');
                    } catch (error) {
                        console.error('Error loading stats:', error);
                        errorMessage.textContent = `Error loading statistics: ${error.message}`;
                        loadingEl.classList.add('hidden');
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
                        
                        // Update currency service status
                        document.getElementById('currency-status').textContent = data.currency_status.status;
                        document.getElementById('currency-last-updated').textContent = data.currency_status.last_updated || 'Never';
                        document.getElementById('currency-fallback').textContent = data.currency_status.using_fallback ? 'Yes' : 'No';
                        
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

@app.get("/scrape", response_class=HTMLResponse)
async def scrape_view(request: Request):
    """Enhanced scraper view with multiple scraper options"""
    content = """
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-6">Car Scraper</h1>
        
        <div class="bg-white p-6 rounded-lg shadow-md mb-8">
            <h2 class="text-xl font-semibold mb-4">Run Scraper</h2>
            <form id="scraper-form" class="space-y-4">
                <div>
                    <label for="scraper-type" class="block text-sm font-medium text-gray-700">Scraper Type</label>
                    <select id="scraper-type" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
                        <option value="simple">Simple Scraper</option>
                        <option value="real">Real Scraper</option>
                        <option value="large">Large Scale Scraper</option>
                        <option value="default">Default Scraper</option>
                    </select>
                    <p class="mt-1 text-sm text-gray-500">Select which scraper implementation to use</p>
                </div>
                
                <div>
                    <label for="country" class="block text-sm font-medium text-gray-700">Country</label>
                    <select id="country" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
                        <option value="denmark">Denmark</option>
                        <option value="sweden">Sweden</option>
                        <option value="norway">Norway</option>
                        <option value="germany">Germany</option>
                        <option value="portugal">Portugal</option>
                        <option value="poland">Poland</option>
                        <option value="france">France</option>
                        <option value="italy">Italy</option>
                    </select>
                </div>
                
                <div>
                    <label for="max-cars" class="block text-sm font-medium text-gray-700">Maximum Cars to Scrape</label>
                    <input type="number" id="max-cars" value="10" min="1" max="1000" 
                           class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                    <p class="mt-1 text-sm text-gray-500">Limit the number of cars to scrape (lower is faster)</p>
                </div>
                
                <div>
                    <button type="submit" id="run-btn" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        Run Scraper
                    </button>
                </div>
            </form>
            
            <div id="status" class="mt-4 p-4 rounded-lg bg-gray-50 hidden">
                <p id="status-message" class="text-sm"></p>
            </div>
        </div>
        
        <!-- Custom URL Scraper -->
        <div class="bg-white p-6 rounded-lg shadow-md">
            <h2 class="text-xl font-semibold mb-4">Custom URL Scraper</h2>
            <form id="custom-scraper-form" class="space-y-4">
                <div>
                    <label for="custom-urls" class="block text-sm font-medium text-gray-700">URLs to Scrape (one per line)</label>
                    <textarea id="custom-urls" rows="5" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"></textarea>
                    <p class="mt-1 text-sm text-gray-500">Enter specific URLs to scrape</p>
                </div>
                
                <div>
                    <label for="custom-scraper-type" class="block text-sm font-medium text-gray-700">Scraper Type</label>
                    <select id="custom-scraper-type" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
                        <option value="simple">Simple Scraper</option>
                        <option value="real">Real Scraper</option>
                    </select>
                </div>
                
                <div>
                    <label for="custom-max-cars" class="block text-sm font-medium text-gray-700">Maximum Cars to Scrape</label>
                    <input type="number" id="custom-max-cars" value="5" min="1" max="100" 
                           class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                </div>
                
                <div>
                    <button type="submit" id="custom-run-btn" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        Run Custom Scraper
                    </button>
                </div>
            </form>
            
            <div id="custom-status" class="mt-4 p-4 rounded-lg bg-gray-50 hidden">
                <p id="custom-status-message" class="text-sm"></p>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Regular scraper form
            const scraperForm = document.getElementById('scraper-form');
            const scraperType = document.getElementById('scraper-type');
            const country = document.getElementById('country');
            const maxCars = document.getElementById('max-cars');
            const runBtn = document.getElementById('run-btn');
            const status = document.getElementById('status');
            const statusMessage = document.getElementById('status-message');
            
            // Custom scraper form
            const customScraperForm = document.getElementById('custom-scraper-form');
            const customUrls = document.getElementById('custom-urls');
            const customScraperType = document.getElementById('custom-scraper-type');
            const customMaxCars = document.getElementById('custom-max-cars');
            const customRunBtn = document.getElementById('custom-run-btn');
            const customStatus = document.getElementById('custom-status');
            const customStatusMessage = document.getElementById('custom-status-message');
            
            // Handle regular scraper form submission
            scraperForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const selectedType = scraperType.value;
                const selectedCountry = country.value;
                const maxCarsValue = parseInt(maxCars.value);
                
                runBtn.disabled = true;
                runBtn.innerHTML = '<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Running...';
                
                fetch('/api/admin/run-scraper', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        type: selectedType,
                        country: selectedCountry,
                        max_cars: maxCarsValue
                    }),
                })
                .then(response => response.json())
                .then(data => {
                    status.classList.remove('hidden');
                    status.classList.add('bg-blue-50');
                    statusMessage.textContent = data.message;
                    
                    setTimeout(() => {
                        runBtn.disabled = false;
                        runBtn.innerHTML = 'Run Scraper';
                    }, 3000);
                })
                .catch(error => {
                    status.classList.remove('hidden');
                    status.classList.add('bg-red-50');
                    statusMessage.textContent = 'Error: ' + error;
                    runBtn.disabled = false;
                    runBtn.innerHTML = 'Run Scraper';
                });
            });
            
            // Handle custom scraper form submission
            customScraperForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                // Parse URLs (one per line)
                const urlsText = customUrls.value.trim();
                if (!urlsText) {
                    customStatus.classList.remove('hidden');
                    customStatus.classList.add('bg-red-50');
                    customStatusMessage.textContent = 'Please enter at least one URL';
                    return;
                }
                
                const urls = urlsText.split('\\n')
                    .map(url => url.trim())
                    .filter(url => url.length > 0);
                
                if (urls.length === 0) {
                    customStatus.classList.remove('hidden');
                    customStatus.classList.add('bg-red-50');
                    customStatusMessage.textContent = 'Please enter at least one valid URL';
                    return;
                }
                
                const selectedType = customScraperType.value;
                const maxCarsValue = parseInt(customMaxCars.value);
                
                customRunBtn.disabled = true;
                customRunBtn.innerHTML = '<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Running...';
                
                fetch('/api/admin/scrape-cars', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        urls: urls,
                        max_cars: maxCarsValue,
                        type: selectedType
                    }),
                })
                .then(response => response.json())
                .then(data => {
                    customStatus.classList.remove('hidden');
                    customStatus.classList.add('bg-blue-50');
                    customStatusMessage.textContent = data.message;
                    
                    setTimeout(() => {
                        customRunBtn.disabled = false;
                        customRunBtn.innerHTML = 'Run Custom Scraper';
                    }, 3000);
                })
                .catch(error => {
                    customStatus.classList.remove('hidden');
                    customStatus.classList.add('bg-red-50');
                    customStatusMessage.textContent = 'Error: ' + error;
                    customRunBtn.disabled = false;
                    customRunBtn.innerHTML = 'Run Custom Scraper';
                });
            });
        });
    </script>
    """
    
    return HTMLResponse(get_page_html("Car Scraper", content))

@app.get("/opportunities", response_class=HTMLResponse)
async def opportunities_view(request: Request):
    """View for car buying opportunities"""
    logger.info("Accessing opportunities page")
    try:
        return templates.TemplateResponse("opportunities.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering opportunities template: {str(e)}")
        # Fallback to inline HTML
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Car Buying Opportunities | CarAgentApp</title>
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        </head>
        <body class="bg-gray-100">
            <nav class="bg-gray-800 text-white p-4">
                <div class="container mx-auto flex justify-between items-center">
                    <a href="/" class="text-xl font-bold">CarAgentApp</a>
                    <div class="space-x-4">
                        <a href="/" class="hover:text-gray-300">Home</a>
                        <a href="/opportunities" class="hover:text-gray-300">Opportunities</a>
                        <a href="/scraper" class="hover:text-gray-300">Scraper</a>
                        <a href="/admin" class="hover:text-gray-300">Admin</a>
                        <a href="/currency-test" class="hover:text-gray-300">Currency Test</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mx-auto px-4 py-8">
                <h1 class="text-3xl font-bold mb-6">Car Buying Opportunities</h1>
                
                <div class="bg-white p-6 rounded-lg shadow-md mb-8">
                    <h2 class="text-xl font-semibold mb-4">Find Underpriced Cars</h2>
                    
                    <div id="opportunities-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        <div class="p-4 border rounded-lg bg-gray-50">
                            <p class="text-center text-gray-500">Loading opportunities...</p>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <h2 class="text-xl font-semibold mb-4">Opportunity Settings</h2>
                    
                    <form id="opportunity-settings-form" class="space-y-4">
                        <div>
                            <label for="min-price-diff" class="block text-sm font-medium text-gray-700">Minimum Price Difference (%)</label>
                            <input type="number" id="min-price-diff" name="min-price-diff" value="15" min="5" max="50" 
                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                            <p class="mt-1 text-sm text-gray-500">Cars must be at least this percentage below market value</p>
                        </div>
                        
                        <div>
                            <label for="max-age" class="block text-sm font-medium text-gray-700">Maximum Car Age (years)</label>
                            <input type="number" id="max-age" name="max-age" value="10" min="1" max="30" 
                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                            <p class="mt-1 text-sm text-gray-500">Only show cars newer than this many years</p>
                        </div>
                        
                        <div>
                            <label for="min-listings" class="block text-sm font-medium text-gray-700">Minimum Comparable Listings</label>
                            <input type="number" id="min-listings" name="min-listings" value="3" min="1" max="20" 
                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                            <p class="mt-1 text-sm text-gray-500">Require at least this many comparable listings for market value calculation</p>
                        </div>
                        
                        <div>
                            <button type="submit" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                                Update Settings
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            
            <script>
                document.addEventListener('DOMContentLoaded', async function() {
                    const opportunitiesContainer = document.getElementById('opportunities-container');
                    const settingsForm = document.getElementById('opportunity-settings-form');
                    
                    // Function to load opportunities
                    async function loadOpportunities() {
                        try {
                            opportunitiesContainer.innerHTML = '<div class="p-4 border rounded-lg bg-gray-50 col-span-full"><p class="text-center text-gray-500">Loading opportunities...</p></div>';
                            
                            // Get settings values
                            const minPriceDiff = document.getElementById('min-price-diff').value;
                            const maxAge = document.getElementById('max-age').value;
                            const minListings = document.getElementById('min-listings').value;
                            
                            // Call the API to get opportunities
                            const response = await fetch(`/api/opportunities?min_price_diff=${minPriceDiff}&max_age=${maxAge}&min_listings=${minListings}`);
                            
                            if (!response.ok) {
                                throw new Error(`HTTP error! status: ${response.status}`);
                            }
                            
                            const data = await response.json();
                            
                            if (data.length === 0) {
                                opportunitiesContainer.innerHTML = '<div class="p-4 border rounded-lg bg-gray-50 col-span-full"><p class="text-center text-gray-500">No opportunities found. Try adjusting your settings.</p></div>';
                                return;
                            }
                            
                            // Render the opportunities
                            opportunitiesContainer.innerHTML = data.map(opportunity => `
                                <div class="bg-white border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                                    <div class="p-4">
                                        <h3 class="text-lg font-semibold">${opportunity.brand} ${opportunity.model} (${opportunity.year})</h3>
                                        <div class="mt-2 flex justify-between">
                                            <span class="text-gray-600">${opportunity.mileage}</span>
                                            <span class="font-bold text-green-600">${opportunity.price}</span>
                                        </div>
                                        <div class="mt-2">
                                            <span class="text-sm text-gray-500">Market value: ${opportunity.market_value}</span>
                                            <div class="mt-1 flex items-center">
                                                <span class="text-sm font-medium text-green-600">${opportunity.discount_percentage}% below market</span>
                                                <span class="ml-2 text-sm text-gray-500">(${opportunity.discount_amount} savings)</span>
                                            </div>
                                        </div>
                                        <div class="mt-3">
                                            <a href="/car/${opportunity.id}" class="text-blue-600 hover:text-blue-800 text-sm font-medium">View Details</a>
                                            <a href="${opportunity.source_url}" target="_blank" class="ml-4 text-blue-600 hover:text-blue-800 text-sm font-medium">View Listing</a>
                                        </div>
                                    </div>
                                </div>
                            `).join('');
                            
                        } catch (error) {
                            console.error('Error loading opportunities:', error);
                            opportunitiesContainer.innerHTML = `<div class="p-4 border rounded-lg bg-red-50 col-span-full"><p class="text-center text-red-500">Error loading opportunities: ${error.message}</p></div>`;
                        }
                    }
                    
                    // Load opportunities on page load
                    loadOpportunities();
                    
                    // Handle settings form submission
                    settingsForm.addEventListener('submit', function(event) {
                        event.preventDefault();
                        loadOpportunities();
                    });
                });
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)

@app.get("/scraper", response_class=HTMLResponse)
async def scraper_view(request: Request):
    """View for scraper management"""
    logger.info("Accessing scraper page")
    try:
        return templates.TemplateResponse("scraper.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering scraper template: {str(e)}")
        # Fallback to inline HTML
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Car Scraper | CarAgentApp</title>
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        </head>
        <body class="bg-gray-100">
            <nav class="bg-gray-800 text-white p-4">
                <div class="container mx-auto flex justify-between items-center">
                    <a href="/" class="text-xl font-bold">CarAgentApp</a>
                    <div class="space-x-4">
                        <a href="/" class="hover:text-gray-300">Home</a>
                        <a href="/opportunities" class="hover:text-gray-300">Opportunities</a>
                        <a href="/scraper" class="hover:text-gray-300">Scraper</a>
                        <a href="/admin" class="hover:text-gray-300">Admin</a>
                        <a href="/currency-test" class="hover:text-gray-300">Currency Test</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mx-auto px-4 py-8">
                <h1 class="text-3xl font-bold mb-6">Car Scraper</h1>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    <!-- Scraper Stats Card -->
                    <div class="bg-white p-6 rounded-lg shadow-md">
                        <h2 class="text-xl font-semibold mb-4">Scraper Statistics</h2>
                        <div id="scraperStats" class="space-y-2">
                            <div class="flex justify-between">
                                <span>Total Cars:</span>
                                <span id="totalCars" class="font-bold">Loading...</span>
                            </div>
                            <div class="flex justify-between">
                                <span>Cars with Source URLs:</span>
                                <span id="carsWithUrl" class="font-bold">Loading...</span>
                            </div>
                            <div class="flex justify-between">
                                <span>Cars without Source URLs:</span>
                                <span id="carsWithoutUrl" class="font-bold">Loading...</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Run Scraper Card -->
                    <div class="bg-white p-6 rounded-lg shadow-md">
                        <h2 class="text-xl font-semibold mb-4">Run Scraper</h2>
                        <form id="scraper-form" class="space-y-4">
                            <div>
                                <label for="scraper-type" class="block text-sm font-medium text-gray-700">Scraper Type</label>
                                <select id="scraper-type" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
                                    <option value="simple">Simple Scraper</option>
                                    <option value="real">Real Scraper</option>
                                    <option value="large">Large Scale Scraper</option>
                                    <option value="default">Default Scraper</option>
                                </select>
                            </div>
                            
                            <div>
                                <label for="country" class="block text-sm font-medium text-gray-700">Country</label>
                                <select id="country" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
                                    <option value="denmark">Denmark</option>
                                    <option value="sweden">Sweden</option>
                                    <option value="norway">Norway</option>
                                    <option value="germany">Germany</option>
                                    <option value="portugal">Portugal</option>
                                    <option value="poland">Poland</option>
                                    <option value="france">France</option>
                                    <option value="italy">Italy</option>
                                </select>
                            </div>
                            
                            <div>
                                <label for="max-cars" class="block text-sm font-medium text-gray-700">Maximum Cars to Scrape</label>
                                <input type="number" id="max-cars" value="10" min="1" max="1000" 
                                       class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                            </div>
                            
                            <div>
                                <button type="submit" id="run-scraper-btn" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                                    Run Scraper
                                </button>
                            </div>
                        </form>
                        
                        <div id="scraper-status" class="mt-4 p-4 rounded-lg bg-gray-50 hidden">
                            <p id="scraper-status-message" class="text-sm"></p>
                        </div>
                    </div>
                </div>
                
                <!-- Custom Scraper Card -->
                <div class="bg-white p-6 rounded-lg shadow-md mb-8">
                    <h2 class="text-xl font-semibold mb-4">Custom Scraper</h2>
                    
                    <form id="custom-scraper-form" class="space-y-4">
                        <div>
                            <label for="listing-urls" class="block text-sm font-medium text-gray-700">Listing URLs (one per line)</label>
                            <textarea id="listing-urls" rows="5" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"></textarea>
                        </div>
                        
                        <div>
                            <label for="max-cars" class="block text-sm font-medium text-gray-700">Maximum Cars to Scrape</label>
                            <input type="number" id="max-cars" value="100" min="1" max="1000" 
                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                        </div>
                        
                        <div>
                            <button type="submit" id="custom-scraper-btn" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                                Start Custom Scraper
                            </button>
                        </div>
                    </form>
                    
                    <div id="custom-scraper-status" class="mt-4 p-4 rounded-lg bg-gray-50 hidden">
                        <p id="custom-scraper-status-message" class="text-sm"></p>
                    </div>
                </div>
            </div>
            
            <script>
                document.addEventListener('DOMContentLoaded', async function() {
                    // Get elements
                    const scraperForm = document.getElementById('scraper-form');
                    const scraperType = document.getElementById('scraper-type');
                    const scraperCountry = document.getElementById('country');
                    const runScraperBtn = document.getElementById('run-scraper-btn');
                    const scraperStatus = document.getElementById('scraper-status');
                    const scraperStatusMessage = document.getElementById('scraper-status-message');
                    
                    const customScraperForm = document.getElementById('custom-scraper-form');
                    const listingUrls = document.getElementById('listing-urls');
                    const maxCars = document.getElementById('max-cars');
                    const customScraperBtn = document.getElementById('custom-scraper-btn');
                    const customScraperStatus = document.getElementById('custom-scraper-status');
                    const customScraperStatusMessage = document.getElementById('custom-scraper-status-message');
                    
                    // Load stats
                    async function loadStats() {
                        try {
                            const response = await fetch('/api/admin/stats');
                            if (!response.ok) {
                                throw new Error(`HTTP error! status: ${response.status}`);
                            }
                            
                            const data = await response.json();
                            
                            document.getElementById('totalCars').textContent = data.total_cars.toLocaleString();
                            document.getElementById('carsWithUrl').textContent = data.cars_with_url.toLocaleString();
                            document.getElementById('carsWithoutUrl').textContent = data.cars_without_url.toLocaleString();
                        } catch (error) {
                            console.error('Error loading stats:', error);
                            document.getElementById('totalCars').textContent = 'Error';
                            document.getElementById('carsWithUrl').textContent = 'Error';
                            document.getElementById('carsWithoutUrl').textContent = 'Error';
                        }
                    }
                    
                    // Load stats on page load
                    loadStats();
                    
                    // Handle scraper form submission
                    scraperForm.addEventListener('submit', function(event) {
                        event.preventDefault();
                        
                        // Disable the button to prevent multiple submissions
                        runScraperBtn.disabled = true;
                        runScraperBtn.innerHTML = '<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Running...';
                        
                        // Get the selected values
                        const type = scraperType.value;
                        const country = scraperCountry.value;
                        
                        // Call the API to run the scraper
                        fetch('/api/admin/run-scraper', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                type: type,
                                country: country
                            }),
                        })
                        .then(response => response.json())
                        .then(data => {
                            // Show the status message
                            scraperStatus.classList.remove('hidden');
                            scraperStatus.classList.add('bg-blue-50');
                            scraperStatusMessage.textContent = data.message;
                            
                            // Re-enable the button after a delay
                            setTimeout(() => {
                                runScraperBtn.disabled = false;
                                runScraperBtn.innerHTML = 'Run Scraper';
                                
                                // Update stats after a delay to reflect new data
                                setTimeout(loadStats, 5000);
                            }, 3000);
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            scraperStatus.classList.remove('hidden');
                            scraperStatus.classList.add('bg-red-50');
                            scraperStatusMessage.textContent = 'Error starting scraper: ' + error;
                            runScraperBtn.disabled = false;
                            runScraperBtn.innerHTML = 'Run Scraper';
                        });
                    });
                    
                    // Handle custom scraper form submission
                    customScraperForm.addEventListener('submit', function(event) {
                        event.preventDefault();
                        
                        // Validate inputs
                        const urlsText = listingUrls.value.trim();
                        if (!urlsText) {
                            customScraperStatus.classList.remove('hidden');
                            customScraperStatus.classList.add('bg-red-50');
                            customScraperStatusMessage.textContent = 'Please enter at least one URL';
                            return;
                        }
                        
                        // Parse URLs (one per line)
                        const urls = urlsText.split('\\n')
                            .map(url => url.trim())
                            .filter(url => url.length > 0);
                        
                        if (urls.length === 0) {
                            customScraperStatus.classList.remove('hidden');
                            customScraperStatus.classList.add('bg-red-50');
                            customScraperStatusMessage.textContent = 'Please enter at least one valid URL';
                            return;
                        }
                        
                        // Get max cars
                        const maxCarsValue = parseInt(maxCars.value);
                        if (isNaN(maxCarsValue) || maxCarsValue < 1) {
                            customScraperStatus.classList.remove('hidden');
                            customScraperStatus.classList.add('bg-red-50');
                            customScraperStatusMessage.textContent = 'Please enter a valid number for maximum cars';
                            return;
                        }
                        
                        // Disable the button to prevent multiple submissions
                        customScraperBtn.disabled = true;
                        customScraperBtn.innerHTML = '<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Scraping...';
                        
                        // Call the API to run the custom scraper
                        fetch('/api/admin/scrape-cars', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                urls: urls,
                                max_cars: maxCarsValue
                            }),
                        })
                        .then(response => response.json())
                        .then(data => {
                            // Show the status message
                            customScraperStatus.classList.remove('hidden');
                            customScraperStatus.classList.add('bg-blue-50');
                            customScraperStatusMessage.textContent = data.message;
                            
                            // Re-enable the button after a delay
                            setTimeout(() => {
                                customScraperBtn.disabled = false;
                                customScraperBtn.innerHTML = 'Start Custom Scraper';
                                
                                // Update stats after a delay to reflect new data
                                setTimeout(loadStats, 5000);
                            }, 3000);
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            customScraperStatus.classList.remove('hidden');
                            customScraperStatus.classList.add('bg-red-50');
                            customScraperStatusMessage.textContent = 'Error starting custom scraper: ' + error;
                            customScraperBtn.disabled = false;
                            customScraperBtn.innerHTML = 'Start Custom Scraper';
                        });
                    });
                });
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)

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
            "source_url": {"$exists": True, "$ne": ""},
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

@app.post("/api/admin/run-scraper")
async def run_scraper(request: Request):
    """Run a scraper for a specific country"""
    try:
        # Get parameters from request
        data = await request.json()
        scraper_type = data.get("type", "simple")
        country = data.get("country", "denmark")
        max_cars = data.get("max_cars", 10)
        
        logger.info(f"Running {scraper_type} scraper for {country} with max_cars={max_cars}")
        
        # This is more reliable in a serverless environment
        
        # Get URLs for the country
        if country not in URLS:
            return JSONResponse({
                "success": False,
                "message": f"Country '{country}' not found in configuration"
            })
        
        urls = URLS[country]
        
        # Run a lightweight version of the scraper directly
        # This avoids issues with subprocess in serverless environments
        async def run_scraper_task():
            try:
                from src.db import MongoDB
                
                # Initialize the database
                db = MongoDB()
                await db.init_db()
                
                # Log the start
                logger.info(f"Starting {scraper_type} scraper for {country} with URLs: {urls}")
                
                # Scrape the first URL as a test
                if urls:
                    # Import the appropriate scraper based on type
                    if scraper_type == "simple":
                        from src.simple_scraper import SimpleScraper
                        scraper = SimpleScraper()
                    elif scraper_type == "real":
                        from src.real_scraper import RealScraper
                        scraper = RealScraper()
                    elif scraper_type == "large":
                        from src.large_scraper import LargeScraper
                        scraper = LargeScraper()
                    else:
                        # Default to simple scraper
                        from src.simple_scraper import SimpleScraper
                        scraper = SimpleScraper()
                    
                    # Run the scraper with the URLs
                    # Limit to just a few URLs for testing in serverless environment
                    test_urls = urls[:1] if isinstance(urls, list) else [urls]
                    await scraper.scrape_urls(test_urls, country, max_cars=max_cars)
                    
                    logger.info(f"Scraper completed for {country}")
            except Exception as e:
                logger.error(f"Error in scraper task: {str(e)}")
        
        # Start the task in the background
        asyncio.create_task(run_scraper_task())
        
        # Return immediately with a success message
        return JSONResponse({
            "success": True,
            "message": f"Started {scraper_type} scraper for {country} with max_cars={max_cars}"
        })
        
    except Exception as e:
        logger.error(f"Error starting scraper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test-mongodb")
async def test_mongodb_connection():
    """Test the MongoDB Atlas connection"""
    try:
        # Test basic connection
        logger.info(f"Testing MongoDB connection to {MONGODB_URI}")
        
        # Count documents
        count = await collection.count_documents({})
        
        # Get a sample document
        sample = await collection.find_one({})
        
        # Create a test document
        test_doc = {
            "test": True,
            "timestamp": datetime.utcnow(),
            "message": "This is a test document from Vercel"
        }
        
        # Insert the test document
        result = await collection.insert_one(test_doc)
        
        # Delete the test document
        await collection.delete_one({"_id": result.inserted_id})
        
        return {
            "success": True,
            "message": "MongoDB Atlas connection successful",
            "total_documents": count,
            "sample_document": str(sample["_id"]) if sample else None,
            "test_document_id": str(result.inserted_id)
        }
    except Exception as e:
        logger.error(f"MongoDB connection test failed: {str(e)}")
        return {
            "success": False,
            "message": f"MongoDB connection test failed: {str(e)}",
            "error": str(e)
        }

@app.get("/api/opportunities")
async def get_opportunities(
    min_price_diff: int = 15,
    max_age: int = 10,
    min_listings: int = 3
):
    """Get car buying opportunities"""
    try:
        logger.info(f"Getting opportunities with min_price_diff={min_price_diff}, max_age={max_age}, min_listings={min_listings}")
        
        # For debugging, return a simple response first
        return [
            {
                "id": "test123",
                "brand": "Test Brand",
                "model": "Test Model",
                "year": 2020,
                "mileage": "50,000 km",
                "price": "200,000 DKK",
                "price_sek": "300,000 SEK",
                "market_value": "250,000 DKK",
                "market_value_sek": "375,000 SEK",
                "discount_percentage": 20.0,
                "discount_amount": "50,000 DKK",
                "source_url": "https://example.com"
            }
        ]
        
        # Original implementation below...
        
    except Exception as e:
        logger.error(f"Error getting opportunities: {str(e)}")
        return {"error": str(e)}

@app.post("/api/admin/scrape-cars")
async def scrape_cars(request: Request):
    """Scrape cars from specified URLs"""
    try:
        # Get parameters from request
        data = await request.json()
        urls = data.get("urls", [])
        max_cars = data.get("max_cars", 5)
        scraper_type = data.get("type", "simple")
        
        if not urls:
            return {"message": "No URLs provided", "success": False}
        
        logger.info(f"Running custom {scraper_type} scraper for {len(urls)} URLs with max_cars={max_cars}")
        
        # Start a background task to scrape the URLs
        async def scrape_task():
            try:
                # Import the appropriate scraper based on type
                if scraper_type == "simple":
                    from src.simple_scraper import SimpleScraper
                    scraper = SimpleScraper()
                elif scraper_type == "real":
                    from src.real_scraper import RealScraper
                    scraper = RealScraper()
                else:
                    # Default to simple scraper
                    from src.simple_scraper import SimpleScraper
                    scraper = SimpleScraper()
                
                await scraper.scrape_urls(urls, "custom", max_cars=max_cars)
                
                logger.info(f"Custom {scraper_type} scraper completed for {len(urls)} URLs")
            except Exception as e:
                logger.error(f"Error in custom scraper task: {str(e)}")
        
        # Start the task in the background
        asyncio.create_task(scrape_task())
        
        return {
            "message": f"Started {scraper_type} scraper for {len(urls)} URLs (max {max_cars} cars)",
            "success": True
        }
    except Exception as e:
        logger.error(f"Error starting custom scraper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test")
async def test_api():
    """Test API endpoint"""
    return {"message": "API is working"}

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        # Get stats from database
        total_cars = await collection.count_documents({})
        cars_with_url = await collection.count_documents({"source_url": {"$exists": True, "$ne": ""}})
        cars_without_url = total_cars - cars_with_url
        
        # Get currency service status
        currency_service = await get_currency_service()
        currency_status = {
            "status": "Active" if currency_service.is_active() else "Inactive",
            "last_updated": currency_service.last_updated.isoformat() if hasattr(currency_service, 'last_updated') and currency_service.last_updated else None,
            "using_fallback": currency_service.using_fallback if hasattr(currency_service, 'using_fallback') else True
        }
        
        return {
            "total_cars": total_cars,
            "cars_with_url": cars_with_url,
            "cars_without_url": cars_without_url,
            "currency_status": currency_status
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add a middleware to handle base paths in Vercel environment
@app.middleware("http")
async def add_base_path(request: Request, call_next):
    response = await call_next(request)
    return response

@app.get("/api/check-brightdata")
async def check_brightdata():
    """Check if BrightData is configured"""
    try:
        from src.brightdata_config import BRIGHTDATA_CONFIG, get_brightdata_proxy
        
        # Check if BrightData is configured
        is_configured = all([
            BRIGHTDATA_CONFIG["username"],
            BRIGHTDATA_CONFIG["password"],
            BRIGHTDATA_CONFIG["host"]
        ])
        
        # Get proxy URL (masked for security)
        proxy = get_brightdata_proxy()
        proxy_configured = proxy is not None
        
        return {
            "is_configured": is_configured,
            "proxy_configured": proxy_configured,
            "host": BRIGHTDATA_CONFIG["host"] if is_configured else None,
            "username": BRIGHTDATA_CONFIG["username"][:10] + "..." if is_configured else None,
            "port": BRIGHTDATA_CONFIG["port"] if is_configured else None
        }
    except Exception as e:
        logger.error(f"Error checking BrightData configuration: {str(e)}")
        return {
            "is_configured": False,
            "error": str(e)
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

@app.get("/test-page", response_class=HTMLResponse)
async def test_page(request: Request):
    """A simple test page to verify routing"""
    content = """
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-6">Test Page</h1>
        <div class="bg-white p-6 rounded-lg shadow-md">
            <p class="text-green-500">If you can see this page, routing is working correctly!</p>
            <div class="mt-4">
                <h2 class="text-xl font-semibold mb-2">Navigation Test Links</h2>
                <ul class="list-disc pl-5 space-y-2">
                    <li><a href="/" class="text-blue-600 hover:underline">Home</a></li>
                    <li><a href="/stats" class="text-blue-600 hover:underline">Stats</a></li>
                    <li><a href="/scrape" class="text-blue-600 hover:underline">Scraper</a></li>
                    <li><a href="/admin" class="text-blue-600 hover:underline">Admin</a></li>
                    <li><a href="/api/test" class="text-blue-600 hover:underline">API Test</a></li>
                </ul>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(get_page_html("Test Page", content))

@app.get("/api/test-stats")
async def test_stats_api():
    """Test stats API endpoint"""
    return {
        "message": "Stats API is working",
        "total_cars": 100,
        "cars_with_url": 75,
        "cars_without_url": 25,
        "currency_status": {
            "status": "Active",
            "last_updated": datetime.utcnow().isoformat(),
            "using_fallback": False
        }
    }

@app.get("/api/hello")
async def hello_api():
    """Simple hello world API endpoint"""
    return {"message": "Hello from CarAgentApp API!"}

@app.get("/api-test", response_class=HTMLResponse)
async def api_test_view(request: Request):
    """API test page"""
    content = """
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold mb-6">API Test Page</h1>
        
        <div class="bg-white p-6 rounded-lg shadow-md mb-8">
            <h2 class="text-xl font-semibold mb-4">Test API Endpoints</h2>
            
            <div class="space-y-4">
                <div>
                    <h3 class="font-medium">Hello API</h3>
                    <button id="testHelloBtn" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Test Hello API
                    </button>
                    <pre id="helloResult" class="mt-2 p-2 bg-gray-100 rounded"></pre>
                </div>
                
                <div>
                    <h3 class="font-medium">Stats API</h3>
                    <button id="testStatsBtn" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Test Stats API
                    </button>
                    <pre id="statsResult" class="mt-2 p-2 bg-gray-100 rounded"></pre>
                </div>
                
                <div>
                    <h3 class="font-medium">BrightData API</h3>
                    <button id="testBrightDataBtn" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Test BrightData API
                    </button>
                    <pre id="brightDataResult" class="mt-2 p-2 bg-gray-100 rounded"></pre>
                </div>
                
                <div>
                    <h3 class="font-medium">Debug Routes</h3>
                    <button id="debugRoutesBtn" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Debug Routes
                    </button>
                    <pre id="debugResult" class="mt-2 p-2 bg-gray-100 rounded"></pre>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Test Hello API
            document.getElementById('testHelloBtn').addEventListener('click', async function() {
                const resultEl = document.getElementById('helloResult');
                resultEl.textContent = 'Loading...';
                
                try {
                    const response = await fetch('/api/hello');
                    const data = await response.json();
                    resultEl.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultEl.textContent = `Error: ${error.message}`;
                }
            });
            
            // Test Stats API
            document.getElementById('testStatsBtn').addEventListener('click', async function() {
                const resultEl = document.getElementById('statsResult');
                resultEl.textContent = 'Loading...';
                
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    resultEl.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultEl.textContent = `Error: ${error.message}`;
                }
            });
            
            // Test BrightData API
            document.getElementById('testBrightDataBtn').addEventListener('click', async function() {
                const resultEl = document.getElementById('brightDataResult');
                resultEl.textContent = 'Loading...';
                
                try {
                    const response = await fetch('/api/check-brightdata');
                    const data = await response.json();
                    resultEl.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultEl.textContent = `Error: ${error.message}`;
                }
            });
            
            // Debug Routes
            document.getElementById('debugRoutesBtn').addEventListener('click', async function() {
                const resultEl = document.getElementById('debugResult');
                resultEl.textContent = 'Loading...';
                
                try {
                    const response = await fetch('/debug-routes');
                    const data = await response.json();
                    resultEl.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultEl.textContent = `Error: ${error.message}`;
                }
            });
        });
    </script>
    """
    
    return HTMLResponse(get_page_html("API Test", content))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 