import asyncio
import argparse
import logging
import os
import sys

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import the scraper
from src.simple_scraper import main as scraper_main
from simple_scraper import SimpleScraper
from src.config import URLS

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the simple scraper')
    parser.add_argument('--country', type=str, default='denmark', 
                        help='Country to scrape (default: denmark)')
    args = parser.parse_args()
    
    # Get URLs for the specified country
    country = args.country.lower()
    if country not in URLS:
        print(f"Error: Country '{country}' not found in URLS config")
        return
    
    urls = URLS[country]
    print(f"Running simple scraper for {country} with URLs: {urls}")
    
    # Run the scraper
    scraper = SimpleScraper()
    await scraper.scrape_urls(urls, country)

if __name__ == "__main__":
    asyncio.run(main()) 