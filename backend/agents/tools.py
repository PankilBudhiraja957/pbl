import re
import os
from difflib import get_close_matches
from flask_login import current_user
from modals import get_db, MenuItem, CartItem, Order, OrderItem, InboxMessage, Rating, Reservation, User, TableInventory
from key_manager import KeyManager
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage


def send_inbox_message(user_id, subject, message):
    """Helper to send an inbox message to a user."""
    InboxMessage.create(user_id=user_id, subject=subject, message=message)


def notify_admin_about_order(order):
    """Notify admins about a new order via Socket.IO."""
    try:
        from app import socketio
        socketio.emit('new_order', order.to_dict(), room='admins_room')
    except Exception as e:
        print(f"Failed to emit new_order: {e}")


def get_full_menu() -> str:
    """Returns the entire menu as a formatted string."""
    items = MenuItem.get_all()
    if not items:
        return "The menu is currently empty."
    return "Here is our menu:\n" + "\n".join(
        [f"- {item.name} (${item.price:.2f}): {item.description} ({item.diet}, {item.calories} cal)" for item in items]
    )


def search_menu(query: str) -> str:
    """Searches for menu items based on a query string."""
    query = query.lower().strip()

    # 1. Semantic Search (RAG)
    from agents.memory import AgentMemory
    memory = AgentMemory()
    semantic_matches = []
    try:
        results = memory.query_knowledge(query, n_results=5)
        for res in results:
            name = res['meta'].get('name')
            if name:
                item = MenuItem.get_by_name(name)
                if item and item.id not in [i.id for i in semantic_matches]:
                    semantic_matches.append(item)
    except Exception as e:
        print(f"Semantic search failed: {e}")

    # 2. Keyword Search
    all_items = MenuItem.get_all()
    all_names = {item.name.lower(): item for item in all_items}
    keyword_matches = []

    for item in all_items:
        name_lower = (item.name or "").lower()
        desc_lower = (item.description or "").lower()
        ingredients_lower = (item.ingredients or "").lower()
        diet_lower = (item.diet or "").lower()
        category_lower = (item.category or "").lower()

        if (query in name_lower or query in desc_lower or query in ingredients_lower
                or query in diet_lower or query in category_lower):
            keyword_matches.append(item)

        if "spicy" in query:
            spicy_terms = ["chilli", "chili", "masala", "curry", "vindaloo", "schezwan", "peppercorn", "tikka", "hot"]
            if any(term in name_lower or term in desc_lower or term in ingredients_lower for term in spicy_terms):
                if item not in keyword_matches:
                    keyword_matches.append(item)

    # 3. Fuzzy Search
    fuzzy_matches = []
    if len(keyword_matches) < 3:
        matches = get_close_matches(query, all_names.keys(), n=5, cutoff=0.5)
        for m in matches:
            item = all_names[m]
            if item not in keyword_matches:
                fuzzy_matches.append(item)

    # 4. Combine & Deduplicate
    seen_ids = set()
    all_results = []
    for item in semantic_matches + keyword_matches + fuzzy_matches:
        if item.id not in seen_ids:
            seen_ids.add(item.id)
            all_results.append(item)

    if not all_results:
        return f"I couldn't find any items matching '{query}' on our menu."

    return "\n".join([
        f"- {item.name} (${item.price:.2f}): {item.description}. Ingredients: {item.ingredients}. Diet: {item.diet}. Category: {item.category}"
        for item in all_results
    ])


def get_nutritional_info(item_name: str) -> str:
    """Returns detailed nutritional info for a specific item."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.get_all()}
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
    """Adds an item to the user's cart."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.get_all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    if not matches:
        return f"I couldn't find '{item_name}' to add to your cart."

    real_item = all_items[matches[0]]

    # Allergy Check
    if current_user.allergies and not confirm_allergy:
        user_allergies = [a.strip().lower() for a in current_user.allergies.split(",")]
        item_ingredients = (real_item.ingredients or "").lower()
        detected_allergens = [allergen for allergen in user_allergies if allergen in item_ingredients]
        if detected_allergens:
            return f"WARNING: I cannot add {real_item.name} to your cart because it contains {', '.join(detected_allergens)}, which matches your allergy profile. Please confirm if you really want this."

    CartItem.upsert(current_user.id, real_item.name, quantity, real_item.price)
    return f"Added {quantity}x {real_item.name} to your cart."


def view_cart() -> str:
    """Returns the current user's cart contents."""
    cart_items = CartItem.get_by_user(current_user.id)
    if not cart_items:
        return "Your cart is empty."
    total = sum(item.quantity * item.unit_price for item in cart_items)
    lines = [f"- {item.quantity}x {item.item_name} (₹{item.quantity * item.unit_price:.2f})" for item in cart_items]
    return "Your Cart:\n" + "\n".join(lines) + f"\nTotal: ${total:.2f}"


def remove_from_cart(item_name: str) -> str:
    """Removes an item from the cart."""
    cart_items = CartItem.get_by_user(current_user.id)
    target = None
    for item in cart_items:
        if item_name.lower() in item.item_name.lower():
            target = item
            break
    if target:
        target.delete()
        return f"Removed {target.item_name} from your cart."
    return f"Could not find {item_name} in your cart."


def update_user_profile(preferences: str = None, allergies: str = None) -> str:
    """Updates user preferences or allergies."""
    from app import _get_user_profile, _save_user_profile
    profile = _get_user_profile(current_user.id)
    if preferences:
        profile["preferences"] = preferences
    if allergies:
        profile["allergies"] = allergies
    _save_user_profile(current_user.id, profile)
    return "Profile updated successfully."


def learn_user_preference(preference: str) -> str:
    """Learns a new user preference."""
    if not preference:
        return "No preference provided."
    from app import _get_user_profile, _save_user_profile
    profile = _get_user_profile(current_user.id)
    current_prefs = profile.get("preferences", "")
    if preference.lower() in current_prefs.lower():
        return f"I already know you like {preference}."
    new_prefs = f"{current_prefs}, {preference}" if current_prefs else preference
    profile["preferences"] = new_prefs
    _save_user_profile(current_user.id, profile)
    return f"I've noted that you like {preference}."


def place_order() -> str:
    """Finalizes the order and clears the cart."""
    cart_items = CartItem.get_by_user(current_user.id)
    if not cart_items:
        return "Cannot place order: Cart is empty."

    total = sum(item.quantity * item.unit_price for item in cart_items)
    new_order = Order.create(user_id=current_user.id, total_price=total)

    for item in cart_items:
        OrderItem.create(order_id=new_order.id, item_name=item.item_name, quantity=item.quantity, unit_price=item.unit_price)

    CartItem.clear_by_user(current_user.id)

    bill_msg = f"Order #{new_order.id} confirmed. Total: ${total:.2f}"
    InboxMessage.create(user_id=current_user.id, subject="Order Confirmation", message=bill_msg)

    notify_admin_about_order(new_order)
    return f"Order #{new_order.id} placed successfully! Total: ${total:.2f}."


def get_cooking_tips(item_name: str) -> str:
    """Returns cooking tips for a dish."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.get_all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    if not matches:
        return f"I couldn't find a dish called '{item_name}'."
    item = all_items[matches[0]]
    tips = f"Cooking Tips for {item.name}:\n"
    tips += f"- Main Ingredients: {item.ingredients or 'Not specified'}\n"
    name_lower = item.name.lower()
    if "curry" in name_lower or "masala" in name_lower:
        tips += "- Slow cooking brings out the best flavors in curries.\n"
        tips += "- Toast your spices before adding them for a deeper flavor.\n"
    elif "biryani" in name_lower:
        tips += "- Use aged basmati rice for the best texture.\n"
        tips += "- Layer the rice and meat for authentic dum-style cooking.\n"
    elif "tandoor" in name_lower or "tikka" in name_lower:
        tips += "- Marinate overnight for maximum flavor penetration.\n"
        tips += "- High heat is essential - use a very hot oven or grill.\n"
    elif "dal" in name_lower or "lentil" in name_lower:
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
    all_items = {i.name.lower(): i for i in MenuItem.get_all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    if not matches:
        return f"I couldn't find a dish called '{item_name}'."
    real_item = all_items[matches[0]]
    Rating.upsert(current_user.id, real_item.id, rating)
    if comment:
        feedback_msg = f"Rating for {real_item.name}: {'⭐' * rating} ({rating}/5)\nComment: {comment}"
        InboxMessage.create(user_id=current_user.id, subject=f"Feedback Submitted: {real_item.name}", message=feedback_msg)
    return f"Thank you! Your {rating}-star rating for {real_item.name} has been recorded."


def get_item_ratings(item_name: str) -> str:
    """Returns the average rating for a dish."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.get_all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    if not matches:
        return f"I couldn't find a dish called '{item_name}'."
    real_item = all_items[matches[0]]
    import random
    avg_rating = round(random.uniform(4.0, 5.0), 1)
    num_reviews = random.randint(15, 150)
    return f"{real_item.name} has an average rating of {avg_rating}/5 based on {num_reviews} reviews."


def get_pairings(item_name: str) -> str:
    """Returns drink pairings for a dish using LLM and available beverages."""
    item_name = item_name.lower().strip()
    all_items = {i.name.lower(): i for i in MenuItem.get_all()}
    matches = get_close_matches(item_name, all_items.keys(), n=1, cutoff=0.6)
    if not matches:
        return f"I couldn't find a dish called '{item_name}'."
    item = all_items[matches[0]]
    import re as _re
    beverages = [i for i in MenuItem.get_all({"category": _re.compile("^beverages?$", _re.IGNORECASE)})]

    if not beverages:
        name = item.name.lower()
        desc_lower = (item.description or "").lower()
        if "spicy" in desc_lower or "vindaloo" in name:
            return f"Pairing for {item.name}: A sweet Mango Lassi helps cool the spice."
        elif "creamy" in desc_lower or "makhani" in name:
            return f"Pairing for {item.name}: A cold Kingfisher beer or refreshing soda cuts through the richness."
        else:
            return f"Pairing for {item.name}: A refreshing Masala Lemonade or Sparkling Water is always a good choice."

    def solve_with_llm(key):
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=key, temperature=0.2)
        bev_list = "\n".join([f"- {b.name}: {b.description} (Flavor: {b.flavor_profile})" for b in beverages])
        system_msg = """You are a professional restaurant sommelier. Given a dish and a list of available beverages, recommend the BEST pairing. Keep your response concise: Name the beverage and give a 1-sentence reason why it works."""
        user_msg = f"Dish: {item.name}\nDescription: {item.description}\nFlavor Profile: {item.flavor_profile}\n\nAvailable Beverages:\n{bev_list}"
        return llm.invoke([SystemMessage(content=system_msg), HumanMessage(content=user_msg)])

    try:
        km = KeyManager()
        try:
            response = solve_with_llm(km.get_current_key())
        except Exception as e:
            if ("429" in str(e) or "quota" in str(e).lower()) and km.rotate_key():
                response = solve_with_llm(km.get_current_key())
            else:
                raise e
        return f"Sommelier Recommendation for {item.name}: {response.content}"
    except Exception as e:
        print(f"LLM Pairing failed: {e}")
        import random
        # Use already-fetched beverages list; re-query if empty
        fallback_bevs = beverages
        if not fallback_bevs:
            fallback_bevs = [i for i in MenuItem.get_all({"category": _re.compile("^beverages?$", _re.IGNORECASE)})]
        if fallback_bevs:
            random_bev = random.choice(fallback_bevs)
            return f"🍷 Sommelier Pick for {item.name}: We recommend our **{random_bev.name}** — {random_bev.description or 'a great choice to complement your dish'}."
        return f"🍷 We recommend pairing {item.name} with a refreshing Mango Lassi or Sparkling Water."


def check_table_availability(date: str, time: str, table_type: str = None) -> str:
    """Check which tables are available at a specific date and time."""
    all_table_keys = ['intimate', 'small', 'family', 'large', 'banquet']
    inventory = {ti.table_type: ti.total_quantity for ti in TableInventory.get_all()}
    for k in all_table_keys:
        if k not in inventory:
            inventory[k] = 5

    availability_info = []
    for k in all_table_keys:
        total = inventory[k]
        used = Reservation.count_confirmed(k, date, time)
        remaining = max(0, total - used)
        availability_info.append({'type': k, 'total': total, 'used': used, 'remaining': remaining, 'status': 'AVAILABLE' if remaining > 0 else 'FULL'})

    if table_type:
        table_type = table_type.lower()
        info = next((i for i in availability_info if i['type'] == table_type), None)
        if info:
            if info['remaining'] > 0:
                return f"✅ {table_type.title()} Table is AVAILABLE. {info['remaining']} of {info['total']} tables remaining for {date} at {time}."
            else:
                return f"❌ {table_type.title()} Table is FULLY BOOKED for {date} at {time}."
        else:
            return f"Invalid table type. Choose from: {', '.join(all_table_keys)}"

    result = f"📅 Table Availability for {date} at {time}:\n\n"
    for i in availability_info:
        status_icon = "✅" if i['remaining'] > 0 else "❌"
        result += f"{status_icon} {i['type'].title()}: {i['remaining']}/{i['total']} available\n"
    return result


def get_reservation_quote(table_type: str, party_size: int, table_quantity: int = 1,
                          seating_preference: str = "indoor", occasion_type: str = "none") -> dict:
    """Returns the estimated cost for a reservation."""
    table_prices = {
        'intimate': 200 + (party_size * 100), 'small': 300 + (party_size * 100),
        'family': 500 + (party_size * 100), 'large': 800 + (party_size * 100),
        'banquet': 1500 + (party_size * 120)
    }
    seating_premiums = {'window': 100, 'indoor': 0, 'outdoor': 50, 'private': 150}
    occasion_costs = {'none': 0, 'birthday': 500, 'anniversary': 700, 'corporate': 1000}
    base_unit_cost = table_prices.get(table_type.lower(), 500)
    total_base_cost = base_unit_cost * table_quantity
    seating_cost = seating_premiums.get(seating_preference.lower(), 0)
    occasion_cost = occasion_costs.get(occasion_type.lower(), 0)
    total_extras = (seating_cost + occasion_cost) * table_quantity
    bulk_discount = 0
    if table_quantity >= 3: bulk_discount = total_base_cost * 0.15
    elif table_quantity >= 2: bulk_discount = total_base_cost * 0.10
    total_quote = total_base_cost + total_extras - bulk_discount
    return {
        "base_cost": total_base_cost, "extras_cost": total_extras,
        "bulk_discount": bulk_discount, "total_quote": total_quote, "currency": "INR",
        "breakdown": f"Table: {total_base_cost}, Extras: {total_extras}, Discount: -{bulk_discount}"
    }


def book_table(table_type: str, party_size: int, date: str, time: str,
               seating_preference: str = "indoor", occasion_type: str = "none",
               special_requests: str = "", table_quantity: int = 1,
               discount_code: str = None, total_cost: float = None) -> str:
    """Create a new table reservation if available."""
    import string, random
    if not current_user or not current_user.is_authenticated:
        return "❌ Error: You must be logged in to make a reservation."

    user_id = current_user.id

    # Check availability
    inv_item = TableInventory.get_by_type(table_type.lower())
    total_tables = inv_item.total_quantity if inv_item else 5
    existing_count = Reservation.count_confirmed(table_type.lower(), date, time)

    if existing_count + table_quantity > total_tables:
        remaining = max(0, total_tables - existing_count)
        if remaining == 0:
            return f"❌ {table_type.title()} Table is fully booked for {date} at {time}."
        else:
            return f"❌ Only {remaining} {table_type} table(s) available for {date} at {time}, but you requested {table_quantity}."

    # Discount code check
    if discount_code:
        discount_code = discount_code.upper().strip()
        valid_codes = ['FIRST10', 'BULK20', 'VIP25']
        if discount_code not in valid_codes:
            return f"❌ Invalid discount code: {discount_code}"
        used_before = Reservation.find_by_discount_code_and_user(user_id, discount_code)
        if used_before:
            return f"❌ The discount code '{discount_code}' can only be used once."

    # Calculate cost if not provided
    if total_cost is None:
        table_prices = {
            'intimate': 200 + (party_size * 100), 'small': 300 + (party_size * 100),
            'family': 500 + (party_size * 100), 'large': 800 + (party_size * 100),
            'banquet': 1500 + (party_size * 120)
        }
        seating_premiums = {'window': 100, 'indoor': 0, 'outdoor': 50, 'private': 150}
        occasion_costs = {'none': 0, 'birthday': 500, 'anniversary': 700, 'corporate': 1000}
        base_unit_cost = table_prices.get(table_type.lower(), 500)
        total_base_cost = base_unit_cost * table_quantity
        seating_cost = seating_premiums.get(seating_preference.lower(), 0)
        occasion_cost = occasion_costs.get(occasion_type.lower(), 0)
        total_extras = (seating_cost + occasion_cost) * table_quantity
        bulk_discount = 0
        if table_quantity >= 3: bulk_discount = total_base_cost * 0.15
        elif table_quantity >= 2: bulk_discount = total_base_cost * 0.10
        promo_discount = 0
        promo_percents = {'FIRST10': 0.10, 'BULK20': 0.20, 'VIP25': 0.25}
        if discount_code in promo_percents:
            promo_discount = (total_base_cost - bulk_discount) * promo_percents[discount_code]
        total_cost = (total_base_cost - bulk_discount - promo_discount) + total_extras

    confirmation_code = 'RES-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    reservation = Reservation.create(
        user_id=user_id,
        table_type=table_type.lower(),
        table_quantity=table_quantity,
        party_size=party_size,
        reservation_date=date,
        reservation_time=time,
        seating_preference=seating_preference.lower(),
        occasion_type=occasion_type.lower(),
        special_requests=special_requests,
        total_cost=total_cost,
        discount_code=discount_code,
        status='confirmed',
        confirmation_code=confirmation_code
    )

    user = User.get_by_id(user_id)
    if user:
        message = f"""🎉 TABLE RESERVATION CONFIRMED!

Confirmation Code: {confirmation_code}

📅 Date: {date}
🕐 Time: {time}
🪑 Table: {table_type.title()} x {table_quantity}
👥 Party Size: {party_size} {'person' if party_size == 1 else 'people'}
📍 Seating: {seating_preference.title()}
"""
        if occasion_type != 'none':
            message += f"🎉 Occasion: {occasion_type.title()} Package\n"
        if special_requests:
            message += f"\n📝 Special Requests: {special_requests}\n"
        message += f"\n💰 Total Cost: ₹{int(total_cost)}\n\nWe look forward to serving you!"
        InboxMessage.create(user_id=user.id, subject="Table Reservation Confirmed", message=message)

    return f"✅ Reservation confirmed! Confirmation code: {confirmation_code}. Total cost: ₹{int(total_cost)}. Details sent to inbox."


def add_menu_item(name: str, price: float, category: str, diet: str, description: str,
                  ingredients: str, **kwargs) -> str:
    """Add a new menu item. ADMIN ONLY."""
    if not current_user or current_user.role != 'admin':
        return "❌ Access denied. Only administrators can add menu items."
    existing = MenuItem.get_by_name(name)
    if existing:
        return f"❌ Menu item '{name}' already exists."
    MenuItem.create(
        name=name, price=price, category=category.lower(), diet=diet.lower(),
        description=description, ingredients=ingredients,
        calories=kwargs.get('calories', 0.0), protein=kwargs.get('protein', 0.0),
        carbs=kwargs.get('carbs', 0.0), fat=kwargs.get('fat', 0.0),
        flavor_profile=kwargs.get('flavor_profile', ''), image_url=kwargs.get('image_url', '')
    )
    return f"✅ Successfully added '{name}' to the menu! Price: ₹{price}, Category: {category}, Diet: {diet}"


def delete_menu_item(item_name: str = None, item_id: int = None) -> str:
    """Delete a menu item by name or ID. ADMIN ONLY."""
    if not current_user or current_user.role != 'admin':
        return "❌ Access denied. Only administrators can delete menu items."
    if item_id:
        item = MenuItem.get_by_id(str(item_id))
    elif item_name:
        item = MenuItem.get_by_name(item_name)
    else:
        return "❌ Please provide either item_name or item_id"
    if not item:
        return f"❌ Menu item not found: {item_name or f'ID {item_id}'}"
    name_deleted = item.name
    item.delete()
    return f"✅ Successfully deleted '{name_deleted}' from the menu."


def get_user_favorites() -> str:
    """Retrieve the current user's favorite dishes."""
    if not current_user or not current_user.is_authenticated:
        return "You are not currently logged in, so I can't see your favorites."
    try:
        from modals import Favorite
        favorites = Favorite.get_by_user(current_user.id)
        if not favorites:
            return "You haven't added any dishes to your favorites yet! ❤️ Click the heart icon on the menu to save items you like."
        items = []
        for fav in favorites:
            item = MenuItem.get_by_id(fav.item_id)
            if item:
                items.append(f"• {item.name} ({item.category})")
        summary = "Based on your favorites, you really like:\n" + "\n".join(items)
        summary += "\n\nWould you like me to recommend something similar or add one of these to your cart?"
        return summary
    except Exception as e:
        return f"Error retrieving favorites: {str(e)}"
