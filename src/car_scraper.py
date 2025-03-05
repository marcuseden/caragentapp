import asyncio
import aiohttp
import logging
import os
import re
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId

# Import configuration
from config import MONGODB_URI, DB_NAME, COLLECTION_NAME

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Create images directory if it doesn't exist
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "images", "cars")
os.makedirs(IMAGES_DIR, exist_ok=True)

class CarScraper:
    def __init__(self, max_cars=1000, delay_range=(1, 3)):
        self.max_cars = max_cars
        self.delay_range = delay_range
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        self.session = None
    
    async def initialize(self):
        """Initialize the aiohttp session"""
        self.session = aiohttp.ClientSession(headers=self.headers)
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def download_image(self, url, car_id, index=0):
        """Download an image and save it to the images directory"""
        if not url:
            return None
        
        try:
            # Create a filename based on car_id and image index
            parsed_url = urlparse(url)
            file_ext = os.path.splitext(parsed_url.path)[1]
            if not file_ext:
                file_ext = '.jpg'  # Default to jpg if no extension
            
            filename = f"{car_id}_{index}{file_ext}"
            filepath = os.path.join(IMAGES_DIR, filename)
            
            # Download the image
            async with self.session.get(url, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download image {url}: Status {response.status}")
                    return None
                
                # Save the image to disk
                with open(filepath, 'wb') as f:
                    f.write(await response.read())
                
                # Return the relative path to the image
                return f"/static/images/cars/{filename}"
        
        except Exception as e:
            logger.error(f"Error downloading image {url}: {str(e)}")
            return None
    
    async def scrape_car_details(self, url):
        """Scrape detailed information about a car from its page"""
        try:
            # Add a random delay to avoid being blocked
            await asyncio.sleep(random.uniform(*self.delay_range))
            
            # Fetch the car detail page
            async with self.session.get(url, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch car details from {url}: Status {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Check if the car is sold
                sold_indicators = ['sold', 'verkauft', 'vendu', 'vendido', 'venduto', 'solgt']
                page_text = soup.get_text().lower()
                if any(indicator in page_text for indicator in sold_indicators):
                    logger.info(f"Car at {url} appears to be sold, skipping")
                    return None
                
                # Extract car details
                car = {
                    'source_url': url,
                    'last_updated': datetime.utcnow(),
                    'images': [],
                    'seller_info': {}
                }
                
                # Extract basic car information (customize based on the website structure)
                # This is a generic example - you'll need to adapt to specific sites
                
                # Title/Name
                title_elem = soup.select_one('h1.car-title, .vehicle-title, .listing-title')
                if title_elem:
                    car['title'] = title_elem.get_text().strip()
                    
                    # Try to extract brand and model from title
                    title_parts = car['title'].split()
                    if len(title_parts) >= 2:
                        car['brand'] = title_parts[0]
                        car['model'] = ' '.join(title_parts[1:])
                
                # Price
                price_elem = soup.select_one('.price, .vehicle-price, .listing-price')
                if price_elem:
                    price_text = price_elem.get_text().strip()
                    # Extract numeric price and currency
                    price_match = re.search(r'([\d.,]+)\s*([A-Za-z]{3})?', price_text)
                    if price_match:
                        price_value = price_match.group(1).replace('.', '').replace(',', '.')
                        car['price'] = price_text
                        car['price_value'] = float(price_value)
                        car['currency'] = price_match.group(2) or 'EUR'  # Default to EUR if no currency found
                
                # Year
                year_elem = soup.select_one('.year, .vehicle-year, .listing-year')
                if year_elem:
                    year_text = year_elem.get_text().strip()
                    year_match = re.search(r'(\d{4})', year_text)
                    if year_match:
                        car['year'] = int(year_match.group(1))
                
                # Mileage
                mileage_elem = soup.select_one('.mileage, .vehicle-mileage, .listing-mileage')
                if mileage_elem:
                    mileage_text = mileage_elem.get_text().strip()
                    mileage_match = re.search(r'([\d.,]+)', mileage_text)
                    if mileage_match:
                        mileage_value = mileage_match.group(1).replace('.', '').replace(',', '')
                        car['mileage'] = mileage_text
                        car['mileage_value'] = int(mileage_value)
                
                # Fuel type
                fuel_elem = soup.select_one('.fuel, .vehicle-fuel, .listing-fuel')
                if fuel_elem:
                    car['fuel_type'] = fuel_elem.get_text().strip()
                
                # Transmission
                transmission_elem = soup.select_one('.transmission, .vehicle-transmission, .listing-transmission')
                if transmission_elem:
                    car['transmission'] = transmission_elem.get_text().strip()
                
                # Country/Location
                location_elem = soup.select_one('.location, .vehicle-location, .listing-location')
                if location_elem:
                    location_text = location_elem.get_text().strip()
                    # Try to extract country from location
                    countries = ['denmark', 'germany', 'sweden', 'norway', 'poland', 'france', 'italy', 'portugal']
                    for country in countries:
                        if country in location_text.lower():
                            car['country'] = country
                            break
                    if 'country' not in car:
                        car['country'] = 'unknown'
                
                # Extract seller information
                seller_elem = soup.select_one('.seller, .dealer, .contact-info')
                if seller_elem:
                    # Seller name
                    name_elem = seller_elem.select_one('.name, .seller-name, .dealer-name')
                    if name_elem:
                        car['seller_info']['name'] = name_elem.get_text().strip()
                    
                    # Seller phone
                    phone_elem = seller_elem.select_one('.phone, .seller-phone, .dealer-phone')
                    if phone_elem:
                        car['seller_info']['phone'] = phone_elem.get_text().strip()
                    
                    # Seller email
                    email_elem = seller_elem.select_one('.email, .seller-email, .dealer-email')
                    if email_elem:
                        car['seller_info']['email'] = email_elem.get_text().strip()
                    
                    # Alternative: look for email pattern in the page
                    if 'email' not in car['seller_info']:
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                        email_matches = re.findall(email_pattern, html)
                        if email_matches:
                            car['seller_info']['email'] = email_matches[0]
                
                # Extract images
                image_elements = soup.select('.car-image, .vehicle-image, .listing-image, .gallery img')
                image_urls = []
                
                for img in image_elements:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        # Make sure the URL is absolute
                        full_url = urljoin(url, src)
                        image_urls.append(full_url)
                
                # If no images found, try alternative selectors
                if not image_urls:
                    # Look for image URLs in the page source
                    img_pattern = r'(https?://[^\s"\']+\.(jpg|jpeg|png|webp))'
                    img_matches = re.findall(img_pattern, html)
                    image_urls = [match[0] for match in img_matches]
                
                # Download images
                for i, img_url in enumerate(image_urls[:10]):  # Limit to 10 images per car
                    local_path = await self.download_image(img_url, car.get('_id', f"temp_{int(time.time())}"), i)
                    if local_path:
                        car['images'].append({
                            'url': img_url,
                            'local_path': local_path,
                            'is_primary': i == 0  # First image is primary
                        })
                
                return car
        
        except Exception as e:
            logger.error(f"Error scraping car details from {url}: {str(e)}")
            return None
    
    async def scrape_listing_page(self, url):
        """Scrape a listing page to find car detail URLs"""
        try:
            # Add a random delay to avoid being blocked
            await asyncio.sleep(random.uniform(*self.delay_range))
            
            # Fetch the listing page
            async with self.session.get(url, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch listing page {url}: Status {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find car detail links (customize based on the website structure)
                car_links = []
                link_elements = soup.select('.car-link, .vehicle-link, .listing-link, .car-title a')
                
                for link in link_elements:
                    href = link.get('href')
                    if href:
                        # Make sure the URL is absolute
                        full_url = urljoin(url, href)
                        car_links.append(full_url)
                
                return car_links
        
        except Exception as e:
            logger.error(f"Error scraping listing page {url}: {str(e)}")
            return []
    
    async def scrape_cars(self, listing_urls):
        """Scrape cars from the provided listing URLs"""
        try:
            await self.initialize()
            
            # Initialize counters
            cars_saved = 0
            images_saved = 0
            
            # Process each listing URL
            for listing_url in listing_urls:
                logger.info(f"Scraping listing page: {listing_url}")
                
                # Get car detail URLs from the listing page
                car_urls = await self.scrape_listing_page(listing_url)
                logger.info(f"Found {len(car_urls)} car URLs on listing page")
                
                # Process each car URL
                for car_url in car_urls:
                    # Check if we've reached the maximum number of cars
                    if cars_saved >= self.max_cars:
                        logger.info(f"Reached maximum number of cars to scrape ({self.max_cars})")
                        break
                    
                    # Check if this car URL is already in the database
                    existing_car = await collection.find_one({"source_url": car_url})
                    if existing_car:
                        logger.info(f"Car with URL {car_url} already exists in database, skipping")
                        continue
                    
                    # Scrape car details
                    logger.info(f"Scraping car details from: {car_url}")
                    car_data = await self.scrape_car_details(car_url)
                    
                    # If car data was successfully scraped and the car is not sold
                    if car_data:
                        # Insert the car into the database
                        result = await collection.insert_one(car_data)
                        
                        # Update the car's ID and re-download images with the correct ID
                        car_id = result.inserted_id
                        
                        # If images were found with a temporary ID, update them
                        if car_data['images'] and 'temp_' in car_data['images'][0]['local_path']:
                            new_images = []
                            for i, img in enumerate(car_data['images']):
                                new_path = await self.download_image(img['url'], car_id, i)
                                if new_path:
                                    new_images.append({
                                        'url': img['url'],
                                        'local_path': new_path,
                                        'is_primary': i == 0
                                    })
                            
                            # Update the car with the new image paths
                            await collection.update_one(
                                {"_id": car_id},
                                {"$set": {"images": new_images}}
                            )
                        
                        logger.info(f"Saved car with ID {car_id}")
                        cars_saved += 1
                        images_saved += len(car_data.get('images', []))
                    
                    # Check if we've reached the maximum number of cars
                    if cars_saved >= self.max_cars:
                        break
            
            logger.info(f"Scraping complete. Processed {cars_saved} cars, saved {images_saved} images.")
            return cars_saved, images_saved
        
        except Exception as e:
            logger.error(f"Error scraping cars: {str(e)}")
            return 0, 0
        finally:
            # Make sure to close the session
            await self.close()

# Example usage
async def main():
    # List of car listing URLs to scrape
    listing_urls = [
        'https://www.example.com/cars/page1',
        'https://www.example.com/cars/page2',
        # Add more listing URLs as needed
    ]
    
    scraper = CarScraper(max_cars=1000)
    cars_saved, images_saved = await scraper.scrape_cars(listing_urls)
    logger.info(f"Saved {cars_saved} new cars and {images_saved} images to the database")

if __name__ == "__main__":
    asyncio.run(main()) 