import asyncio
from test_scraper import parse_car_details, scrape_cars
from bs4 import BeautifulSoup
import aiohttp
from config import get_proxy_url
from db import MongoDB
import logging

logger = logging.getLogger(__name__)

async def test_single_car():
    # Test URL - a specific car from bilbasen.dk
    url = "https://www.bilbasen.dk/brugt/bil/nissan/ariya/87-advance-5d/6394005"
    
    proxy_url = get_proxy_url('denmark')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy=proxy_url, headers=headers, ssl=False) as response:
            if response.status == 200:
                html = await response.text()
                
                # Debug the HTML structure
                logger.debug(f"Received HTML length: {len(html)}")
                logger.debug("First 1000 characters of HTML:")
                logger.debug(html[:1000])
                
                soup = BeautifulSoup(html, 'lxml')
                car_data = await parse_car_details(soup, url)
                
                if car_data:
                    # Store in MongoDB
                    db = MongoDB()
                    await db.init_db()
                    await db.store_listings([car_data])
                    await db.close()
                    
                    print("\nCar data collected:")
                    for key, value in sorted(car_data.items()):
                        print(f"{key}: {value}")
                else:
                    print("\nFailed to parse car data")
            else:
                print(f"Failed to fetch page: {response.status}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(test_single_car()) 