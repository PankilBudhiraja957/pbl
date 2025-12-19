import requests
import json
import time

# Configuration
BASE_URL = "http://127.0.0.1:5000"
USERNAME = "admin@gmail.com"
PASSWORD = "admin123"

def test_order_error():
    session = requests.Session()
    
    # Wait for server
    print("Waiting for server...")
    time.sleep(5)
    
    # 1. Login
    print("Logging in...")
    try:
        response = session.post(f"{BASE_URL}/api/auth/login", json={"username": USERNAME, "password": PASSWORD})
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # 2. Trigger Error
    print("\nSending 'hi order paneer tikka for me'...")
    chat_payload = {"message": "hi order paneer tikka for me"}
    response = session.post(f"{BASE_URL}/api/ai/chat", json=chat_payload)
    print(f"Status Code: {response.status_code}")
    try:
        print("Reply:", json.dumps(response.json(), indent=2))
    except:
        print("Reply text:", response.text)

if __name__ == "__main__":
    test_order_error()
