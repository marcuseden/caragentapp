#!/bin/bash
echo "Stopping any running instances..."
pkill -f "python3 main.py" || true
echo "Starting the application..."
python3 main.py 