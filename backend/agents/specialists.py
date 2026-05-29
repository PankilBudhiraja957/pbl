from datetime import datetime
from agents.prompts import (
    CHEF_ADVISOR_PROMPT,
    COORDINATOR_PROMPT,
    FEEDBACK_PROMPT,
    MENU_SPECIALIST_PROMPT,
    NUTRITIONIST_PROMPT,
    ORDER_MANAGER_PROMPT,
    RESERVATION_PROMPT,
    SOMMELIER_PROMPT,
)

class BaseAgent:
    def __init__(self, name, role, description, key=None):
        self.name = name
        self.role = role
        self.description = description
        # 'key' matches the orchestrator specialists dict key for tool auth lookup
        self.key = key or name

    def get_system_prompt(self):
        raise NotImplementedError

class NutritionistAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dr. Basil", "Nutritionist", "Analyzes dietary requirements and health goals.", key="Nutritionist")

    def get_system_prompt(self):
        return NUTRITIONIST_PROMPT

class MenuSpecialistAgent(BaseAgent):
    def __init__(self):
        super().__init__("Chef Savour", "Menu Specialist", "Expert on the menu, ingredients, and matching flavors.", key="MenuSpecialist")

    def get_system_prompt(self):
        return MENU_SPECIALIST_PROMPT

class OrderTekkerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Turbo", "Order Manager", "Efficiently handles cart management and checkout.", key="OrderManager")

    def get_system_prompt(self):
        return ORDER_MANAGER_PROMPT

class ChefAdvisorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Chef Arjun", "Chef Advisor", "Provides cooking tips, preparation methods, and culinary secrets.", key="ChefAdvisor")

    def get_system_prompt(self):
        return CHEF_ADVISOR_PROMPT

class FeedbackAgent(BaseAgent):
    def __init__(self):
        super().__init__("Priya", "Feedback Manager", "Handles ratings, reviews, and customer feedback.", key="FeedbackAgent")

    def get_system_prompt(self):
        return FEEDBACK_PROMPT

class SommelierAgent(BaseAgent):
    def __init__(self):
        super().__init__("Sommelier", "Pairing Specialist", "Expert in drink pairings and flavor complements.", key="Sommelier")

    def get_system_prompt(self):
        return SOMMELIER_PROMPT

class ReservationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Reservationist", "Booking Manager", "Handles table reservations and scheduling.", key="Reservationist")

    def get_system_prompt(self):
        return RESERVATION_PROMPT

class CoordinatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Coordinator", "Orchestrator", "Routes user requests to the right specialist.")

    def get_system_prompt(self):
        return COORDINATOR_PROMPT

