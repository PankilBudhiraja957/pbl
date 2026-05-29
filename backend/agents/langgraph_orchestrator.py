from agents.orchestrator import AgentOrchestrator

# Compatibility wrapper for the legacy import path.
# The project previously used a LangGraph-based orchestrator,
# but the built-in AgentOrchestrator now provides the same interface
# without requiring the external langgraph package.

class LangGraphOrchestrator(AgentOrchestrator):
    """Legacy alias preserved for import compatibility."""
    pass
