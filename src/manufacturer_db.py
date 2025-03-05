"""
Module for accessing manufacturer specifications for different car models.
This can be expanded to fetch data from external APIs or a local database.
"""

# Sample manufacturer database with specifications for common models
MANUFACTURER_DB = {
    'Tesla': {
        'Model 3': {
            'body_type': 'Sedan',
            'transmission': 'Automatic',
            'drive_type': 'Rear-wheel drive / All-wheel drive',
            'power': '283-450 HP',
            'battery_capacity': '60-82 kWh',
            'range_km': '430-580 km',
            'charging_speed_dc': '170-250 kW',
            'charging_time': '25-35 min (10-80%)'
        },
        'Model Y': {
            'body_type': 'SUV',
            'transmission': 'Automatic',
            'drive_type': 'Rear-wheel drive / All-wheel drive',
            'power': '299-450 HP',
            'battery_capacity': '60-82 kWh',
            'range_km': '410-530 km',
            'charging_speed_dc': '170-250 kW',
            'charging_time': '25-35 min (10-80%)'
        },
        'Model S': {
            'body_type': 'Sedan',
            'transmission': 'Automatic',
            'drive_type': 'All-wheel drive',
            'power': '670-1020 HP',
            'battery_capacity': '95-100 kWh',
            'range_km': '600-650 km',
            'charging_speed_dc': '250 kW',
            'charging_time': '25-30 min (10-80%)'
        },
        'Model X': {
            'body_type': 'SUV',
            'transmission': 'Automatic',
            'drive_type': 'All-wheel drive',
            'power': '670-1020 HP',
            'battery_capacity': '95-100 kWh',
            'range_km': '560-580 km',
            'charging_speed_dc': '250 kW',
            'charging_time': '25-30 min (10-80%)'
        }
    },
    # Add more manufacturers and models as needed
}

def get_manufacturer_specs(brand: str, model: str):
    """
    Get manufacturer specifications for a specific car model.
    
    Args:
        brand: Car brand/make
        model: Car model
        
    Returns:
        Dictionary with specifications or None if not found
    """
    brand = brand.strip()
    model = model.strip()
    
    # Try exact match
    if brand in MANUFACTURER_DB and model in MANUFACTURER_DB[brand]:
        return MANUFACTURER_DB[brand][model]
    
    # Try case-insensitive match
    for db_brand, models in MANUFACTURER_DB.items():
        if db_brand.lower() == brand.lower():
            for db_model, specs in models.items():
                if db_model.lower() == model.lower():
                    return specs
    
    # Try partial match for model
    for db_brand, models in MANUFACTURER_DB.items():
        if db_brand.lower() == brand.lower():
            for db_model, specs in models.items():
                if db_model.lower() in model.lower() or model.lower() in db_model.lower():
                    return specs
    
    return None 