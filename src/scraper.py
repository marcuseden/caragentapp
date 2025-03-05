import asyncio
import aiohttp
import motor.motor_asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional
import logging
from config import *
from dataclasses import dataclass
import re
import random
import time
from src.db import MongoDB
from src.config import get_proxy_url

# Define the missing constants
BASE_URL = "https://www.bilbasen.dk/brugt/bil"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0"
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CarListing:
    brand: str
    model: str
    registration_number: Optional[str]
    year: int
    mileage: int  # in kilometers
    transmission: str
    fuel_type: str
    body_type: str
    color: str
    wltp_range: Optional[int]  # for electric vehicles, in km
    price: float
    currency: str
    url: str

class CarScraper:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        self.session = None
        
    async def init_session(self):
        self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str, cursor: str = None) -> str:
        """Fetch page content using Bright Data proxy"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        if cursor:
            url = f"{url}?page={cursor}"
        
        # Get country from URL and log it
        country = next((k for k, urls in URLS.items() if any(u in url for u in urls)), None)
        country_code = BRIGHT_DATA_COUNTRY_MAP.get(country, '')
        logger.info(f"Attempting to fetch URL: {url}")
        logger.info(f"Using country code: {country_code}")
        
        # Configure proxy with country-specific settings
        proxy_url = get_proxy_url(country_code)
        logger.info(f"Using proxy URL: {proxy_url}")
        
        try:
            # Configure proxy with SSL verification disabled (if needed)
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn) as session:
                logger.info("Sending request...")
                async with session.get(
                    url,
                    headers=headers,
                    proxy=proxy_url,
                    timeout=30
                ) as response:
                    logger.info(f"Response status: {response.status}")
                    if response.status == 200:
                        content = await response.text()
                        logger.info(f"Successfully fetched {len(content)} bytes")
                        return content
                    else:
                        logger.error(f"Error fetching {url}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Exception while fetching {url}: {str(e)}")
            return None
        finally:
            await asyncio.sleep(1/REQUESTS_PER_SECOND)  # Rate limiting

    async def _parse_bilbasen(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse listings from bilbasen.dk"""
        listings = []
        # Bilbasen uses VIP-cards for listings
        cars = soup.find_all('div', {'data-test': 'VIP-card'})  
        
        logger.info(f"Found {len(cars)} car listings on bilbasen.dk")
        
        for car in cars:
            try:
                # Get the main details container
                details = car.find('div', {'data-test': 'card-details'})
                price_elem = car.find('div', {'data-test': 'price-details'})
                
                # Extract data with better error handling
                try:
                    title = details.find('h3').text.strip()
                    brand, model = self._parse_title(title)
                except:
                    brand, model = "Unknown", "Unknown"
                    
                try:
                    specs = details.find_all('span', {'data-test': 'spec-data'})
                    year = self._extract_year(specs)
                    mileage = self._extract_mileage(specs)
                    fuel_type = self._extract_fuel_type(specs)
                except:
                    year, mileage, fuel_type = 0, 0, "Unknown"
                    
                try:
                    price = self._parse_price(price_elem.text) if price_elem else 0.0
                except:
                    price = 0.0
                    
                listing = CarListing(
                    brand=brand,
                    model=model,
                    registration_number=None,  # Not always available
                    year=year,
                    mileage=mileage,
                    transmission="Unknown",  # Need to find correct selector
                    fuel_type=fuel_type,
                    body_type="Unknown",  # Need to find correct selector
                    color="Unknown",  # Need to find correct selector
                    wltp_range=None,  # Only for electric vehicles
                    price=price,
                    currency='DKK',
                    url=self._get_listing_url(car)
                )
                
                logger.debug(f"Parsed listing: {listing}")
                listings.append(listing.__dict__)
                
            except Exception as e:
                logger.error(f"Error parsing car listing: {str(e)}")
                continue
        
        return listings

    def _parse_title(self, title: str) -> tuple:
        """Parse brand and model from title"""
        parts = title.split(' ', 1)
        if len(parts) >= 2:
            return parts[0], parts[1]
        return parts[0], "Unknown"

    def _extract_year(self, specs: List) -> int:
        """Extract year from specifications"""
        for spec in specs:
            if spec.text.strip().isdigit():
                return int(spec.text.strip())
        return 0

    def _extract_mileage(self, specs: List) -> int:
        """Extract mileage from specifications"""
        for spec in specs:
            text = spec.text.strip().lower()
            if 'km' in text:
                return self._convert_mileage(text)
        return 0

    def _extract_fuel_type(self, specs: List) -> str:
        """Extract fuel type from specifications"""
        fuel_types = ['benzin', 'diesel', 'el', 'hybrid', 'plugin']
        for spec in specs:
            text = spec.text.strip().lower()
            if text in fuel_types:
                return text
        return "Unknown"

    def _get_listing_url(self, car_elem) -> str:
        """Extract the full URL for the listing"""
        try:
            link = car_elem.find('a')
            if link and 'href' in link.attrs:
                url = link['href']
                if not url.startswith('http'):
                    url = f"https://www.bilbasen.dk{url}"
                return url
        except:
            pass
        return ""

    async def _parse_finn(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse listings from finn.no"""
        listings = []
        cars = soup.find_all('article', class_='ads__unit')  # adjust selector as needed
        
        for car in cars:
            try:
                listing = CarListing(
                    brand=car.find('div', class_='brand').text.strip(),
                    model=car.find('div', class_='model').text.strip(),
                    registration_number=car.find('div', class_='reg').text.strip(),
                    year=int(car.find('div', class_='year').text.strip()),
                    mileage=self._convert_mileage(car.find('div', class_='mileage').text.strip()),
                    transmission=car.find('div', class_='transmission').text.strip(),
                    fuel_type=car.find('div', class_='fuel').text.strip(),
                    body_type=car.find('div', class_='body').text.strip(),
                    color=car.find('div', class_='color').text.strip(),
                    wltp_range=self._parse_wltp(car.find('div', class_='wltp')),
                    price=self._parse_price(car.find('div', class_='price').text.strip()),
                    currency='NOK',
                    url=car.find('a', class_='ad-link')['href']
                )
                listings.append(listing.__dict__)
            except Exception as e:
                logger.error(f"Error parsing listing: {str(e)}")
                continue
        
        return listings

    def _convert_mileage(self, mileage_text: str) -> int:
        """Convert mileage from various formats to kilometers"""
        # Remove non-numeric characters and convert to int
        numbers = ''.join(filter(str.isdigit, mileage_text))
        if not numbers:
            return 0
            
        mileage = int(numbers)
        
        # Convert from miles to km if needed
        if 'mil' in mileage_text.lower():
            return mileage * 10  # Swedish/Norwegian mil = 10km
        
        return mileage

    def _parse_wltp(self, wltp_element) -> Optional[int]:
        """Parse WLTP range for electric vehicles"""
        if not wltp_element:
            return None
            
        try:
            # Extract numeric value from WLTP range text
            wltp_text = wltp_element.text.strip()
            numbers = ''.join(filter(str.isdigit, wltp_text))
            return int(numbers) if numbers else None
        except:
            return None

    def _parse_price(self, price_text: str) -> float:
        """Convert price string to float"""
        # Remove currency symbols and non-numeric characters
        numbers = ''.join(filter(lambda x: x.isdigit() or x == '.', price_text))
        return float(numbers) if numbers else 0.0

    async def parse_listing(self, html: str, source: str) -> List[Dict]:
        """Parse car listings from HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        
        if 'bilbasen.dk' in source:
            return await self._parse_bilbasen(soup)
        elif 'finn.no' in source:
            return await self._parse_finn(soup)
        elif 'blocket.se' in source:
            return await self._parse_blocket(soup)
        # Add more website-specific parsing methods
        
        logger.warning(f"No parser implemented for {source}")
        return []

    def _get_next_cursor(self, html: str) -> Optional[str]:
        """Extract next page cursor from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for common pagination patterns
        next_link = soup.find('a', class_='next') or \
                   soup.find('a', rel='next') or \
                   soup.find('a', text=lambda t: t and 'Next' in t)
                   
        if next_link and 'href' in next_link.attrs:
            # Extract page number from href
            href = next_link['href']
            page_match = re.search(r'page=(\d+)', href)
            if page_match:
                return page_match.group(1)
        
        return None

    async def store_listings(self, listings: List[Dict]):
        """Store listings in MongoDB"""
        if not listings:
            return
            
        try:
            await self.collection.insert_many(listings)
            logger.info(f"Stored {len(listings)} listings in database")
        except Exception as e:
            logger.error(f"Error storing listings: {str(e)}")

    async def scrape_website(self, url: str, country: str):
        """Scrape a single website with cursor pagination"""
        cursor = "1"
        while cursor:
            html = await self.fetch_page(url, cursor)
            if not html:
                break
                
            listings = await self.parse_listing(html, url)
            if not listings:
                break
                
            # Add metadata to listings
            for listing in listings:
                listing.update({
                    'source_url': url,
                    'country': country,
                    'scraped_at': datetime.utcnow()
                })
                
            await self.store_listings(listings)
            
            # Update cursor for next page
            cursor = self._get_next_cursor(html)
            await asyncio.sleep(1/REQUESTS_PER_SECOND)  # Rate limiting

    async def run(self):
        """Main entry point to run the scraper"""
        await self.init_session()
        
        tasks = []
        for country, urls in URLS.items():
            for url in urls:
                tasks.append(self.scrape_website(url, country))
                
        await asyncio.gather(*tasks)
        await self.close_session()

async def fetch_page(session, url, retries=3):
    """Fetch a page with retry logic"""
    for attempt in range(retries):
        try:
            # Add random delay to avoid rate limiting
            await asyncio.sleep(random.uniform(1, 3))
            
            async with session.get(url, headers=HEADERS, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                logger.warning(f"Got status {response.status} for {url}")
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{retries} failed for {url}: {str(e)}")
            if attempt == retries - 1:
                logger.error(f"Failed to fetch {url} after {retries} attempts")
                return None
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    return None

async def parse_listing_page(html, country="denmark"):
    """Parse a listing page to extract basic car info and detail URLs"""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    
    # This selector will need to be adjusted based on the actual site structure
    # For Bilbasen, we'll try different selectors
    car_elements = soup.select('.bb-listing-clickable, .listing-heading, .listing-card')
    
    if not car_elements:
        # Try alternative selectors if the first ones don't work
        car_elements = soup.select('article, .car-item, .car-card')
    
    logger.info(f"Found {len(car_elements)} car elements on page")
    
    for car_element in car_elements:
        try:
            # Extract basic info - try different possible selectors
            title_element = (
                car_element.select_one('.bb-listing-title, .listing-heading h2, .car-title') or
                car_element.select_one('h2, h3')
            )
            
            price_element = (
                car_element.select_one('.bb-listing-price, .price, .listing-price') or
                car_element.select_one('[class*="price"]')
            )
            
            # Try to find the detail URL
            detail_url = None
            if car_element.name == 'a':
                detail_url = car_element.get('href')
            else:
                link = car_element.select_one('a')
                if link:
                    detail_url = link.get('href')
            
            if title_element and price_element and detail_url:
                # Process title to extract brand and model
                title_text = title_element.text.strip()
                
                # Try to extract brand and model
                brand = "Unknown"
                model = ""
                
                # Common car brands to look for
                car_brands = ["Audi", "BMW", "Mercedes", "Volkswagen", "VW", "Ford", "Toyota", 
                              "Honda", "Mazda", "Nissan", "Volvo", "Peugeot", "Renault", "Skoda", 
                              "Hyundai", "Kia", "Tesla", "Porsche", "Fiat", "Citroen"]
                
                for b in car_brands:
                    if b.lower() in title_text.lower():
                        brand = b
                        model_start = title_text.lower().find(b.lower()) + len(b)
                        model = title_text[model_start:].strip()
                        break
                
                if brand == "Unknown" and " " in title_text:
                    # If no known brand found, use first word as brand
                    title_parts = title_text.split(' ', 1)
                    brand = title_parts[0]
                    model = title_parts[1] if len(title_parts) > 1 else ""
                
                # Process price
                price_text = price_element.text.strip()
                price = 0
                
                # Extract digits from price
                digits = ''.join(filter(str.isdigit, price_text))
                if digits:
                    price = int(digits)
                
                # Make sure the URL is absolute
                if detail_url and not detail_url.startswith('http'):
                    if detail_url.startswith('/'):
                        detail_url = f"https://www.bilbasen.dk{detail_url}"
                    else:
                        detail_url = f"https://www.bilbasen.dk/{detail_url}"
                
                # Add to listings
                listings.append({
                    'brand': brand,
                    'model': model,
                    'cash_price': price,
                    'country': country,
                    'source_url': detail_url,
                    'scraped_at': datetime.utcnow()
                })
                
                logger.debug(f"Found car: {brand} {model}, Price: {price}")
        except Exception as e:
            logger.error(f"Error parsing car element: {str(e)}")
    
    logger.info(f"Extracted {len(listings)} car listings from page")
    return listings

async def parse_detail_page(session, car_data):
    """Fetch and parse a car detail page to get more information"""
    if not car_data or 'source_url' not in car_data:
        return car_data
    
    url = car_data['source_url']
    html = await fetch_page(session, url)
    
    if not html:
        return car_data
    
    soup = BeautifulSoup(html, 'html.parser')
    
    try:
        # Try to extract year - look for patterns like "Year: 2020" or just "2020"
        year_patterns = [
            # Look for year in a dedicated element
            lambda s: s.select_one('.year, .car-year, [class*="year"]'),
            # Look for text containing "year" or "årgang"
            lambda s: s.find(text=re.compile(r'(year|årgang|årsmodel)', re.I)),
            # Look for 4-digit numbers that could be years
            lambda s: re.search(r'\b(19|20)\d{2}\b', s.text)
        ]
        
        for pattern in year_patterns:
            result = pattern(soup)
            if result:
                if hasattr(result, 'text'):  # If it's an element
                    year_text = result.text.strip()
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                    if year_match:
                        car_data['year'] = int(year_match.group(0))
                        break
                elif hasattr(result, 'group'):  # If it's a regex match
                    car_data['year'] = int(result.group(0))
                    break
        
        # Try to extract mileage - look for patterns like "150,000 km" or "150.000 km"
        mileage_patterns = [
            # Look for mileage in a dedicated element
            lambda s: s.select_one('.mileage, .car-mileage, [class*="mileage"], [class*="kilometer"]'),
            # Look for text containing "km" or "kilometer"
            lambda s: s.find(text=re.compile(r'(km|kilometer|miles)', re.I))
        ]
        
        for pattern in mileage_patterns:
            result = pattern(soup)
            if result and hasattr(result, 'text'):
                mileage_text = result.text.strip()
                # Extract digits, ignoring separators
                mileage_digits = ''.join(filter(str.isdigit, mileage_text))
                if mileage_digits:
                    car_data['mileage'] = int(mileage_digits)
                    break
        
        # Try to extract fuel type
        fuel_patterns = [
            # Look for fuel type in a dedicated element
            lambda s: s.select_one('.fuel, .fuel-type, [class*="fuel"]'),
            # Look for common fuel types in text
            lambda s: s.find(text=re.compile(r'(diesel|petrol|benzin|electric|el|hybrid)', re.I))
        ]
        
        for pattern in fuel_patterns:
            result = pattern(soup)
            if result and hasattr(result, 'text'):
                fuel_text = result.text.strip().lower()
                
                # Map common fuel terms to standardized values
                fuel_mapping = {
                    'diesel': 'Diesel',
                    'benzin': 'Petrol',
                    'petrol': 'Petrol',
                    'electric': 'El',
                    'el': 'El',
                    'hybrid': 'Hybrid',
                    'plugin': 'Plug-in Hybrid',
                    'plug-in': 'Plug-in Hybrid'
                }
                
                for key, value in fuel_mapping.items():
                    if key in fuel_text:
                        car_data['fuel_type'] = value
                        break
                
                if 'fuel_type' in car_data:
                    break
        
        # Try to extract equipment/features
        equipment_patterns = [
            # Look for lists of equipment
            lambda s: s.select('ul.equipment li, .features li, .car-features li'),
            # Look for comma-separated features
            lambda s: s.select('[class*="equipment"], [class*="features"]')
        ]
        
        for pattern in equipment_patterns:
            elements = pattern(soup)
            if elements:
                if isinstance(elements, list):
                    equipment = [item.text.strip() for item in elements if item.text.strip()]
                    if equipment:
                        car_data['equipment'] = equipment
                        break
                else:
                    # If it's a single element with comma-separated features
                    text = elements.text.strip()
                    if ',' in text:
                        equipment = [item.strip() for item in text.split(',') if item.strip()]
                        if equipment:
                            car_data['equipment'] = equipment
                            break
        
        # For electric cars, try to extract battery info
        if car_data.get('fuel_type') == 'El':
            # Try to find battery capacity (kWh)
            battery_patterns = [
                lambda s: s.find(text=re.compile(r'\d+\s*kwh|\d+\s*kWh', re.I)),
                lambda s: s.find(text=re.compile(r'battery.*capacity', re.I))
            ]
            
            for pattern in battery_patterns:
                result = pattern(soup)
                if result:
                    battery_text = result if isinstance(result, str) else result.text
                    capacity_match = re.search(r'(\d+[.,]?\d*)\s*kwh', battery_text, re.I)
                    if capacity_match:
                        capacity = capacity_match.group(1).replace(',', '.')
                        car_data['battery_capacity'] = float(capacity)
                        break
            
            # Try to find range (km)
            range_patterns = [
                lambda s: s.find(text=re.compile(r'\d+\s*km.*range|range.*\d+\s*km', re.I)),
                lambda s: s.find(text=re.compile(r'wltp.*\d+|rækkevidde.*\d+', re.I))
            ]
            
            for pattern in range_patterns:
                result = pattern(soup)
                if result:
                    range_text = result if isinstance(result, str) else result.text
                    range_match = re.search(r'(\d+)\s*km', range_text)
                    if range_match:
                        car_data['range_km'] = int(range_match.group(1))
                        break
    
    except Exception as e:
        logger.error(f"Error parsing detail page {url}: {str(e)}")
    
    return car_data

async def scrape_cars(target_count=500):
    """Main function to scrape cars"""
    db = MongoDB()
    await db.init_db()
    
    try:
        # Create a session for all requests
        async with aiohttp.ClientSession() as session:
            page = 1
            total_cars = 0
            
            while total_cars < target_count:
                # Construct page URL
                page_url = f"{BASE_URL}?page={page}"
                logger.info(f"Scraping page {page}: {page_url}")
                
                # Fetch listing page
                html = await fetch_page(session, page_url)
                if not html:
                    logger.error(f"Failed to fetch page {page}")
                    break
                
                # Parse listing page to get basic car info
                cars = await parse_listing_page(html)
                if not cars:
                    logger.info(f"No cars found on page {page}, stopping")
                    break
                
                # Fetch and parse detail pages for each car
                detailed_cars = []
                for car in cars[:min(len(cars), target_count - total_cars)]:
                    detailed_car = await parse_detail_page(session, car)
                    detailed_cars.append(detailed_car)
                    
                    # Add a small delay between detail page requests
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Store cars in database
                if detailed_cars:
                    stored_count = await db.store_listings(detailed_cars)
                    logger.info(f"Stored {stored_count} cars from page {page}")
                    total_cars += stored_count
                
                # Check if we've reached the target
                if total_cars >= target_count:
                    logger.info(f"Reached target of {target_count} cars")
                    break
                
                # Move to next page
                page += 1
                
                # Add a delay between pages
                await asyncio.sleep(random.uniform(2, 5))
        
        logger.info(f"Scraping completed. Total cars scraped: {total_cars}")
        return total_cars
    
    except Exception as e:
        logger.error(f"Error in scrape_cars: {str(e)}")
        return 0
    finally:
        await db.close()

async def main():
    """Entry point for the scraper"""
    logger.info("Starting car scraper")
    start_time = time.time()
    
    # Scrape cars
    car_count = await scrape_cars(500)
    
    # Log results
    elapsed_time = time.time() - start_time
    logger.info(f"Scraping completed in {elapsed_time:.2f} seconds")
    logger.info(f"Total cars scraped: {car_count}")
    
    return car_count > 0

if __name__ == "__main__":
    asyncio.run(main()) 