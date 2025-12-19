import google.generativeai as genai
import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add current dir to path to import key_manager if needed, 
# but actually we can just read the key from env directly for this test 
# if KeyManager relies on os.environ anyway.

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from key_manager import KeyManager

def list_gemini_models():
    km = KeyManager()
    key = km.get_current_key()
    
    if not key:
        print("Error: No GEMINI_API_KEY found in environment.")
        return

    print(f"Using API Key: ...{key[-5:]}")
    genai.configure(api_key=key)

    print("\nListing available models...")
    try:
        with open("available_models.txt", "w") as f:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"- {m.name}")
                    f.write(f"{m.name}\n")
        print("Models written to available_models.txt")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_gemini_models()
