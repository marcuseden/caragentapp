import uvicorn

if __name__ == "__main__":
    print("Starting test server...")
    uvicorn.run("src.web_app:app", host="127.0.0.1", port=5557) 