import asyncio
from scraper import CarScraper
from analysis import PriceAnalyzer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Run the scraper
    scraper = CarScraper()
    await scraper.run()
    
    # Run analysis
    analyzer = PriceAnalyzer()
    
    # Get general price statistics
    stats = analyzer.get_price_statistics()
    logger.info("Price statistics by country:")
    logger.info(stats)
    
    # Find arbitrage opportunities
    opportunities = analyzer.find_arbitrage_opportunities(min_price_diff=0.2)
    logger.info("Found arbitrage opportunities:")
    for opp in opportunities:
        logger.info(f"Make: {opp['make']}, Model: {opp['model']}, Year: {opp['year']}")
        logger.info(f"Price difference: {opp['price_difference']*100:.1f}%")
        logger.info("Prices by country:")
        for price in opp['prices']:
            logger.info(f"  {price['country']}: {price['price']}")

if __name__ == "__main__":
    asyncio.run(main()) 