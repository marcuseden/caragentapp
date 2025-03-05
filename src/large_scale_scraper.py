import asyncio
import aiohttp
import logging
import random
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import ssl
import os
import sys
from urllib.parse import urljoin
from bson.objectid import ObjectId

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db import MongoDB
from src.config import get_proxy_url

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# Define source sites for different countries
SOURCES = [
    {
        "name": "bilbasen",
        "country": "denmark",
        "base_url": "https://www.bilbasen.dk/brugt/bil",
        "listing_selector": "div.bb-listing-clickable, article.listing-item",
        "pagination_param": "page",
        "title_selector": "h2.listing-heading, .bb-listing-title",
        "price_selector": ".bb-listing-price, .listing-price",
        "link_selector": "a.listing-link, a.bb-listing-link",
        "max_pages": 100
    },
    {
        "name": "mobile",
        "country": "germany",
        "base_url": "https://suchen.mobile.de/fahrzeuge/search.html?categories=Car&isSearchRequest=true&sortOption.sortBy=creationTime&sortOption.sortOrder=DESCENDING",
        "listing_selector": "div.cBox--resultItem, article.car-item",
        "pagination_param": "pageNumber",
        "title_selector": "h2.headline-title, .vehicle-data__headline",
        "price_selector": ".price-block__price, .vehicle-data__price",
        "link_selector": "a.link--muted, a.vehicle-data__link",
        "max_pages": 100
    },
    {
        "name": "blocket",
        "country": "sweden",
        "base_url": "https://www.blocket.se/annonser/hela_sverige/fordon/bilar",
        "listing_selector": "article.styled__Article-sc-1kpvi4z-0, .item_row",
        "pagination_param": "page",
        "title_selector": "h2.styled__Heading-sc-1kpvi4z-11, .item_title",
        "price_selector": ".styled__Price-sc-1kpvi4z-8, .list_price",
        "link_selector": "a.styled__StyledLink-sc-1kpvi4z-2, a.item_link",
        "max_pages": 100
    }
]

async def fetch_with_retry(session, url, max_retries=3, delay=2):
    """Fetch a URL with retry logic"""
    for attempt in range(max_retries):
        try:
            # Create SSL context that ignores certificate errors
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with session.get(url, headers=HEADERS, timeout=30, ssl=ssl_context) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:  # Too Many Requests
                    wait_time = int(response.headers.get('Retry-After', delay * (attempt + 1)))
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry.")
                    await asyncio.sleep(wait_time)
                else:
                    logger.warning(f"Got status {response.status} for {url}. Attempt {attempt+1}/{max_retries}")
                    await asyncio.sleep(delay * (attempt + 1))
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}. Attempt {attempt+1}/{max_retries}")
            await asyncio.sleep(delay * (attempt + 1))
    
    return None

async def check_url_validity(session, url):
    """Check if a URL is valid without downloading the full page"""
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with session.head(url, headers=HEADERS, timeout=10, ssl=ssl_context) as response:
            return 200 <= response.status < 400
    except Exception as e:
        logger.error(f"Error checking URL {url}: {str(e)}")
        return False

async def extract_listings(html, source, base_url):
    """Extract car listings from HTML"""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    
    # Find all car listings
    elements = soup.select(source["listing_selector"])
    logger.info(f"Found {len(elements)} car elements on page")
    
    for element in elements:
        try:
            # Extract title
            title_el = element.select_one(source["title_selector"])
            if not title_el:
                continue
            title = title_el.text.strip()
            
            # Extract price
            price_el = element.select_one(source["price_selector"])
            price_text = price_el.text.strip() if price_el else ""
            
            # Extract numeric price
            price = 0
            if price_text:
                price_digits = re.findall(r'\d+', price_text.replace('.', '').replace(',', ''))
                if price_digits:
                    price = int(''.join(price_digits))
            
            # Extract link
            link_el = element.select_one(source["link_selector"]) or element.find('a')
            if not link_el or not link_el.get('href'):
                continue
            
            # Construct absolute URL
            relative_url = link_el['href']
            url = urljoin(base_url, relative_url)
            
            # Extract brand and model from title
            brand = title.split(' ')[0] if ' ' in title else title
            model = ' '.join(title.split(' ')[1:]) if ' ' in title else ""
            
            # Create listing object
            listing = {
                "title": title,
                "brand": brand,
                "model": model,
                "cash_price": price,
                "country": source["country"],
                "source_url": url,
                "source_name": source["name"],
                "scraped_at": datetime.utcnow()
            }
            
            listings.append(listing)
            
        except Exception as e:
            logger.error(f"Error extracting listing: {str(e)}")
    
    return listings

async def extract_car_details(session, listing):
    """Extract detailed car information from the car's page"""
    url = listing["source_url"]
    
    # First check if the URL is valid
    is_valid = await check_url_validity(session, url)
    if not is_valid:
        logger.warning(f"Invalid URL: {url}")
        return None
    
    html = await fetch_with_retry(session, url)
    if not html:
        logger.warning(f"Failed to fetch car details: {url}")
        return listing
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract year
        year_pattern = r'\b(19|20)\d{2}\b'
        year_matches = re.findall(year_pattern, html)
        if year_matches:
            listing["year"] = int(year_matches[0])
        
        # Extract mileage
        mileage_pattern = r'(\d{1,3}(?:[.,]\d{3})+|\d+)\s*(?:km|miles|mi)'
        mileage_matches = re.findall(mileage_pattern, html, re.IGNORECASE)
        if mileage_matches:
            mileage_text = mileage_matches[0]
            mileage_digits = re.findall(r'\d+', mileage_text.replace('.', '').replace(',', ''))
            if mileage_digits:
                listing["mileage"] = int(''.join(mileage_digits))
        
        # Extract fuel type
        fuel_types = ['Diesel', 'Petrol', 'Electric', 'Hybrid', 'Benzin', 'El', 'Plugin-hybrid']
        for fuel in fuel_types:
            if fuel.lower() in html.lower():
                if fuel.lower() == 'benzin':
                    listing["fuel_type"] = 'Petrol'
                elif fuel.lower() == 'el':
                    listing["fuel_type"] = 'Electric'
                else:
                    listing["fuel_type"] = fuel
                break
        
        # Extract color
        colors = ['Black', 'White', 'Silver', 'Blue', 'Red', 'Grey', 'Green', 'Yellow', 'Brown', 'Orange']
        for color in colors:
            if color.lower() in html.lower():
                listing["color"] = color
                break
        
        # Extract transmission
        if 'automatic' in html.lower() or 'automatisk' in html.lower() or 'automatik' in html.lower():
            listing["transmission"] = 'Automatic'
        elif 'manual' in html.lower() or 'manuell' in html.lower() or 'manuelt' in html.lower():
            listing["transmission"] = 'Manual'
        
        # Extract body type
        body_types = ['Sedan', 'Hatchback', 'SUV', 'Coupe', 'Convertible', 'Wagon', 'Van', 'Kombi']
        for body in body_types:
            if body.lower() in html.lower():
                listing["body_type"] = body
                break
        
        # For electric vehicles, try to extract battery info
        if listing.get("fuel_type") == 'Electric':
            # Extract battery capacity
            battery_pattern = r'(\d+(?:\.\d+)?)\s*kWh'
            battery_matches = re.findall(battery_pattern, html)
            if battery_matches:
                listing["battery_capacity"] = float(battery_matches[0])
            
            # Extract range
            range_pattern = r'(\d+)\s*km.*WLTP|WLTP.*(\d+)\s*km'
            range_matches = re.findall(range_pattern, html)
            if range_matches:
                flat_matches = [item for sublist in range_matches for item in sublist if item]
                if flat_matches:
                    listing["range_km"] = int(flat_matches[0])
        
        # Extract equipment
        equipment = []
        equipment_keywords = [
            'Navigation', 'Leather', 'Sunroof', 'Parking sensors', 'Camera',
            'Heated seats', 'Bluetooth', 'Cruise control', 'Climate control',
            'LED', 'Alloy wheels', 'Keyless', 'Apple CarPlay', 'Android Auto'
        ]
        
        for keyword in equipment_keywords:
            if keyword.lower() in html.lower():
                equipment.append(keyword)
        
        if equipment:
            listing["equipment"] = equipment
        
        return listing
        
    except Exception as e:
        logger.error(f"Error extracting car details from {url}: {str(e)}")
        return listing

async def scrape_source(session, source, db, target_count, start_page=1):
    """Scrape a single source until target count is reached"""
    base_url = source["base_url"]
    pagination_param = source["pagination_param"]
    max_pages = source["max_pages"]
    country = source["country"]
    
    total_scraped = 0
    page = start_page
    
    while total_scraped < target_count and page <= max_pages:
        # Construct URL with pagination
        url = f"{base_url}?{pagination_param}={page}"
        logger.info(f"Scraping {country} page {page}: {url}")
        
        # Fetch page
        html = await fetch_with_retry(session, url)
        if not html:
            logger.error(f"Failed to fetch page {page} from {country}")
            page += 1
            continue
        
        # Extract listings
        listings = await extract_listings(html, source, base_url)
        if not listings:
            logger.info(f"No listings found on page {page} from {country}")
            page += 1
            continue
        
        # Process each listing to get details
        valid_listings = []
        for listing in listings[:min(len(listings), target_count - total_scraped)]:
            detailed_listing = await extract_car_details(session, listing)
            if detailed_listing:
                valid_listings.append(detailed_listing)
            
            # Add a small delay between requests
            await asyncio.sleep(random.uniform(1, 3))
        
        # Store valid listings
        if valid_listings:
            stored_count = await db.store_listings(valid_listings)
            logger.info(f"Stored {stored_count} cars from {country} page {page}")
            total_scraped += stored_count
        
        # Check if we've reached the target
        if total_scraped >= target_count:
            logger.info(f"Reached target of {target_count} cars from {country}")
            break
        
        # Move to next page
        page += 1
        
        # Add a delay between pages
        await asyncio.sleep(random.uniform(3, 6))
    
    return total_scraped

async def main(target_count=10000):
    """Main function to scrape cars from multiple sources"""
    logger.info(f"Starting large-scale scraper to collect {target_count} cars")
    start_time = time.time()
    
    # Initialize database
    db = MongoDB()
    await db.init_db()
    
    try:
        # Create SSL context for the session
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create aiohttp session with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Calculate cars per source
            cars_per_source = target_count // len(SOURCES)
            remaining = target_count % len(SOURCES)
            
            # Create tasks for each source
            tasks = []
            for i, source in enumerate(SOURCES):
                # Add remaining cars to the first source
                source_target = cars_per_source + (remaining if i == 0 else 0)
                tasks.append(scrape_source(session, source, db, source_target))
            
            # Run all tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Calculate total cars scraped
            total_scraped = sum(results)
            
            # Log results
            elapsed_time = time.time() - start_time
            logger.info(f"Scraping completed in {elapsed_time:.2f} seconds")
            logger.info(f"Total cars scraped: {total_scraped}")
            
            return total_scraped > 0
    
    except Exception as e:
        logger.error(f"Error in main scraper: {str(e)}")
        return False
    finally:
        await db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape car listings from multiple sources")
    parser.add_argument("--count", type=int, default=10000, help="Number of cars to scrape")
    args = parser.parse_args()
    
    asyncio.run(main(args.count)) 