import os
import re
import csv
import threading
from flask import Flask, request, jsonify, session
from datetime import datetime
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from modals import db, User, MenuItem, Order, OrderItem, InboxMessage, Rating, CartItem
from werkzeug.security import generate_password_hash, check_password_hash
from difflib import get_close_matches
from sqlalchemy.orm import relationship
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Initialize Extensions ---
db.init_app(app)
# Allow both localhost and 127.0.0.1 for development
CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    ping_timeout=20,
    ping_interval=25,
    async_mode='eventlet' if os.environ.get('USE_EVENTLET') else None # Optional but good practice
)

# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Register Blueprints ---
app.register_blueprint(recommendations_bp)

# --- Helper Functions for Cart ---
def add_to_cart(user_id, item_name, quantity, unit_price):
    existing = CartItem.query.filter_by(user_id=user_id, item_name=item_name).first()
    if existing:
        existing.quantity += quantity
    else:
        cart_item = CartItem(user_id=user_id, item_name=item_name, quantity=quantity, unit_price=unit_price)
        db.session.add(cart_item)
    db.session.commit()

def get_user_cart(user_id):
    return CartItem.query.filter_by(user_id=user_id).all()

def remove_from_cart(user_id, item_name):
    CartItem.query.filter_by(user_id=user_id, item_name=item_name).delete()
    db.session.commit()

def clear_cart(user_id):
    CartItem.query.filter_by(user_id=user_id).delete()
    db.session.commit()

# --- Ordering Agent ---
def ordering_agent(user, cart):
    total_price = sum(item['qty'] * item['unit_price'] for item in cart)
    new_order = Order(user_id=user.id, total_price=total_price)
    db.session.add(new_order)
    db.session.commit()
    
    for item in cart:
        order_item = OrderItem(order_id=new_order.id, item_name=item['name'], quantity=item['qty'], unit_price=item['unit_price'])
        db.session.add(order_item)
    
    bill_message = f"Order #{new_order.id} Confirmed!\n\nItems:\n"
    for item in cart:
        bill_message += f"- {item['qty']}x {item['name']} @ ₹{item['unit_price']:.2f} = ₹{item['qty'] * item['unit_price']:.2f}\n"
    bill_message += f"\nTotal: ₹{total_price:.2f}\n\nThank you for your order!"
    
    inbox_msg = InboxMessage(user_id=user.id, subject=f"Order #{new_order.id} Confirmation", message=bill_message)
    db.session.add(inbox_msg)
    db.session.commit()
    
    return new_order

# --- CSV Migration ---
def migrate_csv_to_db():
    """Migrates menu from CSV to SQL DB and syncs with Vector DB (Brain)."""
    # 1. SQL Migration (Fresh Sync to prevent duplication)
    print("Starting fresh menu migration...")
    MenuItem.query.delete() # Clear existing duplicates
    db.session.commit()
    
    csv_path = os.path.join(os.path.dirname(__file__), 'menu.csv')
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = MenuItem(
                    name=row.get('name'),
                    description=row.get('description'),
                    price=float(row.get('price', 0)),
                    category=row.get('course'), # Correctly mapping 'course' to 'category'
                    ingredients=row.get('ingredients'),
                    diet=row.get('diet'),
                    calories=float(row.get('calories', 0)) if row.get('calories') else None,
                    protein=float(row.get('protein', 0)) if row.get('protein') else None,
                    carbs=float(row.get('carbs', 0)) if row.get('carbs') else None,
                    fat=float(row.get('fat', 0)) if row.get('fat') else None,
                    image_url=row.get('image_url')
                )
                db.session.add(item)
            db.session.commit()
        print("Menu migrated from CSV to SQL DB (Clean State).")

    # 2. Brain (Vector DB) Sync
    print("Checking Brain status...")
    brain_count = agent_memory.get_knowledge_count()
    all_items = MenuItem.query.all()

    if brain_count < len(all_items):
        print(f"Brain has {brain_count} items, SQL has {len(all_items)}. Starting sync...")
        indexing_tasks = []
        for item in all_items:
            text = f"{item.name}: {item.description}. Ingredients: {item.ingredients}. Diet: {item.diet}. Category: {item.category}."
            meta = {
                "id": str(item.id), 
                "name": item.name or "", 
                "category": item.category or "", 
                "diet": item.diet or ""
            }
            indexing_tasks.append((text, meta))
            
        def background_indexer(tasks):
            import time
            print(f"--- [Sync] Indexing {len(tasks)} items to Brain ---")
            for text, meta in tasks:
                agent_memory.add_knowledge(text, meta)
                time.sleep(2) # Prevent quota exhaustion on free tier keys
            print("--- [Sync] Brain update complete ---")
            
        thread = threading.Thread(target=background_indexer, args=(indexing_tasks,))
        thread.daemon = True
        thread.start()
    else:
        print(f"Brain synced ({brain_count} items).")

# --- Agent Orchestrator Instance ---
orchestrator = None
from agents.memory import AgentMemory

# Initialize Memory
agent_memory = AgentMemory()

# --- New Agent Logic Integration ---
def route_user_request(user_message: str) -> str:
    global orchestrator
    if not orchestrator:
        orchestrator = LangGraphOrchestrator(socketio)
        print("--- [LangGraph Orchestrator] Initialized lazy-loaded. ---")
    
    chat_history = session.get('chat_history', [])
    
    from langchain_core.messages import HumanMessage, AIMessage
    lc_history = []
    for msg in chat_history:
        if msg['role'] == 'user':
            lc_history.append(HumanMessage(content=msg['content']))
        else:
            lc_history.append(AIMessage(content=msg['content']))
            
    return orchestrator.route_request(user_message, lc_history)

@app.route("/api/dataspace", methods=["GET"])
def get_dataspace():
    """Returns the live stream of agent thoughts/memory."""
    return jsonify(agent_memory.get_dataspace_stream())

# --- API Routes (Largely Unchanged) ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route("/api/signup", methods=["POST"])
def signup():
    # ... (rest of the function is unchanged)
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 409
    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created successfully"}), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    # ... (rest of the function is unchanged)
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user, remember=True)
        return jsonify(user.to_dict())
    return jsonify({"message": "Invalid credentials"}), 401
    
@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    # ... (rest of the function is unchanged)
    logout_user()
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@app.route("/api/auth/status")
def auth_status():
    # ... (rest of the function is unchanged)
    if current_user.is_authenticated:
        return jsonify({"isLoggedIn": True, "user": current_user.to_dict()})
    return jsonify({"isLoggedIn": False, "user": None})

@app.route("/api/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        data = request.get_json()
        current_user.allergies = data.get("allergies", "")
        current_user.preferences = data.get("preferences", "")

        # Parse nutrition goals from preferences string if present
        preferences_str = current_user.preferences or ""
        calorie_goal = data.get("calorie_goal")
        protein_goal = data.get("protein_goal")
        carb_goal = data.get("carb_goal")
        fat_goal = data.get("fat_goal")

        # If nutrition goals are not directly provided, try to parse from preferences string
        if not all([calorie_goal, protein_goal, carb_goal, fat_goal]) and preferences_str:
            # Example format: "calories=250, protein=15, carb=10, fat=15"
            try:
                prefs = preferences_str.lower().replace(" ", "").split(",")
                for pref in prefs:
                    if pref.startswith("calories="):
                        calorie_goal = float(pref.split("=")[1])
                    elif pref.startswith("protein="):
                        protein_goal = float(pref.split("=")[1])
                    elif pref.startswith("carb="):
                        carb_goal = float(pref.split("=")[1])
                    elif pref.startswith("fat="):
                        fat_goal = float(pref.split("=")[1])
            except Exception as e:
                print(f"Error parsing nutrition goals from preferences: {e}")

        current_user.calorie_goal = calorie_goal
        current_user.protein_goal = protein_goal
        current_user.carb_goal = carb_goal
        current_user.fat_goal = fat_goal

        db.session.commit()
        return jsonify({"message": "Profile updated successfully"})

    return jsonify({
        "username": current_user.username,
        "allergies": current_user.allergies or "",
        "preferences": current_user.preferences or "",
        "calorie_goal": current_user.calorie_goal,
        "protein_goal": current_user.protein_goal,
        "carb_goal": current_user.carb_goal,
        "fat_goal": current_user.fat_goal
    })


@app.route("/api/menu")
def get_menu_api():
    diet_filter = request.args.get('diet')
    category_filter = request.args.get('category')
    search_term = request.args.get('search', '').lower()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    query = MenuItem.query

    if diet_filter and diet_filter != 'All':
        # Handle case-insensitive diet filtering
        if diet_filter.lower() == 'vegetarian':
            query = query.filter(MenuItem.diet.ilike('vegetarian'))
        elif diet_filter.lower() == 'non-vegetarian':
            query = query.filter(MenuItem.diet.ilike('non-vegetarian'))
        elif diet_filter.lower() == 'vegan':
            query = query.filter(MenuItem.diet.ilike('vegan'))
        else:
            query = query.filter(MenuItem.diet == diet_filter)

    if category_filter and category_filter != 'All':
        query = query.filter(MenuItem.category.ilike(category_filter))

    if min_price is not None:
        query = query.filter(MenuItem.price >= min_price)
    if max_price is not None:
        query = query.filter(MenuItem.price <= max_price)

    items = query.all()

    if search_term:
        items = [item for item in items if search_term in (item.name or '').lower() or search_term in (item.description or '').lower() or search_term in (item.ingredients or '').lower()]

    return jsonify([item.to_dict() for item in items])

@app.route("/api/menu/filtered")
@login_required
def get_filtered_menu_api():
    diet_filter = request.args.get('diet')
    category_filter = request.args.get('category')
    search_term = request.args.get('search', '').lower()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    user_allergies = current_user.allergies or ""
    allergies_list = [allergy.strip().lower() for allergy in user_allergies.split(',') if allergy.strip()]
    
    query = MenuItem.query
    
    if diet_filter and diet_filter != 'All':
        if diet_filter.lower() == 'vegetarian':
            query = query.filter(MenuItem.diet.ilike('vegetarian'))
        elif diet_filter.lower() == 'non-vegetarian':
            query = query.filter(MenuItem.diet.ilike('non-vegetarian'))
        elif diet_filter.lower() == 'vegan':
            query = query.filter(MenuItem.diet.ilike('vegan'))
        else:
            query = query.filter(MenuItem.diet == diet_filter)

    if category_filter and category_filter != 'All':
        query = query.filter(MenuItem.category.ilike(category_filter))

    if min_price is not None:
        query = query.filter(MenuItem.price >= min_price)
    if max_price is not None:
        query = query.filter(MenuItem.price <= max_price)
    
    all_items = query.all()
    
    filtered_items = []
    for item in all_items:
        item_ingredients = (item.ingredients or "").lower()
        if not any(allergy in item_ingredients for allergy in allergies_list):
            if search_term:
                if search_term in (item.name or '').lower() or search_term in (item.description or '').lower() or search_term in item_ingredients:
                    filtered_items.append(item.to_dict())
            else:
                filtered_items.append(item.to_dict())
    return jsonify(filtered_items)

@app.route("/api/admin/menu", methods=["POST"])
@login_required
@admin_required
def admin_add_dish():
    data = request.get_json()
    new_dish = MenuItem(
        name=data['name'],
        description=data.get('description'),
        price=float(data['price']),
        category=data.get('category'),
        ingredients=data.get('ingredients'),
        diet=data.get('diet')
    )
    db.session.add(new_dish)
    db.session.commit()
    return jsonify(new_dish.to_dict()), 201

@app.route("/api/admin/menu/<int:item_id>", methods=["DELETE"])
@login_required
@admin_required
def admin_delete_dish(item_id):
    # ... (rest of the function is unchanged)
    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item deleted successfully"})

@app.route("/api/ai/chat", methods=["POST"])
@login_required
def api_ai_chat():
    user_message = request.json.get('message', '')
    print(f"\n--- [API] Chat Request Received ---\nUser Message: {user_message}\n-----------------------------------", flush=True)
    if 'chat_history' not in session: session['chat_history'] = []

    try:
        bot_reply = route_user_request(user_message)
    except Exception as e:
        print(f"Chat Route Error: {e}")
        bot_reply = "I encountered an error processing your request."

    # Update history and truncate to prevent token exhaustion (Keep last 20 messages)
    session['chat_history'].extend([{"role": "user", "content": user_message}, {"role": "assistant", "content": bot_reply}])
    if len(session['chat_history']) > 20:
        session['chat_history'] = session['chat_history'][-20:]
        
    session.modified = True
    return jsonify({"reply": bot_reply})

@app.route("/api/cart/add", methods=["POST"])
@app.route("/api/cart/add", methods=["POST"])
@login_required
def add_to_cart_api():
    data = request.get_json()
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)
    force = data.get('force', False)

    # FIX: Updated to use the modern db.session.get() method
    menu_item = db.session.get(MenuItem, item_id)

    if not menu_item:
        return jsonify({"message": "Item not found"}), 404

    # --- Allergy Check ---
    if current_user.allergies and not force:
        user_allergies = [a.strip().lower() for a in current_user.allergies.split(",")]
        item_ingredients = menu_item.ingredients.lower() if menu_item.ingredients else ""
        
        detected_allergens = [allergen for allergen in user_allergies if allergen in item_ingredients]
        
        if detected_allergens:
            return jsonify({
                "status": "warning", 
                "message": f"Wait! This item contains {', '.join(detected_allergens)}, which you are allergic to. Are you sure?",
                "requires_confirmation": True
            }), 409
    # ---------------------

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

@app.route("/api/orders", methods=["GET"])
@login_required
def get_orders():
    # ... (rest of the function is unchanged)
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.timestamp.desc()).all()
    return jsonify([order.to_dict() for order in orders])

@app.route("/api/inbox", methods=["GET"])
@login_required
def get_inbox():
    # ... (rest of the function is unchanged)
    messages = InboxMessage.query.filter_by(user_id=current_user.id).order_by(InboxMessage.timestamp.desc()).all()
    return jsonify([msg.to_dict() for msg in messages])

@app.route("/api/inbox/<int:message_id>/read", methods=["POST"])
@login_required
def mark_message_read(message_id):
    # ... (rest of the function is unchanged)
    message = InboxMessage.query.filter_by(id=message_id, user_id=current_user.id).first()
    if not message:
        return jsonify({"message": "Message not found"}), 404
    message.is_read = True
    db.session.commit()
    return jsonify({"message": "Message marked as read"})

@app.route("/api/rate/<int:item_id>", methods=["POST"])
@login_required
def rate_item(item_id):
    data = request.get_json()
    rating_value = data.get('rating')
    if not rating_value or not (1 <= rating_value <= 5):
        return jsonify({"message": "Rating must be between 1 and 5"}), 400

    # Check if item exists
    menu_item = db.session.get(MenuItem, item_id)
    if not menu_item:
        return jsonify({"message": "Item not found"}), 404

    # Check if user already rated this item
    existing_rating = Rating.query.filter_by(user_id=current_user.id, item_id=item_id).first()
    if existing_rating:
        existing_rating.rating = rating_value
        existing_rating.timestamp = datetime.utcnow()
    else:
        new_rating = Rating(user_id=current_user.id, item_id=item_id, rating=rating_value)
        db.session.add(new_rating)

    db.session.commit()
    return jsonify({"message": "Rating submitted successfully"})

@app.route("/api/send-bill", methods=["POST"])
@login_required
def send_bill():
    # Retrieve user's current cart from DB
    cart_items = get_user_cart(current_user.id)
    if not cart_items:
        return jsonify({"message": "Your cart is empty"}), 400

    # Generate bill message for cart items and total
    total_cost = sum(item.quantity * item.unit_price for item in cart_items)
    bill_items = "\n".join([f"- {item.quantity}x {item.item_name} @ ₹{item.unit_price:.2f} each = ₹{(item.quantity * item.unit_price):.2f}" for item in cart_items])
    bill_message = f"Cart Bill\nDate: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\nItems:\n{bill_items}\n\nTotal: ₹{total_cost:.2f}\n\nThis is a bill for your current cart. You can proceed to checkout to place the order."

    # Create InboxMessage with bill details
    bill = InboxMessage(user_id=current_user.id, subject="Bill for Your Cart", message=bill_message)
    db.session.add(bill)
    db.session.commit()

    # Return success JSON response
    return jsonify({"message": "Bill sent to your inbox"})

@app.route("/api/checkout", methods=["POST"])
@login_required
def checkout():
    # Retrieve user's current cart from DB
    cart_items = get_user_cart(current_user.id)
    if not cart_items:
        return jsonify({"message": "Your cart is empty"}), 400

    # Convert to list of dicts for ordering_agent
    cart = [{"name": item.item_name, "qty": item.quantity, "unit_price": item.unit_price} for item in cart_items]

    # Trigger the ordering agent to handle the rest of the process
    new_order = ordering_agent(current_user, cart)

    # Clear the cart from DB
    clear_cart(current_user.id)

    return jsonify({"message": f"Your order (ID: {new_order.id}) has been placed. The total is ₹{new_order.total_price:.2f}. A bill has been sent to your inbox. Thank you!"})

# --- Socket.IO Real-time Events ---
@socketio.on('join')
@login_required
def on_join(data):
    if data.get('role') == 'admin' and current_user.role == 'admin':
        join_room('admins_room')
        print(f"Admin '{current_user.username}' has joined the admin room.")

# --- Main Startup ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        migrate_csv_to_db()
        if not User.query.filter_by(username='admin@gmail.com').first():
            admin = User(username='admin@gmail.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)



