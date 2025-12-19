
import sys
import os

# Ensure backend directory is in path
sys.path.append(os.getcwd())

from flask import Flask
from app import app, db, migrate_csv_to_db
from agents.tools import search_menu
from agents.memory import AgentMemory

def test_rag():
    print("--- Testing Ephemeral RAG ---")
    
    with app.app_context():
        # 1. Initialize DB and Migrate (Should index to Brain)
        print("Initializing DB...")
        db.create_all()
        
        print("Running Migration (populating Brain)...")
        migrate_csv_to_db()
        
        # 2. Check Memory Count
        mem = AgentMemory()
        count = mem.knowledge_collection.count()
        print(f"Brain Count: {count}")
        
        if count == 0:
            print("FAILURE: Brain is empty even after migration.")
            return

        # 3. Test Query
        print("Querying 'spicy'...")
        result = search_menu("spicy")
        print("Search Result Preview:")
        print(result[:500] + "...")
        
        if "I couldn't find" in result:
             print("FAILURE: Search returned nothing.")
        else:
             print("SUCCESS: RAG returned results!")

if __name__ == "__main__":
    test_rag()
