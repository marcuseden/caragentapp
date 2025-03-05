import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connection():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://www.bilbasen.dk/brugt/bil') as response:
                logger.info(f"Status: {response.status}")
                text = await response.text()
                logger.info(f"Retrieved {len(text)} characters")
                return text
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None

async def main():
    result = await test_connection()
    if result:
        logger.info("Connection successful!")
    else:
        logger.error("Connection failed!")

if __name__ == "__main__":
    asyncio.run(main()) 