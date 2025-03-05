import asyncio
import logging
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the scraper
from src.simple_scraper import main as scraper_main

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    print("Starting simple car scraper to collect 500 cars...")
    asyncio.run(scraper_main())
    print("Scraping completed!") 