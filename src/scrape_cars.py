import asyncio
import argparse
import logging
from car_scraper import CarScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_scraper(args):
    """Run the car scraper with the specified arguments"""
    # Create the scraper
    scraper = CarScraper(
        max_cars=args.max_cars,
        delay_range=(args.min_delay, args.max_delay)
    )
    
    # Run the scraper
    cars_saved = await scraper.scrape_cars(args.urls)
    logger.info(f"Saved {cars_saved} new cars to the database")

def main():
    """Parse command-line arguments and run the scraper"""
    parser = argparse.ArgumentParser(description='Scrape car listings and details')
    
    parser.add_argument('urls', nargs='+', help='URLs of car listing pages to scrape')
    parser.add_argument('--max-cars', type=int, default=1000, help='Maximum number of cars to scrape')
    parser.add_argument('--min-delay', type=float, default=1.0, help='Minimum delay between requests (seconds)')
    parser.add_argument('--max-delay', type=float, default=3.0, help='Maximum delay between requests (seconds)')
    
    args = parser.parse_args()
    
    # Run the scraper
    asyncio.run(run_scraper(args))

if __name__ == "__main__":
    main() 