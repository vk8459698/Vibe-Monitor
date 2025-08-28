# traffic_generator.py
import requests
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000"

endpoints = [
    "/",
    "/health", 
    "/slow",
    "/error",
    "/users/1",
    "/users/2",
    "/users/3"
]

def make_request():
    """Make a single request to a random endpoint"""
    endpoint = random.choice(endpoints)
    url = f"{BASE_URL}{endpoint}"
    
    try:
        response = requests.get(url, timeout=10)
        print(f" {endpoint} -> {response.status_code}")
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f" {endpoint} -> Error: {e}")
        return None

def generate_traffic(duration=60, requests_per_second=2):
    """Generate traffic for specified duration"""
    print(f" Starting traffic generation for {duration} seconds")
    print(f" Rate: ~{requests_per_second} requests/second")
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        while time.time() - start_time < duration:
            # Submit requests
            futures = []
            for _ in range(requests_per_second):
                future = executor.submit(make_request)
                futures.append(future)
                time.sleep(1/requests_per_second)  # Spread requests evenly
            
            # Wait for completion (optional)
            for future in futures:
                future.result()
    
    print(" Traffic generation completed!")

def burst_traffic():
    """Generate burst traffic for demos"""
    print(" Generating burst traffic...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for _ in range(50):  # 50 concurrent requests
            future = executor.submit(make_request)
            futures.append(future)
        
        # Wait for all to complete
        for future in futures:
            future.result()
    
    print(" Burst completed!")

if __name__ == "__main__":
    print(" FastAPI Traffic Generator")
    print("=" * 40)
    
    # Wait for service to be ready
    print(" Waiting for service to be ready...")
    while True:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print(" Service is ready!")
                break
        except:
            print(" Service not ready, waiting...")
            time.sleep(2)
    
    # Generate continuous traffic
    try:
        while True:
            print("\n Starting traffic cycle...")
            
            # Normal traffic for 30 seconds
            generate_traffic(duration=30, requests_per_second=2)
            
            # Burst traffic
            burst_traffic()
            
            # Rest period
            print(" Resting for 10 seconds...")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n Stopping traffic generator...")
