import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.currency_service import get_currency_service

async def main():
    # Get the currency service
    service = await get_currency_service()
    
    # Print current rates
    print(f"Exchange rates last updated: {service.last_updated}")
    print("\nCurrent rates from DKK:")
    for currency, rate in sorted(service.rates.items()):
        if currency in ['SEK', 'EUR', 'USD', 'GBP', 'NOK']:
            print(f"  {currency}: {rate:.4f}")
    
    # Test some conversions
    test_amounts = [1000, 5000, 10000, 50000, 100000]
    print("\nConversion examples (DKK to SEK):")
    for amount in test_amounts:
        sek_amount = service.convert(amount, 'DKK', 'SEK')
        print(f"  {amount:,} DKK = {sek_amount:,.2f} SEK")
    
    print("\nConversion examples (SEK to DKK):")
    for amount in test_amounts:
        dkk_amount = service.convert(amount, 'SEK', 'DKK')
        print(f"  {amount:,} SEK = {dkk_amount:,.2f} DKK")

if __name__ == "__main__":
    asyncio.run(main()) 