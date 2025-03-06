from typing import List
import os

# URLs for different countries
URLS = {
    "denmark": ["https://www.bilbasen.dk/brugt/bil"],
    "sweden": ["https://www.blocket.se/annonser/hela_sverige/fordon/bilar"],
    "norway": ["https://www.finn.no/car/used/search.html"],
    "germany": ["https://www.mobile.de/"],
    "portugal": ["https://www.standvirtual.com/"],
    "poland": ["https://www.otomoto.pl/"],
    "france": ["https://www.lacentrale.fr/"],
    "italy": ["https://www.automobile.it/"]
}

# MongoDB configuration
# Use environment variables for sensitive information
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "car_database")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "cars")

# Rate limiting settings
REQUESTS_PER_SECOND = 0.2  # 5 seconds between requests
CONCURRENT_REQUESTS = 3

# Bright Data settings
BRIGHT_DATA_USERNAME = "brd-customer-hl_bb142c5f-zone-denmark"  # Exact username from curl
BRIGHT_DATA_PASSWORD = "syw18ezxx7kg"
BRIGHT_DATA_PORT = "33335"

# Country code mapping
BRIGHT_DATA_COUNTRY_MAP = {
    'denmark': 'dk',
    'norway': 'no',
    'sweden': 'se',
    'germany': 'de',
    'portugal': 'pt',
    'poland': 'pl',
    'france': 'fr',
    'italy': 'it'
}

# Proxy configuration (optional)
def get_proxy_url(country):
    return None

# BrightData configuration
BRIGHTDATA_CONFIG = {
    "username": os.environ.get("BRIGHT_USERNAME", "brd-customer-hl_bb142c5f-zone-denmark"),
    "password": os.environ.get("BRIGHT_PASSWORD", "syw18ezxx7kg"),
    "host": os.environ.get("BRIGHT_HOST", "brd.superproxy.io"),
    "port": int(os.environ.get("BRIGHT_PORT", "33335"))
} 