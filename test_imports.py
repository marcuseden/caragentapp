print("Testing imports...")

try:
    import fastapi
    print("✓ FastAPI imported successfully")
except ImportError as e:
    print(f"✗ Failed to import FastAPI: {e}")

try:
    import uvicorn
    print("✓ Uvicorn imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Uvicorn: {e}")

try:
    import motor
    print("✓ Motor imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Motor: {e}")

try:
    import aiohttp
    print("✓ AIOHTTP imported successfully")
except ImportError as e:
    print(f"✗ Failed to import AIOHTTP: {e}")

try:
    from src.web_app import app
    print("✓ Web app imported successfully")
except Exception as e:
    print(f"✗ Failed to import web app: {e}")

print("Import test complete") 