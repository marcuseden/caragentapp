import aiohttp
import asyncio
import logging
import json
import os
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
EXCHANGE_RATES_FILE = "exchange_rates.json"
EXCHANGE_RATE_TTL = 24  # hours

# Fallback exchange rates (relative to DKK)
FALLBACK_RATES = {
    "DKK": 1.0,
    "SEK": 1.4123,  # 1 DKK = 1.4123 SEK
    "EUR": 0.1341,  # 1 DKK = 0.1341 EUR
    "USD": 0.1456,  # 1 DKK = 0.1456 USD
    "GBP": 0.1147,  # 1 DKK = 0.1147 GBP
    "NOK": 1.5321,  # 1 DKK = 1.5321 NOK
    "PLN": 0.5742,  # 1 DKK = 0.5742 PLN
}

class CurrencyService:
    """Service for currency conversion"""
    
    def __init__(self):
        self.rates = {}
        self.last_updated = None
        self.base_currency = "DKK"  # Danish Krone as base
        self.using_fallback = True
    
    async def initialize(self):
        """Initialize the currency service"""
        logger.info("Initializing currency service")
        
        # Try to load cached rates first
        self._load_cached_rates()
        
        # If rates are outdated or missing, fetch new ones
        if not self.rates or self._is_cache_outdated():
            success = await self.update_rates()
            
            # If update failed, use fallback rates
            if not success:
                logger.warning("Using fallback exchange rates")
                self.rates = FALLBACK_RATES.copy()
                self.last_updated = datetime.now()
                self.using_fallback = True
        
        # Log available currencies
        logger.info(f"Available currencies: {', '.join(sorted(self.rates.keys()))}")
        
        # Log some example rates
        for currency in ['SEK', 'EUR', 'USD']:
            if currency in self.rates:
                logger.info(f"1 DKK = {self.rates[currency]:.4f} {currency}")
    
    def _load_cached_rates(self):
        """Load exchange rates from cache file"""
        try:
            if os.path.exists(EXCHANGE_RATES_FILE):
                with open(EXCHANGE_RATES_FILE, 'r') as f:
                    data = json.load(f)
                    self.rates = data.get('rates', {})
                    self.last_updated = datetime.fromisoformat(data.get('timestamp'))
                    logger.info(f"Loaded cached exchange rates from {self.last_updated}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error loading cached exchange rates: {str(e)}")
            return False
    
    def _save_cached_rates(self):
        """Save exchange rates to cache file"""
        try:
            with open(EXCHANGE_RATES_FILE, 'w') as f:
                json.dump({
                    'rates': self.rates,
                    'timestamp': self.last_updated.isoformat(),
                    'using_fallback': self.using_fallback
                }, f)
            logger.info("Saved exchange rates to cache")
            return True
        except Exception as e:
            logger.error(f"Error saving exchange rates to cache: {str(e)}")
            return False
    
    def _is_cache_outdated(self):
        """Check if cached rates are outdated"""
        if not self.last_updated:
            return True
        
        cache_age = datetime.now() - self.last_updated
        return cache_age > timedelta(hours=EXCHANGE_RATE_TTL)
    
    async def update_rates(self, force=False):
        """Update currency exchange rates"""
        try:
            logger.info("Fetching exchange rates from API")
            
            # Try multiple APIs in case one fails
            apis = [
                "https://open.er-api.com/v6/latest/DKK",
                "https://api.exchangerate-api.com/v4/latest/DKK",
                "https://api.exchangeratesapi.io/latest?base=DKK"
            ]
            
            for api_url in apis:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(api_url, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                # Different APIs have different response formats
                                if "rates" in data:
                                    self.rates = data["rates"]
                                    self.rates[self.base_currency] = 1.0  # Ensure base currency is included
                                    self.last_updated = datetime.now()
                                    self.using_fallback = False
                                    self._save_cached_rates()
                                    logger.info(f"Updated exchange rates from {api_url}")
                                    return True
                except Exception as api_error:
                    logger.warning(f"Failed to fetch from {api_url}: {str(api_error)}")
                    continue
            
            # If we get here, all APIs failed
            logger.error("All exchange rate APIs failed")
            return False
            
        except Exception as e:
            logger.error(f"Error updating exchange rates: {str(e)}")
            return False
    
    def convert(self, amount, from_currency="DKK", to_currency="SEK"):
        """Convert amount from one currency to another"""
        if not amount or not isinstance(amount, (int, float)):
            return None
        
        # If currencies are the same, no conversion needed
        if from_currency == to_currency:
            return amount
        
        # Ensure we have both currencies
        if from_currency not in self.rates:
            logger.warning(f"No exchange rate found for {from_currency}")
            return amount
            
        if to_currency not in self.rates:
            logger.warning(f"No exchange rate found for {to_currency}")
            return amount
        
        # For our base currency (DKK), we can directly use the rate
        if from_currency == self.base_currency:
            return amount * self.rates[to_currency]
        
        # For other currencies, convert to base first, then to target
        # Convert to base currency first
        in_base = amount / self.rates[from_currency]
        # Then convert to target currency
        return in_base * self.rates[to_currency]
    
    def get_formatted_rate(self, from_currency="DKK", to_currency="SEK"):
        """Get formatted exchange rate for display"""
        if from_currency in self.rates and to_currency in self.rates:
            if from_currency == self.base_currency:
                rate = self.rates[to_currency]
            else:
                rate = self.rates[to_currency] / self.rates[from_currency]
                
            return f"1 {from_currency} = {rate:.4f} {to_currency}"
        return f"Rate unavailable"
    
    def get_status(self):
        """Get status information about the currency service"""
        return {
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "using_fallback": self.using_fallback,
            "available_currencies": list(sorted(self.rates.keys())),
            "example_rates": {
                "SEK": self.rates.get("SEK"),
                "EUR": self.rates.get("EUR"),
                "USD": self.rates.get("USD")
            }
        }

# Singleton instance
currency_service = CurrencyService()

async def get_currency_service():
    """Get the currency service instance, initializing if needed"""
    if not currency_service.rates:
        await currency_service.initialize()
    return currency_service

# Test function
async def test_currency_service():
    service = await get_currency_service()
    print(f"Exchange rates last updated: {service.last_updated}")
    print(f"Using fallback rates: {service.using_fallback}")
    
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
    asyncio.run(test_currency_service()) 