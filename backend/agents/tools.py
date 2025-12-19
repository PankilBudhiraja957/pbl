import re
from difflib import get_close_matches
from flask_login import current_user
from modals import db, MenuItem, CartItem, Order, OrderItem, InboxMessage

def get_full_menu() -> str:
    """Returns the entire menu as a formatted string."""
    items = MenuItem.query.all()
    if not items:
        return "The menu is currently empty."
    return "Here is our menu:\n" + "\n".join([f"- {item.name} (${item.price:.2f}): {item.description} ({item.diet}, {item.calories} cal)" for item in items])

def search_menu(query: str) -> str:
    """Searches for menu items based on a query string (name, ingredient, or description)."""
    query = query.lower().strip()
    # 1. Semantic Search (RAG)
    # 1. Semantic Search (RAG)
    # Using AgentMemory singleton directly to avoid circular dependency with orchestrator
    # We can import AgentMemory and use the singleton.
    from agents.memory import AgentMemory
    memory = AgentMemory()
    
    semantic_matches = []
    try:
        results = memory.query_knowledge(query, n_results=5)
        # Results are [{"content": "...", "meta": {...}}]
        # We need to map back to MenuItem objects for consistency or just return text.
        # Returning MenuItem objects is better for the UI/Agent to use details.
        
        for res in results:
             # Try to find by name or ID if stored in meta
             name = res['meta'].get('name')
             if name:
                 # Find in DB
                 item = MenuItem.query.filter_by(name=name).first()
                 if item and item not in semantic_matches:
                     semantic_matches.append(item)
    except Exception as e:
         print(f"Semantic search failed: {e}")

    # 2. Keyword Search (Existing Logic)
    keyword_matches = []
    all_items = MenuItem.query.all()
    
    # Pre-fetch all items for fuzzy matching
    all_names = {item.name.lower(): item for item in all_items}
    
    for item in all_items:
        # Check Name, Description, Ingredients, Diet, Category
        name_lower = (item.name or "").lower()
        desc_lower = (item.description or "").lower()
        ingredients_lower = (item.ingredients or "").lower()
        diet_lower = (item.diet or "").lower()
        category_lower = (item.category or "").lower()
        
        # Exact substring matches
        if (query in name_lower or 
            query in desc_lower or 
            query in ingredients_lower or 
            query in diet_lower or
            query in category_lower):
            keyword_matches.append(item)
            
        # Specific handling for "spicy"
        if "spicy" in query:
             spicy_terms = ["chilli", "chili", "masala", "curry", "vindaloo", "schezwan", "peppercorn", "tikka", "hot"]
             if any(term in name_lower or term in desc_lower or term in ingredients_lower for term in spicy_terms):
                 if item not in keyword_matches:
                     keyword_matches.append(item)

    # 3. Fuzzy Search (Fallback if few results)
    fuzzy_matches = []
    if len(keyword_matches) < 3:
        # Try to match the name specifically
        matches = get_close_matches(query, all_names.keys(), n=5, cutoff=0.5)
        for m in matches:
             item = all_names[m]
             if item not in keyword_matches:
                 fuzzy_matches.append(item)

    # 4. Combine & Deduplicate
    all_results = list(set(semantic_matches + keyword_matches + fuzzy_matches))
    
    if not all_results:
        return f"I couldn't find any items matching '{query}' on our menu."
    
    return "\n".join([f"- {item.name} (${item.price:.2f}): {item.description}. Ingredients: {item.ingredients}. Diet: {item.diet}. Category: {item.category}" for item in all_results])

def get_nutritional_info(item_name: str) -> str:
    """Returns detailed nutritional info for a specific item."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.query.all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    
    if not matches:
        return f"I couldn't find an item called '{item_name}'."
    
    item = all_items[matches[0]]
    return (f"{item.name} Nutrition:\n"
            f"- Calories: {item.calories}\n"
            f"- Protein: {item.protein}g\n"
            f"- Carbs: {item.carbs}g\n"
            f"- Fat: {item.fat}g\n"
            f"- Diet: {item.diet}\n"
            f"- Ingredients: {item.ingredients}")

def add_to_cart(item_name: str, quantity: int = 1, confirm_allergy: bool = False) -> str:
    """Adds an item to the user's cart. Handles fuzzy matching."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.query.all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    
    if not matches:
        return f"I couldn't find '{item_name}' to add to your cart."
    
    real_item = all_items[matches[0]]
    
    # --- Allergy Check ---
    if current_user.allergies and not confirm_allergy:
        user_allergies = [a.strip().lower() for a in current_user.allergies.split(",")]
        item_ingredients = real_item.ingredients.lower() if real_item.ingredients else ""
        detected_allergens = [allergen for allergen in user_allergies if allergen in item_ingredients]
        
        if detected_allergens:
            return f"WARNING: I cannot add {real_item.name} to your cart because it contains {', '.join(detected_allergens)}, which matches your allergy profile. Please confirm if you really want this."
    # ---------------------

    # Check for existing cart item
    existing = CartItem.query.filter_by(user_id=current_user.id, item_name=real_item.name).first()
    if existing:
        existing.quantity += quantity
    else:
        new_item = CartItem(
            user_id=current_user.id, 
            item_name=real_item.name, 
            quantity=quantity, 
            unit_price=real_item.price
        )
        db.session.add(new_item)
    
    db.session.commit()
    return f"Added {quantity}x {real_item.name} to your cart."

def view_cart() -> str:
    """Returns the current user's cart contents."""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return "Your cart is empty."
    
    total = sum(item.quantity * item.unit_price for item in cart_items)
    lines = [f"- {item.quantity}x {item.item_name} (${item.quantity * item.unit_price:.2f})" for item in cart_items]
    return "Your Cart:\n" + "\n".join(lines) + f"\nTotal: ${total:.2f}"

def remove_from_cart(item_name: str) -> str:
    """Removes an item from the cart."""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    target = None
    for item in cart_items:
        if item_name.lower() in item.item_name.lower():
            target = item
            break
    
    if target:
        db.session.delete(target)
        db.session.commit()
        return f"Removed {target.item_name} from your cart."
    return f"Could not find {item_name} in your cart."

def update_user_profile(preferences: str = None, allergies: str = None) -> str:
    """Updates user preferences or allergies. Overwrites existing values."""
    if preferences:
        current_user.preferences = preferences
    if allergies:
        current_user.allergies = allergies
    
    db.session.commit()
    return "Profile updated successfully."

def learn_user_preference(preference: str) -> str:
    """Learns a new user preference and adds it to their long-term profile."""
    if not preference:
        return "No preference provided."
    
    current_prefs = current_user.preferences or ""
    # Avoid duplicates
    if preference.lower() in current_prefs.lower():
        return f"I already know you like {preference}."
        
    new_prefs = f"{current_prefs}, {preference}" if current_prefs else preference
    current_user.preferences = new_prefs
    db.session.commit()
    return f"I've noted that you like {preference}."

def place_order() -> str:
    """Finalizes the order and clears the cart."""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return "Cannot place order: Cart is empty."
    
    total = sum(item.quantity * item.unit_price for item in cart_items)
    new_order = Order(user_id=current_user.id, total_price=total)
    db.session.add(new_order)
    db.session.flush()
    
    for item in cart_items:
        db.session.add(OrderItem(order_id=new_order.id, item_name=item.item_name, quantity=item.quantity, unit_price=item.unit_price))
    
    # Clear cart
    CartItem.query.filter_by(user_id=current_user.id).delete()
    
    # Create bill
    bill_msg = f"Order #{new_order.id} confirmed. Total: ${total:.2f}"
    db.session.add(InboxMessage(user_id=current_user.id, subject="Order Confirmation", message=bill_msg))
    
    db.session.commit()
    return f"Order #{new_order.id} placed successfully! Total: ${total:.2f}."

# ============ NEW TOOLS ============

def get_cooking_tips(item_name: str) -> str:
    """Returns cooking tips and preparation information for a dish."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.query.all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    
    if not matches:
        return f"I couldn't find a dish called '{item_name}'."
    
    item = all_items[matches[0]]
    
    # Generate cooking tips based on the dish type and ingredients
    tips = f"Cooking Tips for {item.name}:\n"
    tips += f"- Main Ingredients: {item.ingredients}\n"
    
    # Add category-specific tips
    if "curry" in item.name.lower() or "masala" in item.name.lower():
        tips += "- Slow cooking brings out the best flavors in curries.\n"
        tips += "- Toast your spices before adding them for a deeper flavor.\n"
    elif "biryani" in item.name.lower():
        tips += "- Use aged basmati rice for the best texture.\n"
        tips += "- Layer the rice and meat for authentic dum-style cooking.\n"
    elif "tandoor" in item.name.lower() or "tikka" in item.name.lower():
        tips += "- Marinate overnight for maximum flavor penetration.\n"
        tips += "- High heat is essential - use a very hot oven or grill.\n"
    elif "dal" in item.name.lower() or "lentil" in item.name.lower():
        tips += "- Finish with a tadka (tempered spices in ghee) for authentic taste.\n"
        tips += "- Pressure cooking makes lentils creamy and perfectly textured.\n"
    else:
        tips += "- Fresh ingredients always make a difference.\n"
        tips += "- Balance your spices according to taste.\n"
    
    tips += f"- Diet Type: {item.diet}"
    return tips

def submit_rating(item_name: str, rating: int, comment: str = "") -> str:
    """Submits a rating (1-5) for a dish."""
    if not 1 <= rating <= 5:
        return "Rating must be between 1 and 5 stars."
    
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.query.all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    
    if not matches:
        return f"I couldn't find a dish called '{item_name}'."
    
    real_item = all_items[matches[0]]
    
    # Store as inbox message for now (could be a Rating table in real app)
    feedback_msg = f"Rating for {real_item.name}: {'⭐' * rating} ({rating}/5)\n"
    if comment:
        feedback_msg += f"Comment: {comment}"
    
    db.session.add(InboxMessage(
        user_id=current_user.id, 
        subject=f"Rating Submitted: {real_item.name}", 
        message=feedback_msg
    ))
    db.session.commit()
    
    return f"Thank you! Your {rating}-star rating for {real_item.name} has been recorded."

def get_item_ratings(item_name: str) -> str:
    """Returns the average rating for a dish (simulated for demo)."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.query.all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    
    if not matches:
        return f"I couldn't find a dish called '{item_name}'."
    
    real_item = all_items[matches[0]]
    
    # Simulated ratings (in real app, would query a Ratings table)
    import random
    avg_rating = round(random.uniform(4.0, 5.0), 1)
    num_reviews = random.randint(15, 150)
    
    return f"{real_item.name} has an average rating of {avg_rating}/5 based on {num_reviews} reviews."

def get_pairings(item_name: str) -> str:
    """Returns drink pairings for a dish."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.query.all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    
    if not matches:
        return f"I couldn't find a dish called '{item_name}'."
    
    item = all_items[matches[0]]
    name = item.name.lower()
    
    # Simple Pairing Logic
    if "spicy" in item.description.lower() or "vindaloo" in name:
        return f"Pairing for {item.name}: A sweet Mango Lassi or a light Riesling wine helps cool the spice."
    elif "creamy" in item.description.lower() or "makhani" in name:
        return f"Pairing for {item.name}: A full-bodied Chardonnay or a cold Kingfisher beer cuts through the richness."
    elif "grilled" in item.description.lower() or "tikka" in name:
        return f"Pairing for {item.name}: A light Pinot Noir or a refreshing Lime Soda complements the smoky flavors."
    elif "biryani" in name:
        return f"Pairing for {item.name}: A spiced Masala Chai or a medium-bodied Shiraz works beautifully."
    else:
        return f"Pairing for {item.name}: A classic Masala Lemonade or Sparkling Water is always a good choice."

def book_table(party_size: int, date: str, time: str) -> str:
    """Simulates booking a table."""
    try:
        # Validate simple inputs
        if party_size < 1:
            return "Party size must be at least 1."
        
        # In a real app, we would validate date/time format and check DB availability
        import random
        conf_code = f"RES-{random.randint(1000, 9999)}"
        
        return f"Confirmed! Table for {party_size} on {date} at {time} has been booked. Your confirmation code is {conf_code}. We look forward to hosting you!"
    except Exception as e:
        return f"There was an error processing your reservation: {e}"
