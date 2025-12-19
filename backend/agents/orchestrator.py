import os
import json
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.specialists import (
    NutritionistAgent, MenuSpecialistAgent, OrderTekkerAgent, 
    CoordinatorAgent, ChefAdvisorAgent, FeedbackAgent,
    SommelierAgent, ReservationAgent
)
from agents.tools import (
    get_full_menu, search_menu, get_nutritional_info, add_to_cart, 
    view_cart, remove_from_cart, update_user_profile, place_order,
    get_cooking_tips, submit_rating, get_item_ratings,
    get_pairings, book_table
)
from agents.memory import AgentMemory
from key_manager import KeyManager

class AgentOrchestrator:
    def __init__(self, socketio):
        self.socketio = socketio
        self.key_manager = KeyManager()
        self.memory = AgentMemory()
        
        # Initialize LLM
        self._init_llm()
        
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

    def _init_llm(self):
        """Initializes or re-initializes the LLM with the current key."""
        api_key = self.key_manager.get_current_key()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.3, 
            google_api_key=api_key,
            request_timeout=30, # Add timeout to prevent indefinite hangs
            max_retries=1
        )
        
    def _invoke_llm(self, messages, retry_count=0):
        """Invokes LLM with automatic key rotation on failure."""
        try:
            return self.llm.invoke(messages)
        except Exception as e:
            error_msg = str(e).lower()
            # Check for quota, auth, or timeout errors
            if ("quota" in error_msg or "429" in error_msg or "401" in error_msg or "timeout" in error_msg) and retry_count < 3:
                print(f"--- [Orchestrator] LLM Error ({e}). Rotating key... ---")
                if self.key_manager.rotate_key():
                    self._init_llm()
                    return self._invoke_llm(messages, retry_count + 1)
            
            # Re-raise if not handled or max retries reached
            raise e

    def _notify_frontend(self, agent_name, status, message=None):
        """Emits a WebSocket event to update the frontend UI."""
        if self.socketio:
            self.socketio.emit('agent_status', {
                'agent': agent_name,
                'status': status,
                'message': message
            })

    def _get_agent_response(self, agent, user_input, chat_history):
        """Invokes the specific agent with tools."""
        
        # Log to Dataspace
        self.memory.log_thought(agent.name, "plan", f"Analyzing request: {user_input}")
        
        # Define the tools string for the prompt
        tools_desc = """
        Available Tools:
        - get_full_menu(): Returns the full menu.
        - search_menu(query): Search for items matching a query.
        - get_nutritional_info(item_name): Get detailed macros for an item.
        - add_to_cart(item_name, quantity, confirm_allergy): Add item to cart. Set confirm_allergy=True to override warnings.
        - view_cart(): Show current cart contents.
        - remove_from_cart(item_name): Remove item from cart.
        - update_user_profile(preferences, allergies): Update user profile.
        - place_order(): Complete checkout and place order.
        - get_cooking_tips(item_name): Get cooking preparation info for a dish.
        - submit_rating(item_name, rating, comment): Submit a rating (1-5) for a dish.
        - get_item_ratings(item_name): Get average rating for a dish.
        - get_pairings(item_name): Get drink pairing recommendations for a dish.
        - book_table(party_size, date, time): Book a reservation.
        """
        
        system_prompt = agent.get_system_prompt() + "\n" + tools_desc
        system_prompt += "\n\nIf you need to use a tool, format your response as:\nTOOL: <tool_name>(<args>)\nExample: TOOL: search_menu('pizza')\nStop generating after the tool call. I will give you the result."
        
        # Inject Knowledge if relevant (simple semantic search for context)
        try:
            relevant_knowledge = self.memory.query_knowledge(user_input)
            if relevant_knowledge:
                knowledge_context = "\n\nRelevant Knowledge from Memory:\n" + "\n".join([k['content'] for k in relevant_knowledge])
                system_prompt += knowledge_context
                self.memory.log_thought(agent.name, "memory", "Retrieved relevant knowledge.", {"count": len(relevant_knowledge)})
        except:
            pass
        
        messages = [SystemMessage(content=system_prompt)]
        # Add limited history
        messages.extend(chat_history[-4:])
        messages.append(HumanMessage(content=user_input))
        
        # 1. Think and Generate (Potential Tool Call)
        self._notify_frontend(agent.name, "thinking", "Analyzing request...")
        try:
            response = self._invoke_llm(messages)
            content = response.content.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            self.memory.log_thought(agent.name, "error", f"LLM Generation Failed: {e}")
            return "I apologize, but I'm having trouble connecting to my brain right now. Please try again in a moment."
        
        # 2. Check for Tool Call
        if "TOOL:" in content:
            try:
                tool_line = [line for line in content.split('\n') if "TOOL:" in line][0]
                tool_call = tool_line.replace("TOOL:", "").strip()
                
                self._notify_frontend(agent.name, "tool_use", f"Executing: {tool_call}")
                self.memory.log_thought(agent.name, "action", f"Executing Tool: {tool_call}")
                print(f"[{agent.name}] Calling Tool: {tool_call}")
                
                # Safe execution with local scope
                local_scope = {
                    "get_full_menu": get_full_menu,
                    "search_menu": search_menu,
                    "get_nutritional_info": get_nutritional_info,
                    "add_to_cart": add_to_cart,
                    "view_cart": view_cart,
                    "remove_from_cart": remove_from_cart,
                    "update_user_profile": update_user_profile,
                    "place_order": place_order,
                    "get_cooking_tips": get_cooking_tips,
                    "submit_rating": submit_rating,
                    "get_item_ratings": get_item_ratings,
                    "get_pairings": get_pairings,
                    "book_table": book_table
                }
                
                tool_result = eval(tool_call, {"__builtins__": {}}, local_scope)
                
                self.memory.log_thought(agent.name, "observation", f"Tool Output: {str(tool_result)[:100]}...")
                
                # 3. Final Response with Tool Output
                follow_up_prompt = f"Tool Output: {tool_result}\n\nNow provide the final response to the user."
                messages.append(AIMessage(content=content))
                messages.append(SystemMessage(content=follow_up_prompt))
                
                self._notify_frontend(agent.name, "responding", "Formulating answer...")
                response = self._invoke_llm(messages)
                return response.content
                
            except Exception as e:
                print(f"Tool error: {e}")
                self.memory.log_thought(agent.name, "critique", f"Tool execution failed: {e}")
                return f"I tried to find that information but encountered an error: {e}"
        
        return content

    def route_request(self, user_input, chat_history):
        """Main entry point."""
        
        # 1. Coordinator Step
        self._notify_frontend("Coordinator", "routing", "Determining best agent...")
        self.memory.log_thought("Coordinator", "plan", f"Routing request: {user_input}")
        
        coord_prompt = self.coordinator.get_system_prompt()
        messages = [SystemMessage(content=coord_prompt), HumanMessage(content=user_input)]
        
        try:
            route_response = self._invoke_llm(messages).content.strip()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Gemini Error in Coordinator: {e}")
            return f"Currently offline or misconfigured. Error: {str(e)}"

        # Clean up response to get key
        target_agent_key = "General"
        for key in self.specialists.keys():
            if key.lower() in route_response.lower():
                target_agent_key = key
                break
        
        print(f"Coordinator routed to: {target_agent_key}")
        self.memory.log_thought("Coordinator", "decision", f"Selected agent: {target_agent_key}")

        # 2. Specialist Step
        if target_agent_key in self.specialists:
            agent = self.specialists[target_agent_key]
            print(f"Routing to: {agent.name}")
            
            self._notify_frontend(agent.name, "active", f"{agent.name} is taking over.")
            response = self._get_agent_response(agent, user_input, chat_history)
            
            self._notify_frontend(agent.name, "idle", "Done.")
            self._notify_frontend("Coordinator", "idle", "Standing by.")
            return response
        else:
            # Fallback for General chat
            self._notify_frontend("Coordinator", "idle", "Standing by.")
            return "Hello! I'm Saffron, your AI restaurant assistant. How can I help you today?"
