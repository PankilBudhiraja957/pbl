
import os
import operator
from typing import TypedDict, Annotated, Sequence, Union, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from agents.specialists import (
    NutritionistAgent, MenuSpecialistAgent, OrderTekkerAgent, 
    CoordinatorAgent, ChefAdvisorAgent, FeedbackAgent,
    SommelierAgent, ReservationAgent
)
# Import tools
from agents.tools import (
    get_full_menu, search_menu, get_nutritional_info, add_to_cart, 
    view_cart, remove_from_cart, update_user_profile, place_order,
    get_cooking_tips, submit_rating, get_item_ratings,
    get_pairings, book_table, learn_user_preference
)
from agents.memory import AgentMemory

from key_manager import KeyManager

# Define State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    user_input: str

class LangGraphOrchestrator:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.key_manager = KeyManager()
        self.memory = AgentMemory()
        self._setup_llm()
        
        # Initialize Agents
        self.coordinator = CoordinatorAgent()
        self.specialists = {
            "Nutritionist": NutritionistAgent(),
            "MenuSpecialist": MenuSpecialistAgent(),
            "OrderManager": OrderTekkerAgent(),
            "ChefAdvisor": ChefAdvisorAgent(),
            "FeedbackAgent": FeedbackAgent(),
            "Sommelier": SommelierAgent(),
            "Reservationist": ReservationAgent()
        }
        
        # Tool Mappings
        self.agent_tools = {
            "Nutritionist": [get_nutritional_info, update_user_profile, learn_user_preference, search_menu],
            "MenuSpecialist": [get_full_menu, search_menu, get_item_ratings, learn_user_preference],
            "OrderManager": [add_to_cart, view_cart, remove_from_cart, place_order, search_menu],
            "ChefAdvisor": [get_cooking_tips, search_menu],
            "FeedbackAgent": [submit_rating, get_item_ratings, search_menu],
            "Sommelier": [get_pairings, search_menu],
            "Reservationist": [book_table]
        }
        
        # Build Graph
        self.graph = self._build_graph()

    def _setup_llm(self):
        """Initializes or re-initializes the LLM with the current API key"""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.3, 
            google_api_key=self.key_manager.get_current_key(),
            timeout=15, # Prevent hanging
            max_retries=2
        )

    def _invoke_llm(self, messages, tools=None, retry_count=0):
        """Wraps LLM invocation with key rotation on quota limits"""
        llm = self.llm
        if tools:
            llm = self.llm.bind_tools(tools)
            
        # Log Interaction
        if retry_count == 0:
             print(f"\n--- [LLM Invoke] Sending {len(messages)} messages (Tools: {len(tools) if tools else 0}) ---", flush=True)
             if messages and hasattr(messages[-1], 'content'):
                 print(f"    Last Message: {messages[-1].content}", flush=True)

        try:
            response = llm.invoke(messages)

            # Log Response
            if response.content:
                print(f"--- [LLM Response] {response.content} ---", flush=True)
            elif response.tool_calls:
                print(f"--- [LLM Tool Calls] {response.tool_calls} ---", flush=True)
            
            return response
        except Exception as e:
            error_msg = str(e).lower()
            if ("quota" in error_msg or "429" in error_msg or "api_key" in error_msg or "401" in error_msg or "disconnected" in error_msg or "503" in error_msg or "500" in error_msg):
                import time
                if retry_count < len(self.key_manager.get_all_keys()) * 2: # Allow multiple retries per key if needed, or simplier: retry a few times
                     print(f"--- [Orchestrator] Transient error/Auth issue detected: {error_msg}. Retrying ({retry_count+1})... ---")
                     # If it's a quota/auth issue, rotate. If it's network, maybe just retry? 
                     # For simplicity, we rotate or at least re-setup to be safe.
                     should_rotate = any(x in error_msg for x in ["quota", "429", "401", "expired", "api_key_invalid", "invalid_argument", "disconnected", "503", "500"])
                     if should_rotate:
                         self.key_manager.rotate_key()
                     
                     time.sleep(1) # Backoff
                     self._setup_llm()
                     return self._invoke_llm(messages, tools, retry_count + 1)
            raise e

    def _notify(self, agent, status, message):
        # Print to Backend Console
        print(f"\n--- [Agent: {agent}] Status: {status.upper()} ---", flush=True)
        print(f"    Message: {message}\n", flush=True)

        if self.socketio:
            self.socketio.emit('agent_status', {
                'agent': agent,
                'status': status,
                'message': message
            })

    def _log_and_broadcast(self, agent, step_type, content, data=None):
        """Logs thought to memory and emits via Socket.IO"""
        # Print to Backend Console
        print(f"--- [Agent: {agent}] {step_type.upper()}: {content}", flush=True)
        if data:
            print(f"    Data: {data}", flush=True)

        # 1. Log to DB/Memory
        entry = self.memory.log_thought(agent, step_type, content, data)
        
        # 2. Emit to Frontend (Push, don't Poll)
        if self.socketio:
            self.socketio.emit('new_thought', entry)

    def coordinator_node(self, state: AgentState):
        self._notify("Coordinator", "thinking", "Routing request...")
        
        user_input = state["user_input"]
        # Log Plan
        self._log_and_broadcast("Coordinator", "plan", f"Analyzing request: {user_input}")

        prompt = self.coordinator.get_system_prompt()
        
        messages = [SystemMessage(content=prompt), HumanMessage(content=user_input)]
        response = self._invoke_llm(messages)
        content = response.content.strip()
        
        # Clean up response to get key
        target_agent = "General"
        for key in self.specialists.keys():
            if key.lower() in content.lower():
                target_agent = key
                break
        
        self._log_and_broadcast("Coordinator", "decision", f"Routed to {target_agent}")
        self._notify("Coordinator", "routed", f"Routed to {target_agent}")
        return {"next_agent": target_agent}

    def specialist_node(self, state: AgentState):
        agent_name = state["next_agent"]
        user_input = state["user_input"]
        
        if agent_name == "General":
             return {"messages": [AIMessage(content="Hello! I'm Saffron, your AI assistant. How can I help you today?")]}

        agent = self.specialists.get(agent_name)
        if not agent:
            return {"messages": [AIMessage(content="I'm having trouble connecting to that specialist.")]}

        self._notify(agent_name, "active", f"{agent_name} is working...")
        self._log_and_broadcast(agent_name, "plan", f"Taking over request.")

        # 1. RAG Memory Injection
        rag_context = ""
        if agent_name in ["MenuSpecialist", "Nutritionist", "ChefAdvisor", "Sommelier"]:
            try:
                # Better RAG Query: combine current input with previous user message for context
                context_query = user_input
                if len(state["messages"]) >= 2:
                    last_user_msg = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
                    if last_user_msg and last_user_msg != user_input:
                        context_query = f"{last_user_msg} {user_input}"
                
                relevant_knowledge = self.memory.query_knowledge(context_query)
                if relevant_knowledge:
                    self._log_and_broadcast(agent_name, "memory", f"Retrieved {len(relevant_knowledge)} memories for query: {context_query}", {"count": len(relevant_knowledge)})
                    rag_context = "\n\nRefer to this knowledge if relevant:\n" + "\n".join([f"- {k['content']}" for k in relevant_knowledge])
            except Exception as e:
                print(f"RAG Error: {e}")

        # 2. Build Prompt
        system_prompt = agent.get_system_prompt() + rag_context
        
        # --- INJECT USER PROFILE ---
        from flask_login import current_user
        try:
             if current_user and current_user.is_authenticated:
                 user_profile = f"\n\n--- User Profile ---\nName: {current_user.username}\nAllergies: {current_user.allergies or 'None'}\nPreferences: {current_user.preferences or 'None'}\n"
                 if current_user.calorie_goal:
                     user_profile += f"Nutrition Goals: {current_user.calorie_goal} cal\n"
                 
                 user_profile += "CRITICAL: Customise your response based on this profile. If the user asks for a recommendation, prioritizing items that match their 'Preferences'.\n"
                 system_prompt += user_profile
        except Exception as e:
            print(f"Error injecting user profile: {e}")
        # ---------------------------

        messages = [SystemMessage(content=system_prompt)]
        messages.extend(state["messages"][-5:]) # Last 5 messages context
        
        # Ensure the last message is from user or at least valid for the LLM call
        last_msg_content = state["messages"][-1].content if state["messages"] else ""
        if last_msg_content != user_input:
            messages.append(HumanMessage(content=user_input))

        # 3. Bind Tools
        tools = self.agent_tools.get(agent_name, [])
        
        # 4. Invoke LLM (Using rotation wrapper)
        self._notify(agent_name, "thinking", "Analyzing...")
        response = self._invoke_llm(messages, tools=tools)
        
        # 5. Handle Tool Calls
        if response.tool_calls:
            self._notify(agent_name, "tool_use", "Executing tools...")
            
            # Simple tool execution loop
            tool_outputs = []
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                self._log_and_broadcast(agent_name, "action", f"Calling Tool: {tool_name}")
                
                # Find matching function
                selected_tool = next((t for t in tools if t.__name__ == tool_name), None)
                
                if selected_tool:
                    try:
                        result = selected_tool(**tool_args)
                        tool_outputs.append(str(result))
                        self._log_and_broadcast(agent_name, "observation", f"Tool Output: {str(result)}")
                    except Exception as e:
                        tool_outputs.append(f"Error executing {tool_name}: {e}")
                else:
                    tool_outputs.append(f"Tool {tool_name} not found.")
            
            # Feed back to LLM for final answer
            # We construct a new message history where the AI calls the tool, and then a "System" or "Tool" message provides the output.
            # Since we are not using the official ToolMessage class with ID mapping here (simplified custom loop),
            # we will provide the context clearly in a new SystemMessage that acts as the observation.
            
            tool_outputs_str = "\n".join(tool_outputs)
            follow_up_prompt = f"Use the following tool usage results to formulate your final response to the user:\n\n{tool_outputs_str}"
            
            # Append the AI's tool-calling message (even if content was empty, it had tool_calls)
            messages.append(response) 
            
            # Append the observation
            messages.append(HumanMessage(content=follow_up_prompt))
            
            self._notify(agent_name, "responding", "Finalizing answer...")
            final_response = self._invoke_llm(messages)
            return {"messages": [final_response]}
            
        else:
            return {"messages": [response]}

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("coordinator", self.coordinator_node)
        workflow.add_node("specialist", self.specialist_node)
        
        workflow.set_entry_point("coordinator")
        
        workflow.add_edge("coordinator", "specialist")
        workflow.add_edge("specialist", END)
        
        return workflow.compile()

    def route_request(self, user_message, chat_history_langchain):
        """Main entry point called by app.py"""
        
        # Initialize state
        initial_state = {
            "messages": chat_history_langchain,
            "user_input": user_message,
            "next_agent": ""
        }
        
        result = self.graph.invoke(initial_state)
        
        # Extract final AI message
        messages = result["messages"]
        if messages and isinstance(messages[-1], AIMessage):
            content = messages[-1].content
            if isinstance(content, list):
                # Join text parts if it's a list (typical for multi-modal or tool-calling messages)
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'text':
                        text_parts.append(part.get('text', ''))
                    elif isinstance(part, str):
                        text_parts.append(part)
                return "\n".join(text_parts)
            return str(content or "")
        return "I'm sorry, I couldn't generate a response."
