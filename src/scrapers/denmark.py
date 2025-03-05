import aiohttp
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

async def fetch_complete_car_info(url):
    """
    Fetch complete car information from a Danish car listing
    
    Args:
        url (str): The source URL of the car listing
        
    Returns:
        dict: Complete car information including contact details and images
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch {url}: HTTP {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract all available information
                result = {
                    "images": [],
                    "contact_info": {},
                    "additional_details": {},
                    "full_description": ""
                }
                
                # Extract images
                image_elements = soup.select('.gallery-image img, .carousel-item img')
                for img in image_elements:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        if not src.startswith('http'):
                            # Handle relative URLs
                            if src.startswith('/'):
                                base_url = '/'.join(url.split('/')[:3])  # http(s)://domain.com
                                src = base_url + src
                            else:
                                src = url.rsplit('/', 1)[0] + '/' + src
                        
                        result["images"].append(src)
                
                # Extract contact information
                contact_section = soup.select_one('.contact-info, .seller-info')
                if contact_section:
                    # Extract dealer name
                    dealer_name = contact_section.select_one('.dealer-name, .seller-name')
                    if dealer_name:
                        result["contact_info"]["name"] = dealer_name.text.strip()
                    
                    # Extract phone
                    phone = contact_section.select_one('.phone, [href^="tel:"]')
                    if phone:
                        result["contact_info"]["phone"] = phone.text.strip() or phone.get('href', '').replace('tel:', '')
                    
                    # Extract email
                    email = contact_section.select_one('.email, [href^="mailto:"]')
                    if email:
                        result["contact_info"]["email"] = email.text.strip() or email.get('href', '').replace('mailto:', '')
                    
                    # Extract address
                    address = contact_section.select_one('.address')
                    if address:
                        result["contact_info"]["address"] = address.text.strip()
                
                # Extract full description
                description = soup.select_one('.description, .car-description')
                if description:
                    result["full_description"] = description.text.strip()
                
                # Extract additional details
                details_section = soup.select('.car-details li, .specifications tr')
                for detail in details_section:
                    # Try to extract key-value pairs
                    key_el = detail.select_one('.key, th')
                    value_el = detail.select_one('.value, td')
                    
                    if key_el and value_el:
                        key = key_el.text.strip().rstrip(':')
                        value = value_el.text.strip()
                        result["additional_details"][key] = value
                
                return result
                
    except Exception as e:
        logger.error(f"Error fetching complete car info from {url}: {str(e)}")
        return None 