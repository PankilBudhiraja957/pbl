
import os
import sys
import csv
import json
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from agents.memory import AgentMemory
import google.generativeai as genai

def seed_and_test_rag():
    print("--- 1. Initializing AgentMemory (Persistent) ---")
    memory = AgentMemory()
    
    # Check count
    count = memory.get_knowledge_count()
    print(f"Current Knowledge Base Size: {count}")
    
    if count == 0:
        print("--- 2. Seeding Knowledge Base from menu.csv ---")
        csv_path = os.path.join(os.path.dirname(__file__), 'menu.csv')
        if not os.path.exists(csv_path):
            print(f"ERROR: {csv_path} not found.")
            return

        items_added = 0
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Construct rich text for embedding
                text = f"{row.get('name')}: {row.get('description')}. Ingredients: {row.get('ingredients')}. Diet: {row.get('diet')}. Category: {row.get('category')}."
                
                meta = {
                    "id": str(row.get('id', items_added)), # Use index if ID missing
                    "name": row.get('name') or "", 
                    "category": row.get('category') or "", 
                    "diet": row.get('diet') or ""
                }
                
                success = memory.add_knowledge(text, meta)
                if success:
                    items_added += 1
                    if items_added % 5 == 0:
                        print(f"  Indexed {items_added} items...")
                else:
                    print(f"  FAILED to add item: {row.get('name')}")
        
        print(f"SUCCESS: Seeded {items_added} items into Vector DB.")
    else:
        print("--- 2. Knowledge Base already populated. Skipping seed. ---")

    print("\n--- 3. Testing RAG Retrieval ---")
    # Test 1: Specific Item
    query = "paneer"
    print(f"Querying for '{query}'...")
    results = memory.query_knowledge(query, n_results=3)
    
    if not results:
        print("FAILURE: No results found for 'paneer'.")
    else:
        print(f"Found {len(results)} matches.")
        for res in results:
            print(f"  - {res['meta'].get('name')}: {res['content'][:60]}...")

    # Test 2: Concept
    query = "something spicy"
    print(f"\nQuerying for '{query}'...")
    results = memory.query_knowledge(query, n_results=2)
    for res in results:
        print(f"  - {res['meta'].get('name')}: {res['content'][:60]}...")

if __name__ == "__main__":
    seed_and_test_rag()
