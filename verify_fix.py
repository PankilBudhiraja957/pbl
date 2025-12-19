
import sys
import os

# Improve path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
    print(f"Added {backend_dir} to sys.path")

from agents.tools import add_to_cart
from modals import MenuItem, CartItem, db

class MockUser:
    def __init__(self, id, allergies):
        self.id = id
        self.allergies = allergies
        self.preferences = ""

# Mock flask_login.current_user
import agents.tools
agents.tools.current_user = MockUser(id=999, allergies="Peanuts")

# Mock DB session
class MockSession:
    def add(self, item):
        print(f"DB ADD: {item}")
    def commit(self):
        print("DB COMMIT")
    def delete(self, item):
        print(f"DB DELETE: {item}")
    def flush(self):
        print("DB FLUSH")

agents.tools.db.session = MockSession()

# Mock Queries
class MockQuery:
    def __init__(self, data):
        self.data = data
    def all(self):
        return self.data
    def filter_by(self, **kwargs):
        # Simple mock filter
        return self
    def first(self):
        return None  # Assume no existing cart item for simplicity

# Create dummy menu
menu_items = [
    MenuItem(name="Peanut Butter Jelly", price=5.0, ingredients="Peanuts, Jelly, Bread", description="Classic PBJ"),
    MenuItem(name="Cheese Sandwich", price=4.0, ingredients="Cheese, Bread", description="Simple cheese sando")
]

# Monkeypatch MenuItem.query
agents.tools.MenuItem.query = MockQuery(menu_items)
agents.tools.CartItem.query = MockQuery([])

print("--- TEST 1: Add allergen item without confirmation ---")
res1 = add_to_cart("Peanut Butter Jelly", 1)
print(f"Result: {res1}")

print("\n--- TEST 2: Add allergen item WITH confirmation ---")
res2 = add_to_cart("Peanut Butter Jelly", 1, confirm_allergy=True)
print(f"Result: {res2}")

print("\n--- TEST 3: Add safe item ---")
res3 = add_to_cart("Cheese Sandwich", 1)
print(f"Result: {res3}")
