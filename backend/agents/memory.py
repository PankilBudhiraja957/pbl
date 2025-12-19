
import os
import json
import uuid
from datetime import datetime
import threading
from dotenv import load_dotenv
import math

# Load env vars
load_dotenv()

# Check for Google GenAI
try:
    import google.generativeai as genai
    GOOGLE_SDK_AVAILABLE = True
except ImportError:
    GOOGLE_SDK_AVAILABLE = False
    print("Warning: google.generativeai not found. Semantic search disabled.")

# Simple Vector Logic
def cosine_similarity(v1, v2):
    "Compute cosine similarity between two vectors."
    dot_product = sum(a*b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a*a for a in v1))
    magnitude2 = math.sqrt(sum(b*b for b in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

from key_manager import KeyManager

class SimpleVectorMemory:
    def __init__(self, persist_path="brain_data.json"):
        self.persist_path = os.path.join(os.path.dirname(__file__), "..", persist_path) # Save in backend root
        self.knowledge = [] # List of {"id":, "text":, "meta":, "embedding":}
        self.key_manager = KeyManager()
        self._configure_genai()
        self.load()

    def _configure_genai(self):
        api_key = self.key_manager.get_current_key()
        if api_key and GOOGLE_SDK_AVAILABLE:
            genai.configure(api_key=api_key)

    def load(self):
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, 'r', encoding='utf-8') as f:
                    self.knowledge = json.load(f)
                print(f"--- [SimpleMemory] Loaded {len(self.knowledge)} items from {self.persist_path} ---")
            except Exception as e:
                print(f"Error loading memory: {e}")

    def save(self):
        try:
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge, f)
        except Exception as e:
            print(f"Error saving memory: {e}")

    def embed_text(self, text, retry_count=0):
        if not GOOGLE_SDK_AVAILABLE or not self.key_manager.get_current_key():
            return [0.0] * 768
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
                title="Memory"
            )
            return result['embedding']
        except Exception as e:
            print(f"Embedding error: {e}")
            # Check for quota or auth errors to rotate
            error_msg = str(e).lower()
            if ("quota" in error_msg or "429" in error_msg or "api_key" in error_msg or "401" in error_msg) and retry_count < len(self.key_manager.get_all_keys()):
                print(f"--- [SimpleMemory] Quota/Auth issue detected. Rotating key and retrying ({retry_count+1})... ---")
                if self.key_manager.rotate_key():
                    self._configure_genai()
                    return self.embed_text(text, retry_count + 1)
            
            return [0.0] * 768

    def add(self, text, metadata=None):
        embedding = self.embed_text(text)
        entry = {
            "id": str(uuid.uuid4()),
            "text": text,
            "meta": metadata or {},
            "embedding": embedding,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.knowledge.append(entry)
        self.save()
        return True

    def query(self, query_text, n_results=3):
        query_embedding = self.embed_text(query_text)
        if not query_embedding:
            return []

        # Calculate scores
        scored_items = []
        for item in self.knowledge:
            score = cosine_similarity(query_embedding, item['embedding'])
            scored_items.append((score, item))

        # Sort and return top N
        scored_items.sort(key=lambda x: x[0], reverse=True)
        top_items = scored_items[:n_results]
        
        # Format like Chroma results for compatibility
        results = []
        for score, item in top_items:
            results.append({
                "content": item['text'],
                "meta": item['meta'],
                "score": score
            })
        return results
    
    def count(self):
        return len(self.knowledge)

class AgentMemory:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AgentMemory, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.dataspace_log = []
        self.max_log_size = 50
        
        # Use Simple Memory
        self.simple_memory = SimpleVectorMemory()
        print("--- [AgentMemory] Initialized with SimpleVectorMemory fallback ---")

    def log_thought(self, agent_name, step_type, content, related_data=None):
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "type": step_type,
            "content": content,
            "data": related_data or {}
        }
        self.dataspace_log.insert(0, entry)
        if len(self.dataspace_log) > self.max_log_size:
            self.dataspace_log.pop()
        return entry

    def add_knowledge(self, text, metadata=None):
        return self.simple_memory.add(text, metadata)

    def get_knowledge_count(self):
        return self.simple_memory.count()

    def query_knowledge(self, query_text, n_results=3):
        return self.simple_memory.query(query_text, n_results)

    def get_dataspace_stream(self, limit=10):
        return self.dataspace_log[:limit]

    def clear_short_term(self):
        self.dataspace_log = []
