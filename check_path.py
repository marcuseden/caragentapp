import sys
import os

print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("Python path:")
for path in sys.path:
    print(f"  - {path}") 