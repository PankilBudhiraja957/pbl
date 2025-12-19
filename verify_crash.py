
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Mock environment variables BEFORE imports
os.environ["GEMINI_API_KEY"] = "fake_key_for_test"

# Mock app and db to avoid full Flask/SQLAlchemy init
mock_app = MagicMock()
mock_db = MagicMock()

# Patch modules
with patch.dict(sys.modules, {'modals': MagicMock(db=mock_db), 'flask_login': MagicMock()}):
    from agents.orchestrator import AgentOrchestrator
    from agents.memory import AgentMemory

class TestAgentCrash(unittest.TestCase):
    def setUp(self):
        # Reset memory singleton
        AgentMemory._instance = None
        self.memory = AgentMemory()
        
        # Mock LLM to simulate different behaviors
        self.mock_socketio = MagicMock()
        self.orchestrator = AgentOrchestrator(self.mock_socketio)
        self.orchestrator.llm = MagicMock()

    def test_coordinator_exception_handling(self):
        """Test if route_request catches exceptions and prints traceback."""
        print("\n--- TEST: Coordinator Exception Handling ---")
        
        # Force LLM to raise an exception
        self.orchestrator.llm.invoke.side_effect = Exception("Simulated Gemini API Failure")
        
        response = self.orchestrator.route_request("Hello", [])
        print(f"Response: {response}")
        self.assertEqual(response, "Currently offline or misconfigured.")

    def test_rag_initialization(self):
        """Test if memory initializes correctly (mocked)."""
        print("\n--- TEST: RAG Initialization ---")
        self.assertIsNotNone(self.memory.knowledge_collection, "Knowledge collection should be initialized (if chroma mocked or valid)")

if __name__ == '__main__':
    unittest.main()
