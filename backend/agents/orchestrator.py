import os
import json
import time
import re
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
    get_pairings, get_reservation_quote, book_table, check_table_availability
)
from agents.memory import AgentMemory
from key_manager import KeyManager
from agents.prompts import BASE_SYSTEM_PROMPT

HISTORY_MESSAGE_LIMIT = 5

class AgentOrchestrator:
    def __init__(self, socketio):
        self.socketio = socketio
        self.key_manager = KeyManager()
        self.memory = AgentMemory()
        self.last_prompt_debug = None
        
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
            model="gemini-2.0-flash", 
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

    def _extract_intent_keywords(self, text: str) -> str:
        text = text.lower()
        if any(w in text for w in ["book", "reserve", "table", "reservation", "booking"]):
            return "Reservationist"
        if any(w in text for w in ["add", "cart", "order", "checkout"]):
            return "OrderManager"
        if any(w in text for w in ["healthy", "calories", "allergy", "diet", "nutrition", "protein"]):
            return "Nutritionist"
        if any(w in text for w in ["cook", "recipe", "chef", "prepare"]):
            return "ChefAdvisor"
        if any(w in text for w in ["wine", "drink", "pairing", "beverage"]):
            return "Sommelier"
        if any(w in text for w in ["rate", "review", "feedback", "star"]):
            return "FeedbackAgent"
        if any(w in text for w in ["menu", "food", "dish", "spicy"]):
            return "MenuSpecialist"
        return "General"

    def _rule_based_fallback(self, agent_name: str, user_input: str) -> str:
        text = user_input.lower()
        if agent_name == "OrderManager":
            if "add" in text and "cart" in text:
                return "I'll help you add that to your cart right away."
            if "order" in text or "checkout" in text:
                return "I can help you place your order."
            return "I can help with your order or cart."
        elif agent_name == "MenuSpecialist":
            if "show" in text or "spicy" in text or "menu" in text:
                return "Let me check the menu for those items."
            return "I can help you explore our menu."
        elif agent_name == "Reservationist":
            if "table" in text or "available" in text:
                return "I will check our table availability for you."
            return "I can help you book a table."
        elif agent_name == "Nutritionist":
            return "I can provide nutritional information."
        return "I am currently unable to process complex requests. How else can I help?"

    def _get_agent_response(self, agent, user_input, chat_history, backend_context=""):
        """Invokes the specific agent with tools."""
        
        # Log to Dataspace
        self.memory.log_thought(agent.name, "plan", f"Analyzing request: {user_input}")
        
        # Define agent-specific tool configurations
        agent_tools = {
            "OrderManager": [
                ("add_to_cart", "add_to_cart(item_name, quantity, confirm_allergy): Add item to cart. Set confirm_allergy=True to override warnings."),
                ("view_cart", "view_cart(): Show current cart contents."),
                ("remove_from_cart", "remove_from_cart(item_name): Remove item from cart."),
                ("place_order", "place_order(): Complete checkout and place order."),
                ("search_menu", "search_menu(query): Search for items matching a query."),
                ("get_full_menu", "get_full_menu(): Returns the full menu.")
            ],
            "Reservationist": [
                ("get_reservation_quote", "get_reservation_quote(table_type, party_size, table_quantity, seating_preference, occasion_type): Get an estimated reservation price quote."),
                ("book_table", "book_table(table_type, party_size, date, time, seating_preference='indoor', occasion_type='none'): Book a reservation."),
                ("check_table_availability", "check_table_availability(date, time, table_type=None): Check table availability.")
            ],
            "MenuSpecialist": [
                ("get_full_menu", "get_full_menu(): Returns the full menu."),
                ("search_menu", "search_menu(query): Search for items matching a query."),
                ("get_nutritional_info", "get_nutritional_info(item_name): Get detailed macros for an item."),
                ("get_cooking_tips", "get_cooking_tips(item_name): Get cooking preparation info for a dish."),
                ("get_item_ratings", "get_item_ratings(item_name): Get average rating for a dish."),
                ("get_pairings", "get_pairings(item_name): Get drink pairing recommendations for a dish.")
            ],
            "Nutritionist": [
                ("get_nutritional_info", "get_nutritional_info(item_name): Get detailed macros for an item."),
                ("search_menu", "search_menu(query): Search for items matching a query."),
                ("update_user_profile", "update_user_profile(preferences, allergies): Update user profile.")
            ],
            "ChefAdvisor": [
                ("get_cooking_tips", "get_cooking_tips(item_name): Get cooking preparation info for a dish."),
                ("search_menu", "search_menu(query): Search for items matching a query.")
            ],
            "FeedbackAgent": [
                ("submit_rating", "submit_rating(item_name, rating, comment): Submit a rating (1-5) for a dish."),
                ("get_item_ratings", "get_item_ratings(item_name): Get average rating for a dish.")
            ],
            "Sommelier": [
                ("get_pairings", "get_pairings(item_name): Get drink pairing recommendations for a dish."),
                ("search_menu", "search_menu(query): Search for items matching a query.")
            ]
        }
        
        allowed_tools = agent_tools.get(agent.key, [])
        if allowed_tools:
            tools_desc = "\nAvailable Tools:\n" + "\n".join([f"- {t[1]}" for t in allowed_tools])
        else:
            tools_desc = "\nNo tools available."
        
        system_prompt = BASE_SYSTEM_PROMPT + "\n\n" + agent.get_system_prompt() + "\n" + tools_desc
        system_prompt += """

GLOBAL FOOD PLANNING RULES:
- For any group/menu/budget plan, calculate realistic quantities before answering.
- Use serving assumptions: starters 1 plate per 2 people; curries/dals 1 portion per 2-3 people; rice/biryani 1 portion per 2-3 people; breads at least 1 per person; desserts/drinks 1 per person.
- Always show quantity x price = subtotal, total, and per-person split when discussing cost.
- If the user asks "is it enough", "how many", "split", "accordingly", or corrects your math, recalculate with quantities instead of repeating the old answer.
- Respect stored allergies from backend context and avoid conflicting menu items.

DOMAIN GUARDRAIL:
- Only answer questions related to DineSmartAI restaurant workflows: dine-in/table reservations, menu, food ordering, cart/checkout, nutrition/allergies, favorites, ratings/reviews, order history, inbox, table availability, party/event food planning, drink pairings, cooking tips for menu items, and admin restaurant operations.
- If the user asks about anything unrelated, politely refuse in one short sentence and redirect to restaurant help. Example: "I can only help with DineSmartAI restaurant, menu, orders, and reservations. What would you like to eat or book?"
- Do not answer unrelated general knowledge, coding, medical/legal/financial, politics, entertainment, personal advice, or web-search questions.
- If a question is partly related, answer only the restaurant-related part.
"""
        if backend_context:
            system_prompt += "\n\n" + backend_context
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
        # Add the last 5 stored chat messages.
        messages.extend(chat_history[-HISTORY_MESSAGE_LIMIT:])
        messages.append(HumanMessage(content=user_input))
        self.last_prompt_debug = {
            "stage": "specialist",
            "agent": agent.name,
            "system_prompt": system_prompt,
            "history_count": min(len(chat_history), HISTORY_MESSAGE_LIMIT),
            "user_input": user_input,
        }
        
        # 1. Think and Generate (Potential Tool Call)
        self._notify_frontend(agent.name, "thinking", "Analyzing request...")
        try:
            response = self._invoke_llm(messages)
            content = response.content.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            self.memory.log_thought(agent.name, "error", f"LLM Generation Failed: {e}")
            return self._rule_based_fallback(agent.key, user_input)
        
        # 2. Check for Tool Call
        tool_lines = [line for line in content.split('\n') if "TOOL:" in line]
        if tool_lines:
            try:
                tool_results = []
                for tool_line in tool_lines:
                    tool_call = tool_line.replace("TOOL:", "").strip()
                    
                    self._notify_frontend(agent.name, "tool_use", f"Executing: {tool_call}")
                    self.memory.log_thought(agent.name, "action", f"Executing Tool: {tool_call}")
                    print(f"[{agent.name}] Calling Tool: {tool_call}")
                    
                    # Safe execution with local scope containing only allowed tools
                    all_tools = {
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
                        "get_reservation_quote": get_reservation_quote,
                        "book_table": book_table,
                        "check_table_availability": check_table_availability
                    }
                    
                    # Filter local_scope to only include allowed tools for this agent
                    local_scope = {}
                    allowed_names = {t[0] for t in allowed_tools}
                    for name in allowed_names:
                        if name in all_tools:
                            local_scope[name] = all_tools[name]
                    
                    # Hard restriction: Parse the tool name from the tool_call and check authorization
                    tool_name_match = re.match(r"^([a-zA-Z0-9_]+)\(", tool_call)
                    if not tool_name_match:
                        raise ValueError(f"Invalid tool call format: {tool_call}")
                    
                    called_tool = tool_name_match.group(1)
                    if called_tool not in local_scope:
                        raise PermissionError(f"Agent '{agent.key}' is not authorized to call tool '{called_tool}'.")
                    
                    tool_result = eval(tool_call, {"__builtins__": {}}, local_scope)
                    
                    self.memory.log_thought(agent.name, "observation", f"Tool Output: {str(tool_result)[:100]}...")
                    tool_results.append(f"{tool_call} -> {tool_result}")
                
                # 3. Final Response with Tool Output
                combined_tool_output = "\n".join(tool_results)
                follow_up_prompt = f"Tool Output:\n{combined_tool_output}\n\nNow provide the final response to the user."
                messages.append(AIMessage(content=content))
                messages.append(HumanMessage(content=follow_up_prompt))
                
                self._notify_frontend(agent.name, "responding", "Formulating answer...")
                response = self._invoke_llm(messages)
                return response.content
                
            except Exception as e:
                print(f"Tool error: {e}")
                self.memory.log_thought(agent.name, "critique", f"Tool execution failed: {e}")
                return f"I tried to find that information but encountered an error: {e}"
        
        return content

    def route_request(self, user_input, chat_history, backend_context=""):
        """Main entry point."""
        
        # Multi-intent routing interceptor
        user_input_lower = user_input.lower()
        spatial_keywords = ["table", "book", "reserve", "reservation", "booking", "seating", "dine-in", "dine in"]
        culinary_keywords = ["menu", "suggest", "recommend", "food", "eat", "dish", "dishes", "meal", "special", "specials", "curry", "paneer", "chicken", "items", "add"]
        # Keywords indicating user wants to ADD/ORDER items (not just browse/suggest)
        order_intent_keywords = ["add", "order", "put in cart", "add to cart", "add these", "add all", "add the", "add items", "place order", "yes add", "yes book", "confirm and add", "book and add"]
        
        has_spatial = any(w in user_input_lower for w in spatial_keywords)
        has_culinary = any(w in user_input_lower for w in culinary_keywords)
        has_order_intent = any(w in user_input_lower for w in order_intent_keywords)
        
        if has_spatial and has_culinary:
            if has_order_intent:
                # User wants to ADD items AND book table → OrderManager + Reservationist
                print("--- [Orchestrator] Multi-intent: Add+Book detected. Executing OrderManager -> Reservationist chain. ---")
                self.memory.log_thought("Coordinator", "plan", "Multi-intent detected: Add Items & Book Table. Running OrderManager -> Reservationist.")
                
                # Step 1: OrderManager handles cart additions
                order_agent = self.specialists["OrderManager"]
                self._notify_frontend(order_agent.name, "active", f"{order_agent.name} is adding items to your cart.")
                order_user_input = (
                    "[SYSTEM ROUTING DIRECTIVE: Focus ONLY on processing menu search or cart operations like adding/removing items to/from the cart, or viewing/placing orders. "
                    "Do NOT attempt to suggest a table or book a table or check table availability. Leave all reservation tasks to the next agent in the sequence.]\n"
                    f"User Request: {user_input}"
                )
                order_response = self._get_agent_response(order_agent, order_user_input, chat_history, backend_context)
                self._notify_frontend(order_agent.name, "idle", "Done.")
                
                # Step 2: Reservationist books the table
                from langchain_core.messages import AIMessage
                updated_chat_history = list(chat_history) + [AIMessage(content=order_response)]
                reservation_agent = self.specialists["Reservationist"]
                self._notify_frontend(reservation_agent.name, "active", f"{reservation_agent.name} is booking your table.")
                reservation_user_input = (
                    "[SYSTEM ROUTING DIRECTIVE: Focus ONLY on reservation quote and table booking operations. "
                    "Do NOT attempt to add items to the cart, suggest menu items, view cart, or place food orders. Those tasks have already been completed by the previous agent in the sequence.]\n"
                    f"User Request: {user_input}"
                )
                reservation_response = self._get_agent_response(reservation_agent, reservation_user_input, updated_chat_history, backend_context)
                self._notify_frontend(reservation_agent.name, "idle", "Done.")
                
                self._notify_frontend("Coordinator", "idle", "Standing by.")
                combined_response = (
                    f"{order_response}\n\n"
                    f"--- Table Booking ---\n"
                    f"{reservation_response}"
                )
                return combined_response
            else:
                # User wants menu suggestions AND a reservation quote → MenuSpecialist + Reservationist
                print("--- [Orchestrator] Multi-intent: Suggest+Book detected. Executing MenuSpecialist -> Reservationist chain. ---")
                self.memory.log_thought("Coordinator", "plan", "Multi-intent detected: Menu Suggestions & Reservation. Running MenuSpecialist -> Reservationist.")
                
                # Step 1: MenuSpecialist
                menu_agent = self.specialists["MenuSpecialist"]
                self._notify_frontend(menu_agent.name, "active", f"{menu_agent.name} is planning your menu suggestions.")
                menu_user_input = (
                    "[SYSTEM ROUTING DIRECTIVE: Focus ONLY on recommending/suggesting menu items, dietary/nutritional info, or drink pairings. "
                    "Do NOT attempt to book a table, check table availability, or fetch reservation quotes. Leave all table/reservation tasks to the next agent in the sequence.]\n"
                    f"User Request: {user_input}"
                )
                menu_response = self._get_agent_response(menu_agent, menu_user_input, chat_history, backend_context)
                self._notify_frontend(menu_agent.name, "idle", "Done.")
                
                # Step 2: Reservationist (with updated chat history containing MenuSpecialist's response)
                from langchain_core.messages import AIMessage
                updated_chat_history = list(chat_history) + [AIMessage(content=menu_response)]
                reservation_agent = self.specialists["Reservationist"]
                self._notify_frontend(reservation_agent.name, "active", f"{reservation_agent.name} is preparing reservation details.")
                reservation_user_input = (
                    "[SYSTEM ROUTING DIRECTIVE: Focus ONLY on reservation quote and checking table availability operations. "
                    "Do NOT attempt to suggest menu items or add food items to the cart. Those tasks have already been completed by the previous agent in the sequence.]\n"
                    f"User Request: {user_input}"
                )
                reservation_response = self._get_agent_response(reservation_agent, reservation_user_input, updated_chat_history, backend_context)
                self._notify_frontend(reservation_agent.name, "idle", "Done.")
                
                self._notify_frontend("Coordinator", "idle", "Standing by.")
                combined_response = (
                    f"{menu_response}\n\n"
                    f"--- Reservation Details ---\n"
                    f"{reservation_response}"
                )
                return combined_response

        # 1. Coordinator Step
        self._notify_frontend("Coordinator", "routing", "Determining best agent...")
        self.memory.log_thought("Coordinator", "plan", f"Routing request: {user_input}")
        
        coord_prompt = BASE_SYSTEM_PROMPT + "\n\n" + self.coordinator.get_system_prompt()
        coord_prompt += """

Routing note:
- Group menu planning, budget planning, quantity correction, per-person split, and "is it enough" questions should route to MenuSpecialist unless the user clearly asks to place an order or finalize a booking.
- A party/menu/budget request without date and time is not a table booking confirmation.
- Unrelated/non-restaurant questions should route to General for a brief domain refusal.
"""
        if backend_context:
            coord_prompt += "\n\n" + backend_context
        messages = [SystemMessage(content=coord_prompt)]
        messages.extend(chat_history[-HISTORY_MESSAGE_LIMIT:])
        messages.append(HumanMessage(content=user_input))
        self.last_prompt_debug = {
            "stage": "coordinator",
            "agent": "Coordinator",
            "system_prompt": coord_prompt,
            "history_count": min(len(chat_history), HISTORY_MESSAGE_LIMIT),
            "user_input": user_input,
        }
        
        try:
            route_response = self._invoke_llm(messages).content.strip()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Gemini Error in Coordinator: {e}")
            route_response = self._extract_intent_keywords(user_input)

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
            response = self._get_agent_response(agent, user_input, chat_history, backend_context)
            
            self._notify_frontend(agent.name, "idle", "Done.")
            self._notify_frontend("Coordinator", "idle", "Standing by.")
            return response
        else:
            # Fallback for General chat
            self._notify_frontend("Coordinator", "idle", "Standing by.")
            messages = [
                SystemMessage(content=(
                    BASE_SYSTEM_PROMPT + "\n\n"
                    "You are DineSmartAI, a concise restaurant assistant. "
                    "Only answer DineSmartAI restaurant-related questions: menu, orders, dine-in reservations, cart, nutrition/allergies, favorites, ratings, order history, inbox, party planning, pairings, and cooking tips for menu items. "
                    "For unrelated questions, give one short refusal and redirect to restaurant help. "
                    "Answer the user using the recent conversation context. "
                    "If the user is confirming or referring to earlier details, restate the known details and ask only for missing information. "
                    "Do not reset the conversation or greet as if this is a new chat."
                ) + ("\n\n" + backend_context if backend_context else ""))
            ]
            messages.extend(chat_history[-HISTORY_MESSAGE_LIMIT:])
            messages.append(HumanMessage(content=user_input))
            self.last_prompt_debug = {
                "stage": "general",
                "agent": "General",
                "system_prompt": messages[0].content,
                "history_count": min(len(chat_history), HISTORY_MESSAGE_LIMIT),
                "user_input": user_input,
            }
            try:
                return self._invoke_llm(messages).content.strip()
            except Exception as e:
                print(f"General chat error: {e}")
                return "I have the previous conversation context, but I could not process that reply. Please try again."
