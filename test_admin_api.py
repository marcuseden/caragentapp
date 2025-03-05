import requests
import json

# Base URL for the admin API
BASE_URL = "http://127.0.0.1:5559"

def test_endpoint(endpoint, method="GET"):
    """Test an API endpoint and print the response"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\nTesting {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        else:
            response = requests.post(url)
        
        print(f"Status: {response.status_code}")
        
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
        except:
            print(f"Response text: {response.text[:200]}...")
    
    except Exception as e:
        print(f"Error: {str(e)}")

# Test all endpoints
if __name__ == "__main__":
    print("Testing Admin API Endpoints")
    print("==========================")
    
    # Test GET endpoints
    test_endpoint("/stats")
    test_endpoint("/test")
    
    # Test POST endpoints
    test_endpoint("/check-invalid-urls", "POST")
    test_endpoint("/update-rates", "POST")
    test_endpoint("/remove-unverified", "POST")
    test_endpoint("/remove-invalid-urls", "POST") 