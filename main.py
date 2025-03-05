import uvicorn
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import the web app
from web_app import app

if __name__ == "__main__":
    print("Starting web server...")
    uvicorn.run(app, host="127.0.0.1", port=5557, reload=True, log_level="debug", access_log=True) 