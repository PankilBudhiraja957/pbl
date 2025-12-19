
import sys
import os

# Ensure backend directory is in path
sys.path.append(os.getcwd())

from agents.memory import AgentMemory

def check_brain():
    print("Initializing AgentMemory...")
    mem = AgentMemory()
    
    if not mem.knowledge_collection:
        print("ERROR: Knowledge collection not available (ChromaDB failed?)")
        return

    count = mem.knowledge_collection.count()
    print(f"Knowledge Collection Count: {count}")
    
    if count == 0:
        print("WARNING: Brain is empty! Attempting to add dummy data...")
        try:
            success = mem.add_knowledge("Test spicy food", {"name": "Test Item"})
            if success:
                print("SUCCESS: Added dummy data.")
            else:
                print("FAILURE: Could not add dummy data.")
        except Exception as e:
            print(f"CRITICAL FAILURE during add: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Brain has data. Querying 'spicy'...")
        results = mem.query_knowledge("spicy")
        for res in results:
            print(f"- {res['meta'].get('name')}: {res['content'][:50]}...")

if __name__ == "__main__":
    check_brain()
