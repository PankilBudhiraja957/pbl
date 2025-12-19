import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# keys from backend directory (simulated loading)
# We will just try one key from the env
# I'll rely on the backend's key manager logic or just read the ENV directly if I can view it?
# The KeyManager reads GEMINI_API_KEYS. 

# Let's try to import KeyManager from backend.
import sys
sys.path.append('backend')
from key_manager import KeyManager

def test_models():
    km = KeyManager()
    key = km.get_current_key()
    print(f"Using key: ...{key[-5:] if key else 'None'}")
    
    if not key:
        print("No API Key found.")
        return

    genai.configure(api_key=key)

    models_to_test = ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-2.5-flash"]
    
    for model_name in models_to_test:
        print(f"\nTesting model: {model_name}...")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hello, this is a test.")
            print(f"SUCCESS: {model_name} responded: {response.text}")
        except Exception as e:
            print(f"FAILED: {model_name} error: {e}")

if __name__ == "__main__":
    test_models()
