import os
import re
import csv
import threading
import json
from flask import Flask, request, jsonify, session
from datetime import datetime
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from modals import (
    init_db, get_db,
    User, MenuItem, Order, OrderItem, InboxMessage,
    Reservation, Rating, CartItem, Favorite, TableInventory
)
from werkzeug.security import generate_password_hash
from difflib import get_close_matches
from flask_cors import CORS
from functools import wraps
from flask_socketio import SocketIO, emit, join_room
from api_recommendations import recommendations_bp

# --- AI & ML Imports ---
from agents.langgraph_orchestrator import LangGraphOrchestrator

# --- Load Environment Variables ---
load_dotenv()

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# --- MongoDB Connection ---
from pymongo import MongoClient

def _connect_mongo():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGODB_DB", "dinesmartai")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    mdb = client[db_name]
    print(f"--- [MongoDB] Connected to '{db_name}' ---")
    return mdb

mongo_db = _connect_mongo()
init_db(mongo_db)  # wire up modals.py

# --- Initialize Extensions ---
CORS(
    app,
    supports_credentials=True,
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    automatic_options=True
)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=20,
    ping_interval=25,
    async_mode='eventlet' if os.environ.get('USE_EVENTLET') else None
)

# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"message": "Authentication required"}), 401

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# --- Register Blueprints ---
app.register_blueprint(recommendations_bp)

# --- Helper Functions for Cart ---
def add_to_cart(user_id, item_name, quantity, unit_price):
    CartItem.upsert(user_id, item_name, quantity, unit_price)

def get_user_cart(user_id):
    return CartItem.get_by_user(user_id)

def remove_from_cart(user_id, item_name):
    CartItem.remove_by_user_and_name(user_id, item_name)

def clear_cart(user_id):
    CartItem.clear_by_user(user_id)

# --- Ordering Agent ---
def ordering_agent(user, cart):
    total_price = sum(item['qty'] * item['unit_price'] for item in cart)
    new_order = Order.create(user_id=user.id, total_price=total_price)

    for item in cart:
        OrderItem.create(
            order_id=new_order.id,
            item_name=item['name'],
            quantity=item['qty'],
            unit_price=item['unit_price']
        )

    bill_message = f"Order #{new_order.id} Confirmed!\n\nItems:\n"
    for item in cart:
        bill_message += f"- {item['qty']}x {item['name']} @ Rs {item['unit_price']:.2f} = Rs {item['qty'] * item['unit_price']:.2f}\n"
    bill_message += f"\nTotal: Rs {total_price:.2f}\n\nThank you for your order!"

    InboxMessage.create(user_id=user.id, subject=f"Order #{new_order.id} Confirmation", message=bill_message)

    try:
        # Reload order so items are populated
        fresh_order = Order.get_by_id(new_order.id)
        socketio.emit('new_order', fresh_order.to_dict(), room='admins_room')
    except Exception as e:
        print(f"Failed to emit new_order: {e}")

    return new_order

# --- CSV Migration ---
def migrate_csv_to_db():
    """Migrates menu from CSV to MongoDB and syncs with Vector DB (Brain)."""
    print("Starting fresh menu migration...")
    mongo_db.menu_items.delete_many({})

    csv_path = os.path.join(os.path.dirname(__file__), 'menu.csv')
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            docs = []
            for row in reader:
                docs.append({
                    "name": row.get('name'),
                    "description": row.get('description'),
                    "price": float(row.get('price', 0)),
                    "category": row.get('course'),
                    "ingredients": row.get('ingredients'),
                    "diet": row.get('diet'),
                    "calories": float(row.get('calories', 0)) if row.get('calories') else 0.0,
                    "protein": float(row.get('protein', 0)) if row.get('protein') else 0.0,
                    "carbs": float(row.get('carbs', 0)) if row.get('carbs') else 0.0,
                    "fat": float(row.get('fat', 0)) if row.get('fat') else 0.0,
                    "image_url": row.get('image_url', ''),
                    "cooking_tips": row.get('cooking_tips', ''),
                    "flavor_profile": row.get('flavor_profile', ''),
                })
            if docs:
                mongo_db.menu_items.insert_many(docs)
        print(f"Menu migrated from CSV to MongoDB ({len(docs)} items).")

    print("Checking Brain status...")
    brain_count = agent_memory.get_knowledge_count()
    all_items = MenuItem.get_all()

    if brain_count < len(all_items):
        print(f"Brain has {brain_count} items, MongoDB has {len(all_items)}. Starting sync...")
        indexing_tasks = []
        for item in all_items:
            text = f"{item.name}: {item.description}. Ingredients: {item.ingredients}. Diet: {item.diet}. Category: {item.category}."
            meta = {"id": item.id, "name": item.name or "", "category": item.category or "", "diet": item.diet or ""}
            indexing_tasks.append((text, meta))

        def background_indexer(tasks):
            import time
            print(f"--- [Sync] Indexing {len(tasks)} items to Brain ---")
            for text, meta in tasks:
                agent_memory.add_knowledge(text, meta)
                time.sleep(2)
            print("--- [Sync] Brain update complete ---")

        thread = threading.Thread(target=background_indexer, args=(indexing_tasks,))
        thread.daemon = True
        thread.start()
    else:
        print(f"Brain synced ({brain_count} items).")

# --- Agent Orchestrator Instance ---
orchestrator = None
from agents.memory import AgentMemory

agent_memory = AgentMemory()
chat_history_lock = threading.Lock()

# --- MongoDB Persistence for Chat / Reservations ---
def _get_chat_history(user_id):
    doc = mongo_db.chat_sessions.find_one({"user_id": str(user_id)}, {"_id": 0, "history": 1})
    return doc.get("history", []) if doc else []

def _save_chat_history(user_id, history):
    history = history[-20:]
    mongo_db.chat_sessions.update_one(
        {"user_id": str(user_id)},
        {"$set": {"history": history, "updated_at": datetime.utcnow()}},
        upsert=True,
    )

def _get_pending_reservation(user_id):
    doc = mongo_db.pending_reservations.find_one({"user_id": str(user_id)}, {"_id": 0, "details": 1})
    return doc.get("details", {}) if doc else {}

def _save_pending_reservation(user_id, details):
    mongo_db.pending_reservations.update_one(
        {"user_id": str(user_id)},
        {"$set": {"details": details, "updated_at": datetime.utcnow()}},
        upsert=True,
    )

def _clear_pending_reservation(user_id):
    mongo_db.pending_reservations.delete_one({"user_id": str(user_id)})

# --- MongoDB: User Profile Helpers ---
def _get_user_profile(user_id):
    doc = mongo_db.user_profiles.find_one({"user_id": str(user_id)}, {"_id": 0})
    return doc if doc else {}

def _save_user_profile(user_id, profile_data):
    # Always coerce allergies/preferences to string before saving
    for field in ("allergies", "preferences"):
        val = profile_data.get(field, "")
        if isinstance(val, list):
            profile_data[field] = ", ".join(str(v) for v in val if v)
        else:
            profile_data[field] = str(val) if val else ""
    profile_data["user_id"] = str(user_id)
    profile_data["updated_at"] = datetime.utcnow()
    mongo_db.user_profiles.update_one(
        {"user_id": str(user_id)},
        {"$set": profile_data},
        upsert=True
    )

def _merge_user_profile(user):
    base = {"id": user.id, "username": user.username, "role": user.role}
    profile = _get_user_profile(user.id)

    # Always coerce allergies/preferences to string (guard against array values from old data)
    allergies = profile.get("allergies", "")
    if isinstance(allergies, list):
        allergies = ", ".join(str(a) for a in allergies if a)
    base["allergies"] = allergies or ""

    preferences = profile.get("preferences", "")
    if isinstance(preferences, list):
        preferences = ", ".join(str(p) for p in preferences if p)
    base["preferences"] = preferences or ""

    base["calorie_goal"] = profile.get("calorie_goal")
    base["protein_goal"] = profile.get("protein_goal")
    base["carb_goal"] = profile.get("carb_goal")
    base["fat_goal"] = profile.get("fat_goal")
    return base

# --- Helpers ---
def _format_money(value):
    try:
        return f"Rs {float(value):.2f}"
    except (TypeError, ValueError):
        return "Rs 0.00"

def _build_ai_backend_context(user, chat_history):
    menu_items = MenuItem.get_all()
    menu_items.sort(key=lambda x: (x.category or "", x.name or ""))
    cart_items = CartItem.get_by_user(user.id)
    favorite_rows = Favorite.get_by_user(user.id)
    favorite_ids = [row.item_id for row in favorite_rows]
    favorite_items = [MenuItem.get_by_id(fid) for fid in favorite_ids if fid]
    favorite_items = [i for i in favorite_items if i]
    recent_orders = Order.get_by_user(user.id)[:5]
    reservations = Reservation.get_by_user(user.id)[:5]

    merged_user = _merge_user_profile(user)
    lines = [
        "BACKEND CONTEXT FOR DINESMARTAI",
        "Use this database context together with the latest user message.",
        "",
        "Current user:",
        f"- id: {merged_user['id']}",
        f"- username: {merged_user['username']}",
        f"- role: {merged_user['role']}",
        f"- allergies: {merged_user['allergies'] or 'none'}",
        f"- preferences: {merged_user['preferences'] or 'none'}",
        f"- nutrition goals: calories={merged_user['calorie_goal'] or 'unset'}, protein={merged_user['protein_goal'] or 'unset'}, carbs={merged_user['carb_goal'] or 'unset'}, fat={merged_user['fat_goal'] or 'unset'}",
        "",
        "Last 3 chat messages:",
    ]
    recent_messages = chat_history[-3:]
    if recent_messages:
        for msg in recent_messages:
            lines.append(f"- {msg.get('role', 'unknown')}: {msg.get('content', '')}")
    else:
        lines.append("- none")

    lines.extend(["", "Current cart:"])
    if cart_items:
        for item in cart_items:
            lines.append(f"- {item.quantity} x {item.item_name} @ {_format_money(item.unit_price)}")
    else:
        lines.append("- empty")

    lines.extend(["", "Favorites:"])
    if favorite_items:
        for item in favorite_items:
            lines.append(f"- {item.name} ({item.category or 'uncategorized'}, {item.diet or 'diet unknown'}, {_format_money(item.price)})")
    else:
        lines.append("- none")

    lines.extend(["", "Recent orders:"])
    if recent_orders:
        for order in recent_orders:
            order_items_str = ", ".join(f"{i.quantity} x {i.item_name}" for i in order.items) or "no items"
            lines.append(f"- order #{order.id}: {order.status}, total {_format_money(order.total_price)}, items: {order_items_str}")
    else:
        lines.append("- none")

    lines.extend(["", "Recent reservations:"])
    if reservations:
        for r in reservations:
            lines.append(
                f"- {r.confirmation_code or 'no-code'}: {r.party_size} people, "
                f"{r.table_type} table, {r.reservation_date} at {r.reservation_time}, "
                f"status={r.status}, occasion={r.occasion_type or 'none'}"
            )
    else:
        lines.append("- none")

    # Send compact menu — name, id, diet, price, calories only (saves ~60% tokens)
    lines.extend(["", f"Full menu ({len(menu_items)} items):"])
    for item in menu_items:
        lines.append(
            f"- {item.name} [id={item.id}] {item.diet or '?'} | {item.category or '?'} | "
            f"{_format_money(item.price)} | {item.calories or 0}cal | {item.protein or 0}g protein"
        )

    latest_res = Reservation.get_latest_by_user(user.id)
    active_reservation = {}
    if latest_res:
        active_reservation = {"status": (latest_res.status or "UNKNOWN").upper(), "code": latest_res.confirmation_code}

    all_menu_item_names = [item.name for item in menu_items]
    target_party_menu = []
    for msg in chat_history[-5:]:
        if isinstance(msg, dict):
            role = msg.get('role', '').lower()
            content = msg.get('content', '')
        else:
            role = 'assistant' if hasattr(msg, 'type') and msg.type == 'ai' else 'user'
            content = msg.content if hasattr(msg, 'content') else ''
        if role in ['assistant', 'ai']:
            for name in all_menu_item_names:
                if name.lower() in content.lower() and name not in target_party_menu:
                    target_party_menu.append(name)

    current_cart_state = [{"item": item.item_name, "qty": item.quantity} for item in cart_items]
    session_state = {
        "active_reservation": active_reservation,
        "target_party_menu": target_party_menu,
        "current_cart_state": current_cart_state
    }
    lines.extend(["", "STRUCTURAL SESSION STATE OBJECT:", json.dumps(session_state, indent=2)])
    return "\n".join(lines)

# --- Reservation Helpers ---
MONTH_LOOKUP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

def _infer_table_type(party_size):
    if not party_size:
        return None
    if party_size <= 2: return "intimate"
    if party_size <= 5: return "small"
    if party_size <= 8: return "family"
    if party_size <= 15: return "large"
    return "banquet"

def _extract_reservation_details(text):
    lower = text.lower()
    details = {}
    party_match = re.search(r"\b(\d+)\s*(?:people|persons|person|guests|guest|friends|friend|ppl)\b", lower)
    if party_match:
        details["party_size"] = int(party_match.group(1))
    table_match = re.search(r"\b(intimate|small|family|large|banquet)\b", lower)
    if table_match:
        details["table_type"] = table_match.group(1)
    date_match = re.search(
        r"\b(\d{1,2})\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{4})\b",
        lower,
    )
    if date_match:
        day = int(date_match.group(1))
        month = MONTH_LOOKUP[date_match.group(2)]
        year = int(date_match.group(3))
        details["date"] = f"{year:04d}-{month:02d}-{day:02d}"
    time_matches = list(re.finditer(r"\b(\d{1,2})(?::(\d{2}))?\s*(?:p\.?m\.?|pm|a\.?m\.?|am)?\b", lower))
    for time_match in time_matches:
        raw = time_match.group(0)
        if not any(marker in raw for marker in ["am", "pm", "a.m", "p.m", ":"]):
            continue
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        if "p" in raw and hour < 12: hour += 12
        if "a" in raw and hour == 12: hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            details["time"] = f"{hour:02d}:{minute:02d}"
            break
    if "no special" in lower or "no occasion" in lower:
        details["occasion_type"] = "none"
    elif "birthday" in lower:
        details["occasion_type"] = "birthday"
    elif "anniversary" in lower:
        details["occasion_type"] = "anniversary"
    elif "corporate" in lower:
        details["occasion_type"] = "corporate"
    return details

def _is_reservation_related(text):
    lower = text.lower()
    return any(word in lower for word in ["book", "booking", "table", "reserve", "reservation", "people", "persons", "guests", "friends"])

def _is_confirmation(text):
    lower = text.lower().strip()
    return any(phrase in lower for phrase in [
        "yes", "correct", "confirm", "confirmed", "booking is correct",
        "that's correct", "that is correct", "ok", "okay", "fine", "book it",
        "no special occasion", "no special occassion", "no special"
    ])

def _missing_reservation_fields(details):
    return [field for field in ["party_size", "date", "time", "table_type"] if not details.get(field)]

def _is_menu_planning_request(text):
    lower = text.lower()
    return any(word in lower for word in ["menu", "suggest", "recommend", "budget", "party", "friends", "persons", "people", "accordingly", "enough", "naan", "bread"])

def _extract_budget(text):
    lower = text.lower().replace(",", "")
    match = re.search(r"(?:budget|under|within|around|rs|₹)\s*(?:rs\.?|₹)?\s*(\d{3,6})", lower)
    if not match:
        match = re.search(r"\b(\d{4,6})\b", lower)
    return int(match.group(1)) if match else None

def _find_menu_item(name):
    return MenuItem.find_ilike(name)

def _item_has_allergy(item, allergies):
    if not item or not allergies:
        return False
    text = f"{item.name or ''} {item.ingredients or ''}".lower()
    return any(allergy and allergy in text for allergy in allergies)

def _first_available_item(names, allergies):
    for name in names:
        item = _find_menu_item(name)
        if item and not _item_has_allergy(item, allergies):
            return item
    return None

def _build_group_menu_plan(user_message, user, chat_history=None):
    history_text = " ".join(msg.get("content", "") for msg in (chat_history or [])[-8:])
    details = _extract_reservation_details(user_message)
    if not details.get("party_size") and _is_menu_planning_request(user_message):
        details = _extract_reservation_details(f"{history_text} {user_message}")
    party_size = details.get("party_size")
    if not party_size or not _is_menu_planning_request(user_message):
        return None

    merged_user = _merge_user_profile(user)
    budget = _extract_budget(user_message) or _extract_budget(history_text)
    allergies = [a.strip().lower() for a in (merged_user['allergies'] or "").split(",") if a.strip()]
    non_veg = "non" in (merged_user['preferences'] or "").lower() or "fish" in user_message.lower() or "chicken" in user_message.lower()

    starter_veg = _first_available_item(["Hara Bhara Kebab", "Tandoori Gobi", "Samosa Plate"], allergies)
    starter_nonveg = _first_available_item(["Amritsari Fish Fry", "Chicken Malai Tikka", "Seekh Kebab"], allergies)
    main_veg = _first_available_item(["Dal Makhani", "Baingan Bharta", "Sarson da Saag", "Chole Bhature"], allergies)
    main_nonveg = _first_available_item(["Butter Chicken", "Kadai Chicken", "Mutton Rogan Josh"], allergies)
    rice = _first_available_item(["Chicken Biryani" if non_veg else "Vegetable Biryani", "Jeera Rice", "Steamed Rice"], allergies)
    bread = _first_available_item(["Butter Naan", "Garlic Naan", "Tandoori Roti"], allergies)
    side = _first_available_item(["Boondi Raita", "Green Salad", "Papadum"], allergies)
    dessert = _first_available_item(["Gulab Jamun", "Gajar ka Halwa", "Kulfi"], allergies)
    drink = _first_available_item(["Fresh Lime Soda", "Sweet Lassi", "Salted Lassi", "Soft Drink"], allergies)

    quantities = []
    starter_qty = max(2, round(party_size * 0.6))
    if starter_veg: quantities.append((starter_veg, starter_qty))
    if starter_nonveg and non_veg: quantities.append((starter_nonveg, max(1, party_size // 2)))
    if main_veg: quantities.append((main_veg, max(1, round(party_size / 3))))
    if main_nonveg and non_veg: quantities.append((main_nonveg, max(1, round(party_size / 3))))
    if rice: quantities.append((rice, max(1, round(party_size / 3))))
    if bread: quantities.append((bread, max(party_size, 1)))
    if side: quantities.append((side, max(1, round(party_size / 4))))
    if dessert and budget and budget >= 3000: quantities.append((dessert, party_size))
    if drink and budget and budget >= 3500: quantities.append((drink, party_size))

    total = sum((item.price or 0) * qty for item, qty in quantities)
    if budget and total > budget:
        quantities = [(item, qty) for item, qty in quantities if item not in {dessert, drink}]
        total = sum((item.price or 0) * qty for item, qty in quantities)

    lines = [f"Here is a suggested menu plan for {party_size} people" + (f" within your Rs {budget} budget:" if budget else ":")]
    for item, qty in quantities:
        lines.append(f"- {qty} x {item.name} @ {_format_money(item.price)} = {_format_money((item.price or 0) * qty)}")
    lines.append(f"Total: {_format_money(total)}")
    if budget:
        lines.append(f"Remaining budget: {_format_money(max(budget - total, 0))}")
    lines.append(f"Split for {party_size} people: {_format_money(total / party_size)} per person")
    if bread:
        lines.append(f"Bread quantity: {party_size} {bread.name}, about 1 per person.")
    if allergies:
        lines.append(f"I avoided items matching your allergy profile: {', '.join(allergies)}.")
    return "\n".join(lines)

def _handle_pending_reservation(user_message, chat_history):
    user_id = current_user.id
    use_previous_details = any(phrase in user_message.lower() for phrase in ["previous", "already told", "same", "that booking", "this booking"])
    history_text = " ".join(msg.get("content", "") for msg in chat_history[-8:]) if use_previous_details else ""
    current_details = _extract_reservation_details(user_message)
    combined_details = _extract_reservation_details(f"{history_text} {user_message}")
    pending = _get_pending_reservation(user_id)

    if not pending and not (_is_reservation_related(user_message) or combined_details):
        return None

    if _is_menu_planning_request(user_message) and not current_details.get("date") and not current_details.get("time"):
        pending.update({k: v for k, v in current_details.items() if v is not None})
        if pending.get("party_size") and not pending.get("table_type"):
            pending["table_type"] = _infer_table_type(pending["party_size"])
        _save_pending_reservation(user_id, pending)
        return None

    pending.update({k: v for k, v in combined_details.items() if v is not None})
    pending.update({k: v for k, v in current_details.items() if v is not None})

    if pending.get("party_size") and not pending.get("table_type"):
        pending["table_type"] = _infer_table_type(pending["party_size"])
    if not pending.get("occasion_type"):
        pending["occasion_type"] = "none"

    _save_pending_reservation(user_id, pending)
    missing = _missing_reservation_fields(pending)
    if missing and _is_reservation_related(user_message):
        readable = {"party_size": "number of people", "date": "date", "time": "time", "table_type": "table type"}
        return "I have part of your booking. Please tell me the " + ", ".join(readable[m] for m in missing) + "."

    if not missing and _is_confirmation(user_message):
        from agents.tools import book_table
        result = book_table(
            pending["table_type"],
            int(pending["party_size"]),
            pending["date"],
            pending["time"],
            occasion_type=pending.get("occasion_type", "none"),
        )
        _clear_pending_reservation(user_id)
        return result

    return None

def route_user_request(user_message: str) -> str:
    global orchestrator
    if not orchestrator:
        orchestrator = LangGraphOrchestrator(socketio)
        print("--- [LangGraph Orchestrator] Initialized lazy-loaded. ---")

    chat_history = _get_chat_history(current_user.id)

    if _is_reservation_related(user_message):
        current_details = _extract_reservation_details(user_message)
        if current_details:
            pending = _get_pending_reservation(current_user.id)
            pending.update({k: v for k, v in current_details.items() if v is not None})
            if pending.get("party_size") and not pending.get("table_type"):
                pending["table_type"] = _infer_table_type(pending["party_size"])
            _save_pending_reservation(current_user.id, pending)

    user_msg_lower = user_message.lower()
    spatial_keywords = ["table", "book", "reserve", "reservation", "booking", "seating", "dine-in", "dine in"]
    culinary_keywords = ["menu", "suggest", "recommend", "food", "eat", "dish", "dishes", "meal", "special", "specials", "curry", "paneer", "chicken"]
    planning_keywords = ["plan", "suggest", "recommend", "how much", "quote", "price", "budget", "options", "details of reservation", "estimate", "suggest menu"]

    has_spatial = any(w in user_msg_lower for w in spatial_keywords)
    has_culinary = any(w in user_msg_lower for w in culinary_keywords)
    is_multi_intent = has_spatial and has_culinary
    is_planning = any(w in user_msg_lower for w in planning_keywords)

    if not is_multi_intent and not is_planning:
        reservation_reply = _handle_pending_reservation(user_message, chat_history)
        if reservation_reply:
            return reservation_reply
        menu_plan_reply = _build_group_menu_plan(user_message, current_user, chat_history)
        if menu_plan_reply:
            return menu_plan_reply

    backend_context = _build_ai_backend_context(current_user, chat_history)

    from langchain_core.messages import HumanMessage, AIMessage
    lc_history = []
    for msg in chat_history:
        if msg['role'] == 'user':
            lc_history.append(HumanMessage(content=msg['content']))
        else:
            lc_history.append(AIMessage(content=msg['content']))

    return orchestrator.route_request(user_message, lc_history, backend_context)

# --- Admin decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# API Routes
# ============================================================

@app.route("/api/dataspace", methods=["GET"])
def get_dataspace():
    return jsonify(agent_memory.get_dataspace_stream())

@app.route("/api/ai/debug-prompt", methods=["GET"])
@login_required
def get_ai_debug_prompt():
    if not orchestrator or not getattr(orchestrator, "last_prompt_debug", None):
        return jsonify({"message": "No AI prompt has been built yet."}), 404
    return jsonify(orchestrator.last_prompt_debug)

# --- Auth ---
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400
    if User.get_by_username(username):
        return jsonify({"message": "Username already exists"}), 409
    new_user = User.create(username=username, password=password)
    return jsonify({"message": "User created successfully"}), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.get_by_username(username)
    if user and user.check_password(password):
        login_user(user, remember=True)
        return jsonify(_merge_user_profile(user))
    return jsonify({"message": "Invalid credentials"}), 401

@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@app.route("/api/auth/status")
def auth_status():
    if current_user.is_authenticated:
        return jsonify({"isLoggedIn": True, "user": _merge_user_profile(current_user)})
    return jsonify({"isLoggedIn": False, "user": None})

# --- Profile ---
@app.route("/api/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        try:
            data = request.get_json()
            allergies_raw = data.get("allergies", "")
            allergies = ", ".join(str(a).strip() for a in allergies_raw if a) if isinstance(allergies_raw, list) else str(allergies_raw).strip()
            preferences_raw = data.get("preferences", "")
            preferences = ", ".join(str(p).strip() for p in preferences_raw if p) if isinstance(preferences_raw, list) else str(preferences_raw).strip()
            calorie_goal = data.get("calorie_goal")
            protein_goal = data.get("protein_goal")
            carb_goal = data.get("carb_goal")
            fat_goal = data.get("fat_goal")
            if not all([calorie_goal, protein_goal, carb_goal, fat_goal]) and preferences:
                try:
                    prefs = preferences.lower().replace(" ", "").split(",")
                    for pref in prefs:
                        if pref.startswith("calories="): calorie_goal = float(pref.split("=")[1])
                        elif pref.startswith("protein="): protein_goal = float(pref.split("=")[1])
                        elif pref.startswith("carb="): carb_goal = float(pref.split("=")[1])
                        elif pref.startswith("fat="): fat_goal = float(pref.split("=")[1])
                except Exception as e:
                    print(f"Error parsing nutrition goals: {e}")
            _save_user_profile(current_user.id, {
                "username": current_user.username,
                "allergies": allergies,
                "preferences": preferences,
                "calorie_goal": calorie_goal,
                "protein_goal": protein_goal,
                "carb_goal": carb_goal,
                "fat_goal": fat_goal,
            })
            return jsonify({"message": "Profile updated successfully"})
        except Exception as e:
            return jsonify({"message": f"Failed to update profile: {str(e)}"}), 500
    profile = _get_user_profile(current_user.id)
    return jsonify({
        "username": current_user.username,
        "allergies": profile.get("allergies", ""),
        "preferences": profile.get("preferences", ""),
        "calorie_goal": profile.get("calorie_goal"),
        "protein_goal": profile.get("protein_goal"),
        "carb_goal": profile.get("carb_goal"),
        "fat_goal": profile.get("fat_goal")
    })

# --- Menu ---
@app.route("/api/menu")
def get_menu_api():
    import re as _re
    diet_filter = request.args.get('diet')
    category_filter = request.args.get('category')
    search_term = request.args.get('search', '').lower()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    mongo_filter = {}
    if diet_filter and diet_filter != 'All':
        mongo_filter["diet"] = _re.compile(f"^{_re.escape(diet_filter)}$", _re.IGNORECASE)
    if category_filter and category_filter != 'All':
        mongo_filter["category"] = _re.compile(f"^{_re.escape(category_filter)}$", _re.IGNORECASE)
    if min_price is not None:
        mongo_filter.setdefault("price", {})["$gte"] = min_price
    if max_price is not None:
        mongo_filter.setdefault("price", {})["$lte"] = max_price

    items = MenuItem.get_all(mongo_filter)
    if search_term:
        items = [i for i in items if search_term in (i.name or '').lower() or search_term in (i.description or '').lower() or search_term in (i.ingredients or '').lower()]
    return jsonify([item.to_dict() for item in items])

@app.route("/api/menu/filtered")
@login_required
def get_filtered_menu_api():
    import re as _re
    diet_filter = request.args.get('diet')
    category_filter = request.args.get('category')
    search_term = request.args.get('search', '').lower()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    profile = _merge_user_profile(current_user)
    user_allergies = profile.get("allergies") or ""
    allergies_list = [a.strip().lower() for a in user_allergies.split(',') if a.strip()]

    mongo_filter = {}
    if diet_filter and diet_filter != 'All':
        mongo_filter["diet"] = _re.compile(f"^{_re.escape(diet_filter)}$", _re.IGNORECASE)
    if category_filter and category_filter != 'All':
        mongo_filter["category"] = _re.compile(f"^{_re.escape(category_filter)}$", _re.IGNORECASE)
    if min_price is not None:
        mongo_filter.setdefault("price", {})["$gte"] = min_price
    if max_price is not None:
        mongo_filter.setdefault("price", {})["$lte"] = max_price

    all_items = MenuItem.get_all(mongo_filter)
    filtered = []
    for item in all_items:
        ingredients_lower = (item.ingredients or "").lower()
        if any(a in ingredients_lower for a in allergies_list):
            continue
        if search_term:
            if search_term in (item.name or '').lower() or search_term in (item.description or '').lower() or search_term in ingredients_lower:
                filtered.append(item.to_dict())
        else:
            filtered.append(item.to_dict())
    return jsonify(filtered)

@app.route("/api/menu/rate", methods=["POST"])
@login_required
def rate_menu_item():
    data = request.get_json()
    item_id = data.get('itemId')
    rating_value = data.get('rating')
    comment = data.get('comment', '')
    if not item_id or not rating_value:
        return jsonify({"message": "Item ID and rating are required"}), 400
    item = MenuItem.get_by_id(item_id)
    if not item:
        return jsonify({"message": "Menu item not found"}), 404
    Rating.upsert(current_user.id, item_id, rating_value)
    if comment:
        feedback_msg = f"Rating for {item.name}: {'⭐' * rating_value} ({rating_value}/5)\nComment: {comment}"
        InboxMessage.create(user_id=current_user.id, subject=f"User Feedback: {item.name}", message=feedback_msg)
    return jsonify({"message": f"Rating for {item.name} submitted successfully!"}), 201

@app.route("/api/menu/pairings", methods=["POST"])
@login_required
def get_menu_pairings():
    data = request.get_json()
    # Accept both camelCase (frontend) and snake_case
    item_name = data.get('itemName') or data.get('item_name', '')
    item = MenuItem.find_ilike(item_name)
    if not item:
        return jsonify({"pairings": "Item not found.", "message": "Item not found"}), 404
    # Use the LLM-based pairing tool for a proper sommelier recommendation
    from agents.tools import get_pairings
    pairing_text = get_pairings(item.name)
    return jsonify({"pairings": pairing_text})

@app.route("/api/menu/cooking-tips", methods=["POST"])
@login_required
def get_cooking_tips():
    data = request.get_json()
    # Accept both camelCase (frontend) and snake_case
    item_name = data.get('itemName') or data.get('item_name', '')
    item = MenuItem.find_ilike(item_name)
    if not item:
        return jsonify({"tips": "Item not found"}), 404
    tips = item.cooking_tips or f"No specific cooking tips for {item.name}."
    return jsonify({"tips": tips})

# --- Admin Menu ---
@app.route("/api/admin/menu", methods=["POST"])
@login_required
@admin_required
def admin_add_dish():
    data = request.get_json()
    new_dish = MenuItem.create(
        name=data['name'],
        description=data.get('description', ''),
        price=float(data['price']),
        category=data.get('category', ''),
        ingredients=data.get('ingredients', ''),
        diet=data.get('diet', ''),
        calories=float(data.get('calories', 0)),
        protein=float(data.get('protein', 0)),
        carbs=float(data.get('carbs', 0)),
        fat=float(data.get('fat', 0)),
        flavor_profile=data.get('flavor_profile', ''),
        image_url=data.get('image_url', ''),
        cooking_tips=data.get('cooking_tips', ''),
    )
    return jsonify(new_dish.to_dict()), 201

@app.route("/api/admin/menu/<item_id>", methods=["DELETE"])
@login_required
@admin_required
def admin_delete_dish(item_id):
    item = MenuItem.get_by_id(item_id)
    if not item:
        return jsonify({"message": "Item not found"}), 404
    item.delete()
    return jsonify({"message": "Item deleted successfully"})

@app.route("/api/admin/menu/<item_id>", methods=["PUT"])
@login_required
@admin_required
def admin_update_dish(item_id):
    item = MenuItem.get_by_id(item_id)
    if not item:
        return jsonify({"message": "Item not found"}), 404
    data = request.get_json()
    item.name = data.get('name', item.name)
    item.description = data.get('description', item.description)
    item.price = float(data.get('price', item.price))
    item.category = data.get('category', item.category)
    item.ingredients = data.get('ingredients', item.ingredients)
    item.diet = data.get('diet', item.diet)
    item.save()
    return jsonify(item.to_dict())

# --- Admin Orders ---
@app.route("/api/admin/orders", methods=["GET"])
@login_required
@admin_required
def admin_get_orders():
    orders = Order.get_all()
    return jsonify([o.to_dict() for o in orders])

@app.route("/api/admin/orders/<order_id>/status", methods=["PATCH"])
@login_required
@admin_required
def admin_update_order_status(order_id):
    order = Order.get_by_id(order_id)
    if not order:
        return jsonify({"message": "Order not found"}), 404
    data = request.get_json()
    order.status = data.get('status', order.status)
    order.save()
    try:
        socketio.emit('order_status_update', order.to_dict())
    except Exception as e:
        print(f"Failed to emit order status update: {e}")
    return jsonify(order.to_dict())

# --- Cart ---
@app.route("/api/cart/add", methods=["POST"])
@login_required
def add_to_cart_api():
    data = request.get_json()
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)
    force = data.get('force', False)

    menu_item = MenuItem.get_by_id(item_id)
    if not menu_item:
        return jsonify({"message": "Item not found"}), 404

    profile = _merge_user_profile(current_user)
    user_allergies_str = profile.get("allergies") or ""
    if user_allergies_str and not force:
        user_allergies = [a.strip().lower() for a in user_allergies_str.split(",")]
        item_ingredients = (menu_item.ingredients or "").lower()
        detected_allergens = [a for a in user_allergies if a in item_ingredients]
        if detected_allergens:
            return jsonify({
                "status": "warning",
                "message": f"Wait! This item contains {', '.join(detected_allergens)}, which you are allergic to. Are you sure?",
                "requires_confirmation": True
            }), 409

    add_to_cart(current_user.id, menu_item.name, quantity, menu_item.price)
    return jsonify({"message": "Item added to cart successfully", "status": "success"})

@app.route("/api/cart", methods=["GET"])
@login_required
def get_cart():
    cart_items = get_user_cart(current_user.id)
    cart = [{"name": item.item_name, "qty": item.quantity, "unit_price": item.unit_price} for item in cart_items]
    total = sum(item['qty'] * item['unit_price'] for item in cart)
    return jsonify({"cart": cart, "total": total})

@app.route("/api/cart/remove", methods=["POST"])
@login_required
def remove_from_cart_api():
    data = request.get_json()
    item_name = data.get('item_name')
    if not item_name:
        return jsonify({"message": "Item name is required"}), 400
    remove_from_cart(current_user.id, item_name)
    return jsonify({"message": "Item removed from cart successfully"})

# --- Checkout / Orders ---
@app.route("/api/checkout", methods=["POST"])
@login_required
def checkout():
    cart_items = get_user_cart(current_user.id)
    if not cart_items:
        return jsonify({"message": "Your cart is empty"}), 400
    cart = [{"name": item.item_name, "qty": item.quantity, "unit_price": item.unit_price} for item in cart_items]
    new_order = ordering_agent(current_user, cart)
    clear_cart(current_user.id)
    return jsonify({"message": f"Your order (ID: {new_order.id}) has been placed. Total: Rs {new_order.total_price:.2f}. A bill has been sent to your inbox. Thank you!"})

@app.route("/api/orders", methods=["GET"])
@login_required
def get_orders():
    orders = Order.get_by_user(current_user.id)
    return jsonify([o.to_dict() for o in orders])

# --- Inbox ---
@app.route("/api/inbox", methods=["GET"])
@login_required
def get_inbox():
    messages = InboxMessage.get_by_user(current_user.id)
    return jsonify([msg.to_dict() for msg in messages])

@app.route("/api/inbox/<message_id>/read", methods=["POST"])
@login_required
def mark_message_read(message_id):
    message = InboxMessage.get_by_id_and_user(message_id, current_user.id)
    if not message:
        return jsonify({"message": "Message not found"}), 404
    message.mark_read()
    return jsonify({"message": "Message marked as read"})

# --- Reservations ---
@app.route('/api/reservations/my-bookings', methods=['GET'])
@login_required
def my_bookings():
    reservations = Reservation.get_by_user(current_user.id)
    return jsonify([r.to_dict() for r in reservations])

@app.route('/api/reservations/availability', methods=['GET'])
def check_availability():
    date_str = request.args.get('date')
    table_type = request.args.get('table_type')
    if not date_str or not table_type:
        return jsonify({"message": "date and table_type are required"}), 400
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD"}), 400

    table = TableInventory.get_by_type(table_type)
    if not table:
        return jsonify({"available": False, "message": f"No tables of type '{table_type}' found"}), 404

    existing_bookings = Reservation.count_confirmed_by_date(table_type, date_str)
    available_count = max(0, table.total_quantity - existing_bookings)
    return jsonify({
        "available": available_count > 0,
        "available_count": available_count,
        "table_type": table_type,
        "date": date_str
    })

@app.route('/api/reservations/quote', methods=['POST'])
@login_required
def reservation_quote():
    data = request.get_json()
    table_type = data.get('table_type')
    party_size = data.get('party_size')
    date_str = data.get('date')
    time_str = data.get('time')
    occasion_type = data.get('occasion_type', 'none')
    if not all([table_type, party_size, date_str, time_str]):
        return jsonify({"message": "table_type, party_size, date, and time are required"}), 400
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD"}), 400
    table = TableInventory.get_by_type(table_type)
    if not table:
        return jsonify({"message": f"Table type '{table_type}' not found"}), 404
    existing_bookings = Reservation.count_confirmed_by_date(table_type, date_str)
    available_count = table.total_quantity - existing_bookings
    quote = {
        "table_type": table_type,
        "party_size": party_size,
        "date": date_str,
        "time": time_str,
        "occasion_type": occasion_type,
        "available": available_count > 0,
        "available_count": max(0, available_count),
        "price_per_head": 0,
        "estimated_total": 0
    }
    return jsonify(quote)

@app.route('/api/reservations/book', methods=['POST'])
@login_required
def book_reservation():
    import random, string
    data = request.get_json()
    table_type = data.get('table_type')
    party_size = data.get('party_size')
    date_str = data.get('date')
    time_str = data.get('time')
    occasion_type = data.get('occasion_type', 'none')
    special_requests = data.get('special_requests', '')
    if not all([table_type, party_size, date_str, time_str]):
        return jsonify({"message": "table_type, party_size, date, and time are required"}), 400
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        datetime.strptime(time_str, '%H:%M')
    except ValueError as e:
        return jsonify({"message": f"Invalid date/time format: {e}"}), 400
    table = TableInventory.get_by_type(table_type)
    if not table:
        return jsonify({"message": f"Table type '{table_type}' not found"}), 404
    existing_bookings = Reservation.count_confirmed_by_date(table_type, date_str)
    if existing_bookings >= table.total_quantity:
        return jsonify({"message": f"No {table_type} tables available on {date_str}"}), 409
    confirmation_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    reservation = Reservation.create(
        user_id=current_user.id,
        table_type=table_type,
        party_size=int(party_size),
        reservation_date=date_str,
        reservation_time=time_str,
        occasion_type=occasion_type,
        special_requests=special_requests,
        status='confirmed',
        confirmation_code=confirmation_code,
        table_quantity=1,
    )
    InboxMessage.create(
        user_id=current_user.id,
        subject=f"Reservation Confirmed - {confirmation_code}",
        message=f"Your reservation has been confirmed!\n\nConfirmation Code: {confirmation_code}\nTable Type: {table_type}\nParty Size: {party_size}\nDate: {date_str}\nTime: {time_str}\nOccasion: {occasion_type}\n\nThank you for choosing DineSmartAI!"
    )
    try:
        socketio.emit('new_reservation', reservation.to_dict(), room='admins_room')
    except Exception as e:
        print(f"Failed to emit new_reservation: {e}")
    return jsonify({
        "message": "Reservation confirmed successfully!",
        "confirmation_code": confirmation_code,
        "reservation": reservation.to_dict()
    }), 201

@app.route('/api/reservations/<reservation_id>/cancel', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    reservation = Reservation.get_by_id_and_user(reservation_id, current_user.id)
    if not reservation:
        return jsonify({"message": "Reservation not found"}), 404
    if reservation.status == 'cancelled':
        return jsonify({"message": "Reservation is already cancelled"}), 400
    reservation.status = 'cancelled'
    reservation.save()
    return jsonify({"message": "Reservation cancelled successfully"})

@app.route('/api/admin/reservations', methods=['GET'])
@login_required
@admin_required
def admin_get_reservations():
    reservations = Reservation.get_all()
    return jsonify([r.to_dict() for r in reservations])

@app.route('/api/admin/tables', methods=['GET'])
@login_required
@admin_required
def admin_get_tables():
    tables = TableInventory.get_all()
    return jsonify([t.to_dict() for t in tables])

@app.route('/api/admin/tables/update', methods=['POST'])
@login_required
@admin_required
def admin_update_tables():
    data = request.get_json()
    for item in data:
        TableInventory.upsert(
            table_type=item.get('table_type'),
            total_quantity=item.get('total_tables', item.get('total_quantity', 1))
        )
    return jsonify({"message": "Table inventory updated successfully"})

# --- Favorites ---
@app.route('/api/favorites/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    data = request.get_json()
    item_id = data.get('item_id')
    if not item_id:
        return jsonify({"message": "item_id is required"}), 400
    item = MenuItem.get_by_id(item_id)
    if not item:
        return jsonify({"message": "Menu item not found"}), 404
    existing = Favorite.get_by_user_and_item(current_user.id, item_id)
    if existing:
        existing.delete()
        return jsonify({"message": "Removed from favorites", "is_favorite": False})
    else:
        Favorite.create(user_id=current_user.id, item_id=item_id)
        return jsonify({"message": "Added to favorites", "is_favorite": True})

@app.route('/api/favorites/my-favorites', methods=['GET'])
@login_required
def my_favorites():
    favorite_rows = Favorite.get_by_user(current_user.id)
    items = [MenuItem.get_by_id(f.item_id) for f in favorite_rows]
    items = [i.to_dict() for i in items if i]
    return jsonify(items)

@app.route('/api/favorites/check/<item_id>', methods=['GET'])
@login_required
def check_favorite(item_id):
    exists = Favorite.get_by_user_and_item(current_user.id, item_id)
    return jsonify({"is_favorite": bool(exists)})

# --- Ratings ---
@app.route("/api/rate/<item_id>", methods=["POST"])
@login_required
def rate_item(item_id):
    data = request.get_json()
    rating_value = data.get('rating')
    if not rating_value or not (1 <= rating_value <= 5):
        return jsonify({"message": "Rating must be between 1 and 5"}), 400
    menu_item = MenuItem.get_by_id(item_id)
    if not menu_item:
        return jsonify({"message": "Item not found"}), 404
    Rating.upsert(current_user.id, item_id, rating_value)
    return jsonify({"message": "Rating submitted successfully"})

# --- AI Chat ---
@app.route("/api/ai/chat", methods=["POST"])
@login_required
def api_ai_chat():
    user_message = request.json.get('message', '')
    print(f"\n--- [API] Chat Request ---\nUser: {user_message}\n---", flush=True)
    chat_history = _get_chat_history(current_user.id)
    try:
        bot_reply = route_user_request(user_message)
    except Exception as e:
        import traceback
        print(f"Chat Route Error: {e}")
        traceback.print_exc()
        bot_reply = "I encountered an error processing your request. Please try again."
    chat_history.extend([
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": bot_reply}
    ])
    _save_chat_history(current_user.id, chat_history)
    return jsonify({"reply": bot_reply})

@app.route("/api/ai/chat/history", methods=["GET"])
@login_required
def api_ai_chat_history():
    chat_history = _get_chat_history(current_user.id)
    return jsonify({"history": chat_history})

# --- Socket.IO ---
@socketio.on('join')
def on_join(data):
    if current_user.is_authenticated and data.get('role') == 'admin' and current_user.role == 'admin':
        join_room('admins_room')
        print(f"Admin '{current_user.username}' joined admin room.")

# --- Main Startup ---
if __name__ == "__main__":
    # Ensure table inventory defaults
    table_types = [
        ("intimate", 5), ("small", 8), ("family", 6), ("large", 4), ("banquet", 2)
    ]
    for ttype, count in table_types:
        if not TableInventory.get_by_type(ttype):
            TableInventory.upsert(ttype, count)

    migrate_csv_to_db()

    # Ensure admin user exists
    if not User.get_by_username('admin@gmail.com'):
        User.create(username='admin@gmail.com', password='admin123', role='admin')
        print("Admin user created.")

    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)
