from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from datetime import datetime
import json
from src.db import get_cars, get_car_by_id
from src.scraper import run_scraper

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

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Helper functions
def format_currency(value):
    """Format a number as currency"""
    try:
        if isinstance(value, str):
            # Remove non-numeric characters
            value = ''.join(c for c in value if c.isdigit() or c == '.')
        return f"${int(float(value)):,}" if value else "N/A"
    except (ValueError, TypeError):
        return value

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Redirect to car listing page"""
    return templates.TemplateResponse(
        "car_list.html",
        {
            "request": request,
            "cars": [],
            "total_cars": 0,
            "page": 1,
            "limit": 12,
            "total_pages": 0,
            "format_currency": format_currency
        }
    )

@app.get("/cars", response_class=HTMLResponse)
async def car_list(
    request: Request, 
    page: int = 1, 
    limit: int = 12,
    brand: str = None,
    min_year: int = None,
    max_year: int = None
):
    """Car listing page with pagination and filtering"""
    try:
        # Calculate skip for pagination
        skip = (page - 1) * limit
        
        # Build filters
        filters = {}
        if brand:
            filters["brand"] = {"$regex": brand, "$options": "i"}
        if min_year:
            filters["year"] = filters.get("year", {})
            filters["year"]["$gte"] = str(min_year)
        if max_year:
            filters["year"] = filters.get("year", {})
            filters["year"]["$lte"] = str(max_year)
        
        # Get cars with pagination and filtering
        cars, total = await get_cars(limit=limit, skip=skip, filters=filters)
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit if total > 0 else 1
        
        return templates.TemplateResponse(
            "car_list.html",
            {
                "request": request,
                "cars": cars,
                "total_cars": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "brand": brand,
                "min_year": min_year,
                "max_year": max_year,
                "format_currency": format_currency
            }
        )
    except Exception as e:
        logger.error(f"Error rendering car list: {str(e)}")
        return templates.TemplateResponse(
            "car_list.html",
            {
                "request": request,
                "error": str(e),
                "cars": [],
                "total_cars": 0,
                "page": 1,
                "limit": limit,
                "total_pages": 1,
                "format_currency": format_currency
            }
        )

@app.get("/car/{car_id}", response_class=HTMLResponse)
async def car_detail(request: Request, car_id: str):
    """Car detail page"""
    try:
        car = await get_car_by_id(car_id)
        
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        
        return templates.TemplateResponse(
            "car_detail.html",
            {
                "request": request,
                "car": car,
                "format_currency": format_currency
            }
        )
    except Exception as e:
        logger.error(f"Error rendering car detail: {str(e)}")
        return templates.TemplateResponse(
            "car_detail.html",
            {
                "request": request,
                "error": str(e),
                "car": None,
                "format_currency": format_currency
            }
        )

@app.get("/scraper", response_class=HTMLResponse)
async def scraper_page(request: Request):
    """Scraper page"""
    countries = ["denmark", "sweden", "norway", "germany", "portugal", "poland", "france", "italy"]
    return templates.TemplateResponse(
        "scraper.html",
        {
            "request": request,
            "countries": countries
        }
    )

@app.post("/run-scraper")
async def run_scraper_endpoint(country: str = Form(...)):
    """Run scraper for a specific country"""
    try:
        result = await run_scraper(country)
        return result
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "environment": os.environ.get("VERCEL_ENV", "development"),
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 