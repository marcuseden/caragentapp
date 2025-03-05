from typing import List

URLS = {
    'denmark': [
        'https://www.bilbasen.dk/brugt/bil',
        'https://www.dba.dk/biler/biler/'
    ],
    'norway': [
        'https://www.finn.no/car/used/search.html',
        'https://www.autodb.no/brukte-biler/'
    ],
    'sweden': [
        'https://www.blocket.se/annonser/hela_sverige/fordon/bilar',
        'https://www.bilweb.se/sok/bilar',
        'https://www.kvd.se/sok/bilar'
    ],
    'germany': [
        'https://www.autoscout24.com/lst/',
        'https://www.mobile.de/?lang=en'
    ],
    'portugal': [
        'https://www.standvirtual.com/carros/'
    ],
    'poland': [
        'https://www.olx.pl/motoryzacja/samochody/'
    ],
    'france': [
        'https://www.leboncoin.fr/voitures/offres/'
    ],
    'italy': [
        'https://www.subito.it/annunci-italia/vendita/auto/'
    ]
}

# MongoDB configuration
MONGODB_URI = "mongodb://localhost:27017"
DB_NAME = "car_listings"
COLLECTION_NAME = "listings"

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

def get_proxy_url(country):
    return None 