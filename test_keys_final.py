
import os
import requests
import json
from dotenv import load_dotenv

def test_keys():
    load_dotenv('backend/.env')
    keys_str = os.environ.get("GEMINI_API_KEYS", "")
    if not keys_str:
        print("No GEMINI_API_KEYS found in backend/.env")
        return
    
    keys = [k.strip().strip('"') for k in keys_str.split(",") if k.strip()]
    print(f"Found {len(keys)} keys.\n")

    for i, key in enumerate(keys):
        print(f"[{i}] Testing key: {key[:10]}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        headers = {'Content-Type': 'application/json'}
        payload = {'contents': [{'parts':[{'text': 'hi'}]}]}
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            if response.status_code == 200:
                print(f"    SUCCESS: {response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No text response')}")
            else:
                print(f"    FAILED: Status {response.status_code}")
                print(f"    Body: {response.text}")
        except Exception as e:
            print(f"    ERROR: {e}")

if __name__ == "__main__":
    test_keys()
