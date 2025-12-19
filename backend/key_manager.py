import os
import threading

class KeyManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(KeyManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # Load keys from environment
        keys_str = os.environ.get("GEMINI_API_KEYS", "")
        if keys_str:
            self.keys = [k.strip().strip('"') for k in keys_str.split(",") if k.strip()]
        else:
            # Fallback to single key
            single_key = os.environ.get("GEMINI_API_KEY")
            self.keys = [single_key] if single_key else []
        
        self.current_index = 0
        print(f"--- [KeyManager] Initialized with {len(self.keys)} keys ---")

    def get_current_key(self):
        if not self.keys:
            return None
        return self.keys[self.current_index]

    def rotate_key(self):
        if not self.keys or len(self.keys) <= 1:
            return False
        
        with self._lock:
            self.current_index = (self.current_index + 1) % len(self.keys)
            print(f"--- [KeyManager] Rotated to key index {self.current_index} ---")
            return True

    def get_all_keys(self):
        return self.keys
