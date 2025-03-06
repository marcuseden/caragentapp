import os

# BrightData configuration
BRIGHTDATA_CONFIG = {
    "username": os.environ.get("BRIGHT_USERNAME", "brd-customer-hl_bb142c5f-zone-denmark"),
    "password": os.environ.get("BRIGHT_PASSWORD", "syw18ezxx7kg"),
    "host": os.environ.get("BRIGHT_HOST", "brd.superproxy.io"),
    "port": int(os.environ.get("BRIGHT_PORT", "33335"))
}

def get_brightdata_proxy():
    """Get BrightData proxy configuration"""
    config = BRIGHTDATA_CONFIG
    
    if not config["username"] or not config["password"] or not config["host"]:
        return None
    
    proxy_url = f"http://{config['username']}:{config['password']}@{config['host']}:{config['port']}"
    return {
        "http": proxy_url,
        "https": proxy_url
    } 