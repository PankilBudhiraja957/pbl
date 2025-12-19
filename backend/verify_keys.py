
import os
import google.generativeai as genai
from dotenv import load_dotenv

def verify_keys():
    load_dotenv()
    keys_str = os.environ.get("GEMINI_API_KEYS", "")
    if not keys_str:
        single_key = os.environ.get("GEMINI_API_KEY")
        keys = [single_key] if single_key else []
    else:
        keys = [k.strip().strip('"') for k in keys_str.split(",") if k.strip()]

    print(f"Found {len(keys)} keys to verify.\n")

    for i, key in enumerate(keys):
        print(f"[{i}] Key: {key[:10]}...{key[-5:]}")
        genai.configure(api_key=key)
        
        # Test models to try
        test_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash-exp']
        
        success = False
        for model_name in test_models:
            try:
                model = genai.GenerativeModel(model_name)
                # Minimal call
                response = model.generate_content("Hi", generation_config={"max_output_tokens": 5})
                print(f"    Status: VALID (Model: {model_name})")
                success = True
                break
            except Exception as e:
                err = str(e).lower()
                if "not_found" in err or "404" in err:
                    continue # Try next model
                
                print(f"    Status: FAILED for {model_name}")
                print(f"    Error: {str(e)[:200]}")
                break
        
        if not success:
             print("    Result: No valid models found for this key or key is invalid.")
    
    print("\nVerification complete.")

if __name__ == "__main__":
    verify_keys()
