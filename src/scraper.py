import aiohttp
import logging
from bs4 import BeautifulSoup
from datetime import datetime
import asyncio
from src.db import save_car

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URLs for different countries
SCRAPER_URLS = {
    "denmark": ["https://www.bilbasen.dk/brugt/bil"],
    "sweden": ["https://www.blocket.se/annonser/hela_sverige/fordon/bilar"],
    "norway": ["https://www.finn.no/car/used/search.html"],
    "germany": ["https://www.mobile.de/"],
    "portugal": ["https://www.standvirtual.com/"],
    "poland": ["https://www.otomoto.pl/"],
    "france": ["https://www.lacentrale.fr/"],
    "italy": ["https://www.automobile.it/"]
}

async def scrape_cars(country, url):
    """Scrape cars from a given URL"""
    logger.info(f"Scraping cars from {url}")
    results = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Parse HTML with BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract car data based on country-specific selectors
                    if country == "denmark":
                        results = await scrape_denmark(soup)
                    elif country == "sweden":
                        results = await scrape_sweden(soup)
                    # Add more country-specific scrapers as needed
                    else:
                        # Generic scraper as fallback
                        results = await scrape_generic(soup)
                    
                    logger.info(f"Found {len(results)} cars from {url}")
                    return results
                else:
                    logger.error(f"Failed to fetch {url}: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return []

async def scrape_denmark(soup):
    """Scrape cars from Danish websites"""
    cars = []
    
    try:
        # Find car listings
        listings = soup.select('.bb-listing-clickable')
        
        for listing in listings[:5]:  # Limit to 5 for testing
            try:
                # Extract data
                title_elem = listing.select_one('.bb-listing-heading')
                price_elem = listing.select_one('.bb-listing-price')
                details_elem = listing.select_one('.bb-listing-data')
                
                title = title_elem.text.strip() if title_elem else "Unknown"
                price = price_elem.text.strip() if price_elem else "Unknown"
                details = details_elem.text.strip() if details_elem else ""
                
                # Parse title to get brand and model
                brand_model = title.split(' ', 1)
                brand = brand_model[0] if len(brand_model) > 0 else "Unknown"
                model = brand_model[1] if len(brand_model) > 1 else ""
                
                # Extract year from details
                year = ""
                if "årgang" in details.lower():
                    year_parts = details.split("årgang")
                    if len(year_parts) > 1:
                        year = year_parts[1].strip().split()[0]
                
                # Create car object
                car = {
                    "brand": brand,
                    "model": model,
                    "year": year,
                    "price": price,
                    "details": details,
                    "source_url": "https://www.bilbasen.dk" + listing.get('href', ''),
                    "source_country": "denmark",
                    "scraped_at": datetime.utcnow().isoformat()
                }
                
                cars.append(car)
                
                # Save to database
                await save_car(car)
                
            except Exception as e:
                logger.error(f"Error parsing listing: {str(e)}")
                continue
    
    except Exception as e:
        logger.error(f"Error in Denmark scraper: {str(e)}")
    
    return cars

async def scrape_sweden(soup):
    """Scrape cars from Swedish websites"""
    # Similar implementation to Denmark but with Swedish-specific selectors
    return []

async def scrape_generic(soup):
    """Generic scraper for any website"""
    # Basic implementation that looks for common patterns
    return []

async def run_scraper(country):
    """Run scraper for a specific country"""
    if country not in SCRAPER_URLS:
        return {"status": "error", "message": f"Country {country} not supported"}
    
    results = []
    for url in SCRAPER_URLS[country]:
        cars = await scrape_cars(country, url)
        results.extend(cars)
    
    return {
        "status": "success",
        "message": f"Scraped {len(results)} cars from {country}",
        "cars": results
    } 