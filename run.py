import socket
import uvicorn
import os
import sys

# Add the parent directory to the path so we can import modules correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def find_free_port(start_port=5555, max_port=5585):
    """Find a free port between start_port and max_port"""
    for port in range(start_port, max_port + 1):
        try:
            # Try to create a socket with the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    raise OSError("No free ports found in range")

if __name__ == "__main__":
    try:
        port = find_free_port()
        print(f"Starting web server on port {port}...")
        print(f"Open your browser at: http://127.0.0.1:{port}")
        
        uvicorn.run(
            "src.web_app:app",
            host="127.0.0.1",
            port=port,
            reload=False
        )
    except Exception as e:
        print(f"Error starting server: {e}") 