import asyncio
import logging
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the scraper
from src.large_scale_scraper import main as scraper_main

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the large-scale car scraper")
    parser.add_argument("--count", type=int, default=10000, help="Number of cars to scrape")
    args = parser.parse_args()
    
    print(f"Starting large-scale car scraper to collect {args.count} cars...")
    asyncio.run(scraper_main(args.count))
    print("Scraping completed!") 