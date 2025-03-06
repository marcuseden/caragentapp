import asyncio
import aiohttp
import logging
import random
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import ssl
from src.db import MongoDB
from src.brightdata_config import get_brightdata_proxy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.bilbasen.dk/brugt/bil"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Define source domains for different countries
source_domains = {
    'denmark': 'bilbasen.dk',
    'germany': 'mobile.de',
    'sweden': 'blocket.se',
    'norway': 'finn.no',
    'poland': 'otomoto.pl',
    'france': 'lacentrale.fr'
}

# Function to generate dummy car data
def generate_dummy_cars(count=20):
    """Generate dummy car data for testing"""
    cars = []
    for i in range(count):
        # Create more varied data
        brand = random.choice(['Audi', 'BMW', 'Mercedes', 'Volkswagen', 'Toyota', 'Tesla', 
                              'Ford', 'Hyundai', 'Kia', 'Mazda', 'Volvo', 'Peugeot'])
        
        # Different models for different brands
        models = {
            'Audi': ['A3', 'A4', 'A6', 'Q5', 'e-tron'],
            'BMW': ['3-Series', '5-Series', 'X3', 'X5', 'i4'],
            'Mercedes': ['C-Class', 'E-Class', 'GLC', 'EQC'],
            'Volkswagen': ['Golf', 'Passat', 'Tiguan', 'ID.4'],
            'Toyota': ['Corolla', 'RAV4', 'Camry', 'Prius'],
            'Tesla': ['Model 3', 'Model Y', 'Model S', 'Model X'],
            'Ford': ['Focus', 'Kuga', 'Mustang Mach-E'],
            'Hyundai': ['i30', 'Tucson', 'Kona', 'IONIQ'],
            'Kia': ['Ceed', 'Sportage', 'e-Niro'],
            'Mazda': ['3', 'CX-5', 'MX-30'],
            'Volvo': ['V60', 'XC40', 'XC60'],
            'Peugeot': ['208', '3008', 'e-208']
        }
        
        model = random.choice(models.get(brand, ['Unknown']))
        
        # Different countries with different price ranges
        country = random.choice(['denmark', 'germany', 'sweden', 'norway', 'poland', 'france'])
        
        # Price ranges by country (to create realistic arbitrage opportunities)
        price_ranges = {
            'denmark': (300000, 600000),
            'germany': (250000, 500000),
            'sweden': (280000, 550000),
            'norway': (350000, 650000),
            'poland': (200000, 400000),
            'france': (270000, 520000)
        }
        
        price_range = price_ranges.get(country, (250000, 500000))
        price = random.randint(price_range[0], price_range[1])
        
        # Adjust price for electric vehicles (usually more expensive)
        fuel_type = random.choice(['Diesel', 'Petrol', 'El', 'Hybrid'])
        if fuel_type == 'El':
            price = int(price * 1.2)  # 20% premium for electric
        
        # More recent years for electric vehicles
        if fuel_type == 'El':
            year = random.randint(2018, 2023)
        else:
            year = random.randint(2015, 2023)
        
        # Lower mileage for newer cars
        max_mileage = (2023 - year) * 20000
        mileage = random.randint(5000, max(10000, max_mileage))
        
        # Create car object with more fields
        car_data = {
            'brand': brand,
            'model': model,
            'cash_price': price,
            'country': country,
            'year': year,
            'mileage': mileage,
            'fuel_type': fuel_type,
            'color': random.choice(['Black', 'White', 'Silver', 'Blue', 'Red', 'Grey']),
            'scraped_at': datetime.utcnow(),
            'source_url': f"https://www.{source_domains.get(country, 'example.com')}/cars/{brand.lower()}/{model.lower().replace(' ', '-')}-{random.randint(10000, 99999)}"
        }
        
        # Add EV-specific data for electric vehicles
        if fuel_type == 'El':
            car_data['battery_capacity'] = random.choice([40, 58, 64, 75, 80, 100])
            car_data['range_km'] = int(car_data['battery_capacity'] * random.uniform(4, 6))
            car_data['energy_consumption'] = random.uniform(15, 22)
        
        # Add some equipment
        equipment_options = [
            'Navigation', 'Leather seats', 'Sunroof', 'Parking sensors', 
            'Backup camera', 'Heated seats', 'Bluetooth', 'Cruise control',
            'Climate control', 'LED headlights', 'Alloy wheels', 'Keyless entry',
            'Apple CarPlay', 'Android Auto', 'Wireless charging', 'Premium sound system'
        ]
        
        # Add 3-8 random equipment items
        car_data['equipment'] = random.sample(equipment_options, random.randint(3, 8))
        
        cars.append(car_data)
    
    return cars

class SimpleScraper:
    def __init__(self):
        self.proxy = get_brightdata_proxy()
        
    async def scrape_urls(self, urls, country, max_cars=10):
        """Scrape car listings from the provided URLs"""
        logger.info(f"Starting simple scraper for {country} with {len(urls)} URLs (max {max_cars} cars)")
        
        # Create a session with the proxy if available
        session_kwargs = {}
        if self.proxy:
            logger.info("Using BrightData proxy")
            session_kwargs["proxy"] = self.proxy["http"]
        
        async with aiohttp.ClientSession(**session_kwargs) as session:
            for url in urls:
                try:
                    logger.info(f"Scraping URL: {url}")
                    
                    # Make the request
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"Failed to fetch {url}: {response.status}")
                            continue
                        
                        html = await response.text()
                        
                        # Parse the HTML
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract car data (simplified example)
                        car_elements = soup.select('.car-listing')[:max_cars]
                        
                        for car_element in car_elements:
                            # Extract car details
                            car_data = {
                                "brand": car_element.select_one('.brand').text.strip(),
                                "model": car_element.select_one('.model').text.strip(),
                                "year": int(car_element.select_one('.year').text.strip()),
                                "price": float(car_element.select_one('.price').text.strip().replace('$', '').replace(',', '')),
                                "source_url": car_element.select_one('a')['href'],
                                "country": country,
                                "created_at": datetime.utcnow()
                            }
                            
                            # Save to database (simplified)
                            logger.info(f"Extracted car: {car_data['brand']} {car_data['model']}")
                            
                except Exception as e:
                    logger.error(f"Error scraping {url}: {str(e)}")
        
        logger.info(f"Simple scraper completed for {country}")

async def main():
    """Main scraper function"""
    logger.info("Starting simple car scraper")
    start_time = time.time()
    
    # Initialize database
    db = MongoDB()
    await db.init_db()
    
    try:
        total_cars = 0
        target_count = 500
        
        # Generate dummy data in batches
        while total_cars < target_count:
            batch_size = min(50, target_count - total_cars)
            logger.info(f"Generating batch of {batch_size} cars")
            
            # Generate a batch of dummy cars
            cars = generate_dummy_cars(batch_size)
            
            # Store cars
            if cars:
                stored = await db.store_listings(cars)
                logger.info(f"Stored {stored} cars")
                total_cars += stored
            
            # Add a small delay between batches
            await asyncio.sleep(0.5)
        
        # Log results
        elapsed_time = time.time() - start_time
        logger.info(f"Data generation completed in {elapsed_time:.2f} seconds")
        logger.info(f"Total cars generated: {total_cars}")
        
        return total_cars > 0
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return False
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main()) 