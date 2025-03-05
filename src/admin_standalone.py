import uvicorn
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Import the admin app
from src.admin import admin_app

# Setup static files for standalone mode
from fastapi.staticfiles import StaticFiles
static_dir = os.path.join(project_root, "static")
admin_app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    print("Starting admin server...")
    print(f"Admin UI available at: http://127.0.0.1:5559/")
    print(f"API test page available at: http://127.0.0.1:5559/test-api")
    uvicorn.run(
        admin_app,
        host="127.0.0.1",
        port=5559,
        log_level="debug"
    ) 