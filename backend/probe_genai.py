
import os
import traceback

try:
    import google.generativeai as genai
    print("SUCCESS: google.generativeai imported")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found")
    else:
        genai.configure(api_key=api_key)
        print("Configured GenAI")
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content="Hello world",
                task_type="retrieval_document"
            )
            if 'embedding' in result:
                print("SUCCESS: Embedding generated")
            else:
                print(f"FAILURE: No embedding in result: {result}")
        except Exception as e:
            print(f"FAILURE during embedding: {e}")
            traceback.print_exc()
except Exception as e:
    print(f"FAILURE: Import failed: {e}")
    traceback.print_exc()
