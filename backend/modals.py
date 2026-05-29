"""
modals.py — MongoDB-backed models using PyMongo.
Replaces Flask-SQLAlchemy with direct PyMongo collections.
Flask-Login is preserved via a lightweight User class.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from bson import ObjectId


# ---------------------------------------------------------------------------
# Mongo DB holder — set by init_db() called from app.py
# ---------------------------------------------------------------------------
_mongo_db = None


def init_db(mongo_db_instance):
    """Called once from app.py after MongoDB connection is established."""
    global _mongo_db
    _mongo_db = mongo_db_instance
    _ensure_indexes()


def get_db():
    return _mongo_db


def _ensure_indexes():
    """Create all necessary indexes on startup."""
    db = _mongo_db
    if db is None:
        return
    db.users.create_index("username", unique=True)
    db.menu_items.create_index("name")
    db.orders.create_index("user_id")
    db.order_items.create_index("order_id")
    db.inbox_messages.create_index([("user_id", 1), ("timestamp", -1)])
    db.cart_items.create_index([("user_id", 1), ("item_name", 1)])
    db.ratings.create_index([("user_id", 1), ("item_id", 1)])
    db.table_inventory.create_index("table_type", unique=True)
    db.reservations.create_index("confirmation_code", unique=True, sparse=True)
    db.reservations.create_index("user_id")
    db.favorites.create_index([("user_id", 1), ("item_id", 1)], unique=True)
    db.chat_sessions.create_index("user_id", unique=True)
    db.pending_reservations.create_index("user_id", unique=True)
    db.user_profiles.create_index("user_id", unique=True)


# ---------------------------------------------------------------------------
# Helper: convert ObjectId → str in dicts
# ---------------------------------------------------------------------------
def _oid(val):
    """Return ObjectId from str or ObjectId."""
    if isinstance(val, ObjectId):
        return val
    try:
        return ObjectId(str(val))
    except Exception:
        return val


def _to_str_id(doc):
    """Return a copy of doc with _id converted to str 'id'."""
    if doc is None:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


# ---------------------------------------------------------------------------
# User (Flask-Login compatible)
# ---------------------------------------------------------------------------
class User(UserMixin):
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.username = doc.get("username", "")
        self.password_hash = doc.get("password_hash", "")
        self.role = doc.get("role", "customer")
        # profile fields (may be stored in user_profiles collection too)
        self.allergies = doc.get("allergies", "")
        self.preferences = doc.get("preferences", "")
        self.calorie_goal = doc.get("calorie_goal")
        self.protein_goal = doc.get("protein_goal")
        self.carb_goal = doc.get("carb_goal")
        self.fat_goal = doc.get("fat_goal")

    # Flask-Login requires get_id() to return a string
    def get_id(self):
        return self.id

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "allergies": self.allergies or "",
            "preferences": self.preferences or "",
            "calorie_goal": self.calorie_goal,
            "protein_goal": self.protein_goal,
            "carb_goal": self.carb_goal,
            "fat_goal": self.fat_goal,
        }

    # ---- Class-level query helpers (mirror SQLAlchemy API used in app.py) ----

    @classmethod
    def query_filter_by(cls, **kwargs):
        """Returns a list of User objects matching kwargs."""
        db = get_db()
        docs = list(db.users.find(kwargs))
        return [cls(d) for d in docs]

    @classmethod
    def get_by_id(cls, user_id):
        db = get_db()
        doc = db.users.find_one({"_id": _oid(user_id)})
        return cls(doc) if doc else None

    @classmethod
    def get_by_username(cls, username):
        db = get_db()
        doc = db.users.find_one({"username": username})
        return cls(doc) if doc else None

    @classmethod
    def create(cls, username, password, role="customer"):
        db = get_db()
        ph = generate_password_hash(password)
        result = db.users.insert_one({
            "username": username,
            "password_hash": ph,
            "role": role,
            "allergies": "",
            "preferences": "",
            "calorie_goal": None,
            "protein_goal": None,
            "carb_goal": None,
            "fat_goal": None,
            "created_at": datetime.utcnow(),
        })
        doc = db.users.find_one({"_id": result.inserted_id})
        return cls(doc)


# ---------------------------------------------------------------------------
# MenuItem
# ---------------------------------------------------------------------------
class MenuItem:
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.name = doc.get("name", "")
        self.description = doc.get("description", "")
        self.ingredients = doc.get("ingredients", "")
        self.diet = doc.get("diet", "")
        self.price = doc.get("price", 0.0)
        self.category = doc.get("category", "")
        self.calories = doc.get("calories", 0.0)
        self.protein = doc.get("protein", 0.0)
        self.carbs = doc.get("carbs", 0.0)
        self.fat = doc.get("fat", 0.0)
        self.flavor_profile = doc.get("flavor_profile", "")
        self.image_url = doc.get("image_url", "")
        self.cooking_tips = doc.get("cooking_tips", "")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "ingredients": self.ingredients,
            "diet": self.diet,
            "price": self.price,
            "category": self.category,
            "calories": self.calories,
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat,
            "flavor_profile": self.flavor_profile,
            "image_url": self.image_url,
            "cooking_tips": self.cooking_tips,
        }

    @classmethod
    def get_all(cls, filters=None):
        db = get_db()
        docs = list(db.menu_items.find(filters or {}))
        return [cls(d) for d in docs]

    @classmethod
    def get_by_id(cls, item_id):
        db = get_db()
        doc = db.menu_items.find_one({"_id": _oid(item_id)})
        return cls(doc) if doc else None

    @classmethod
    def get_by_name(cls, name):
        db = get_db()
        doc = db.menu_items.find_one({"name": name})
        return cls(doc) if doc else None

    @classmethod
    def find_ilike(cls, name):
        """Case-insensitive name match."""
        import re
        db = get_db()
        doc = db.menu_items.find_one({"name": re.compile(f"^{re.escape(name)}$", re.IGNORECASE)})
        return cls(doc) if doc else None

    @classmethod
    def create(cls, **kwargs):
        db = get_db()
        result = db.menu_items.insert_one(kwargs)
        doc = db.menu_items.find_one({"_id": result.inserted_id})
        return cls(doc)

    def save(self):
        db = get_db()
        db.menu_items.update_one(
            {"_id": _oid(self.id)},
            {"$set": {
                "name": self.name, "description": self.description,
                "ingredients": self.ingredients, "diet": self.diet,
                "price": self.price, "category": self.category,
                "calories": self.calories, "protein": self.protein,
                "carbs": self.carbs, "fat": self.fat,
                "flavor_profile": self.flavor_profile,
                "image_url": self.image_url, "cooking_tips": self.cooking_tips,
            }}
        )

    def delete(self):
        db = get_db()
        db.menu_items.delete_one({"_id": _oid(self.id)})


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------
class Order:
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.timestamp = doc.get("timestamp", datetime.utcnow())
        self.total_price = doc.get("total_price", 0.0)
        self.user_id = str(doc.get("user_id", ""))
        self.status = doc.get("status", "pending")
        self._items = None  # lazy-loaded

    @property
    def items(self):
        if self._items is None:
            db = get_db()
            docs = list(db.order_items.find({"order_id": self.id}))
            self._items = [OrderItem(d) for d in docs]
        return self._items

    @property
    def user(self):
        return User.get_by_id(self.user_id)

    def to_dict(self):
        u = self.user
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "total_price": self.total_price,
            "user_id": self.user_id,
            "username": u.username if u else "Unknown",
            "status": self.status,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def create(cls, user_id, total_price, status="pending"):
        db = get_db()
        result = db.orders.insert_one({
            "user_id": str(user_id),
            "total_price": total_price,
            "status": status,
            "timestamp": datetime.utcnow(),
        })
        doc = db.orders.find_one({"_id": result.inserted_id})
        return cls(doc)

    @classmethod
    def get_by_id(cls, order_id):
        db = get_db()
        doc = db.orders.find_one({"_id": _oid(order_id)})
        return cls(doc) if doc else None

    @classmethod
    def get_by_user(cls, user_id):
        db = get_db()
        docs = list(db.orders.find({"user_id": str(user_id)}).sort("timestamp", -1))
        return [cls(d) for d in docs]

    @classmethod
    def get_all(cls):
        db = get_db()
        docs = list(db.orders.find().sort("timestamp", -1))
        return [cls(d) for d in docs]

    def save(self):
        db = get_db()
        db.orders.update_one({"_id": _oid(self.id)}, {"$set": {"status": self.status}})


# ---------------------------------------------------------------------------
# OrderItem
# ---------------------------------------------------------------------------
class OrderItem:
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.item_name = doc.get("item_name", "")
        self.quantity = doc.get("quantity", 1)
        self.unit_price = doc.get("unit_price", 0.0)
        self.order_id = str(doc.get("order_id", ""))

    def to_dict(self):
        return {
            "item_name": self.item_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
        }

    @classmethod
    def create(cls, order_id, item_name, quantity, unit_price):
        db = get_db()
        result = db.order_items.insert_one({
            "order_id": str(order_id),
            "item_name": item_name,
            "quantity": quantity,
            "unit_price": unit_price,
        })
        doc = db.order_items.find_one({"_id": result.inserted_id})
        return cls(doc)


# ---------------------------------------------------------------------------
# InboxMessage
# ---------------------------------------------------------------------------
class InboxMessage:
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.user_id = str(doc.get("user_id", ""))
        self.subject = doc.get("subject", "")
        self.message = doc.get("message", "")
        self.timestamp = doc.get("timestamp", datetime.utcnow())
        self.is_read = doc.get("is_read", False)

    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_read": self.is_read,
        }

    @classmethod
    def create(cls, user_id, subject, message):
        db = get_db()
        result = db.inbox_messages.insert_one({
            "user_id": str(user_id),
            "subject": subject,
            "message": message,
            "timestamp": datetime.utcnow(),
            "is_read": False,
        })
        doc = db.inbox_messages.find_one({"_id": result.inserted_id})
        return cls(doc)

    @classmethod
    def get_by_user(cls, user_id):
        db = get_db()
        docs = list(db.inbox_messages.find({"user_id": str(user_id)}).sort("timestamp", -1))
        return [cls(d) for d in docs]

    @classmethod
    def get_by_id_and_user(cls, msg_id, user_id):
        db = get_db()
        doc = db.inbox_messages.find_one({"_id": _oid(msg_id), "user_id": str(user_id)})
        return cls(doc) if doc else None

    def mark_read(self):
        db = get_db()
        self.is_read = True
        db.inbox_messages.update_one({"_id": _oid(self.id)}, {"$set": {"is_read": True}})


# ---------------------------------------------------------------------------
# CartItem
# ---------------------------------------------------------------------------
class CartItem:
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.user_id = str(doc.get("user_id", ""))
        self.item_name = doc.get("item_name", "")
        self.quantity = doc.get("quantity", 1)
        self.unit_price = doc.get("unit_price", 0.0)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
        }

    @classmethod
    def get_by_user(cls, user_id):
        db = get_db()
        docs = list(db.cart_items.find({"user_id": str(user_id)}))
        return [cls(d) for d in docs]

    @classmethod
    def get_by_user_and_name(cls, user_id, item_name):
        db = get_db()
        doc = db.cart_items.find_one({"user_id": str(user_id), "item_name": item_name})
        return cls(doc) if doc else None

    @classmethod
    def upsert(cls, user_id, item_name, quantity, unit_price):
        db = get_db()
        existing = db.cart_items.find_one({"user_id": str(user_id), "item_name": item_name})
        if existing:
            db.cart_items.update_one(
                {"_id": existing["_id"]},
                {"$inc": {"quantity": quantity}}
            )
            doc = db.cart_items.find_one({"_id": existing["_id"]})
        else:
            result = db.cart_items.insert_one({
                "user_id": str(user_id),
                "item_name": item_name,
                "quantity": quantity,
                "unit_price": unit_price,
            })
            doc = db.cart_items.find_one({"_id": result.inserted_id})
        return cls(doc)

    @classmethod
    def remove_by_user_and_name(cls, user_id, item_name):
        db = get_db()
        db.cart_items.delete_one({"user_id": str(user_id), "item_name": item_name})

    @classmethod
    def clear_by_user(cls, user_id):
        db = get_db()
        db.cart_items.delete_many({"user_id": str(user_id)})

    def save(self):
        db = get_db()
        db.cart_items.update_one(
            {"_id": _oid(self.id)},
            {"$set": {"quantity": self.quantity, "unit_price": self.unit_price}}
        )

    def delete(self):
        db = get_db()
        db.cart_items.delete_one({"_id": _oid(self.id)})


# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------
class Rating:
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.user_id = str(doc.get("user_id", ""))
        self.item_id = str(doc.get("item_id", ""))
        self.rating = doc.get("rating", 0)
        self.timestamp = doc.get("timestamp", datetime.utcnow())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_id": self.item_id,
            "rating": self.rating,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def get_all(cls):
        db = get_db()
        docs = list(db.ratings.find())
        return [cls(d) for d in docs]

    @classmethod
    def get_by_user_and_item(cls, user_id, item_id):
        db = get_db()
        doc = db.ratings.find_one({"user_id": str(user_id), "item_id": str(item_id)})
        return cls(doc) if doc else None

    @classmethod
    def upsert(cls, user_id, item_id, rating_value):
        db = get_db()
        existing = db.ratings.find_one({"user_id": str(user_id), "item_id": str(item_id)})
        if existing:
            db.ratings.update_one(
                {"_id": existing["_id"]},
                {"$set": {"rating": rating_value, "timestamp": datetime.utcnow()}}
            )
            doc = db.ratings.find_one({"_id": existing["_id"]})
        else:
            result = db.ratings.insert_one({
                "user_id": str(user_id),
                "item_id": str(item_id),
                "rating": rating_value,
                "timestamp": datetime.utcnow(),
            })
            doc = db.ratings.find_one({"_id": result.inserted_id})
        return cls(doc)


# ---------------------------------------------------------------------------
# TableInventory
# ---------------------------------------------------------------------------
class TableInventory:
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.table_type = doc.get("table_type", "")
        self.total_quantity = doc.get("total_quantity", 5)
        # legacy alias used in some routes
        self.total_tables = self.total_quantity

    def to_dict(self):
        return {
            "id": self.id,
            "table_type": self.table_type,
            "total_quantity": self.total_quantity,
        }

    @classmethod
    def get_all(cls):
        db = get_db()
        docs = list(db.table_inventory.find())
        return [cls(d) for d in docs]

    @classmethod
    def get_by_type(cls, table_type):
        db = get_db()
        doc = db.table_inventory.find_one({"table_type": table_type})
        return cls(doc) if doc else None

    @classmethod
    def upsert(cls, table_type, total_quantity):
        db = get_db()
        db.table_inventory.update_one(
            {"table_type": table_type},
            {"$set": {"table_type": table_type, "total_quantity": total_quantity}},
            upsert=True,
        )
        return cls.get_by_type(table_type)


# ---------------------------------------------------------------------------
# Reservation
# ---------------------------------------------------------------------------
class Reservation:
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.user_id = str(doc.get("user_id", ""))
        self.table_type = doc.get("table_type", "")
        self.table_quantity = doc.get("table_quantity", 1)
        self.party_size = doc.get("party_size", 0)
        self.reservation_date = doc.get("reservation_date")  # stored as date string YYYY-MM-DD
        self.reservation_time = doc.get("reservation_time")  # stored as time string HH:MM
        self.seating_preference = doc.get("seating_preference", "indoor")
        self.occasion_type = doc.get("occasion_type", "none")
        self.special_requests = doc.get("special_requests", "")
        self.total_cost = doc.get("total_cost")
        self.discount_code = doc.get("discount_code")
        self.payment_method = doc.get("payment_method", "cash")
        self.payment_status = doc.get("payment_status", "pending")
        self.status = doc.get("status", "confirmed")
        self.confirmation_code = doc.get("confirmation_code")
        self.created_at = doc.get("created_at", datetime.utcnow())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "table_type": self.table_type,
            "table_quantity": self.table_quantity,
            "party_size": self.party_size,
            "reservation_date": self.reservation_date,
            "reservation_time": self.reservation_time,
            "seating_preference": self.seating_preference,
            "occasion_type": self.occasion_type,
            "special_requests": self.special_requests,
            "total_cost": self.total_cost,
            "status": self.status,
            "confirmation_code": self.confirmation_code,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @classmethod
    def create(cls, **kwargs):
        db = get_db()
        kwargs.setdefault("created_at", datetime.utcnow())
        kwargs["user_id"] = str(kwargs.get("user_id", ""))
        result = db.reservations.insert_one(kwargs)
        doc = db.reservations.find_one({"_id": result.inserted_id})
        return cls(doc)

    @classmethod
    def get_by_id(cls, res_id):
        db = get_db()
        doc = db.reservations.find_one({"_id": _oid(res_id)})
        return cls(doc) if doc else None

    @classmethod
    def get_by_id_and_user(cls, res_id, user_id):
        db = get_db()
        doc = db.reservations.find_one({"_id": _oid(res_id), "user_id": str(user_id)})
        return cls(doc) if doc else None

    @classmethod
    def get_by_user(cls, user_id):
        db = get_db()
        docs = list(db.reservations.find({"user_id": str(user_id)}).sort([("reservation_date", -1), ("reservation_time", -1)]))
        return [cls(d) for d in docs]

    @classmethod
    def get_all(cls):
        db = get_db()
        docs = list(db.reservations.find().sort([("reservation_date", -1), ("reservation_time", -1)]))
        return [cls(d) for d in docs]

    @classmethod
    def count_confirmed(cls, table_type, reservation_date, reservation_time):
        """Sum of table_quantity for confirmed reservations at given slot."""
        db = get_db()
        pipeline = [
            {"$match": {
                "table_type": table_type,
                "reservation_date": reservation_date,
                "reservation_time": reservation_time,
                "status": "confirmed",
            }},
            {"$group": {"_id": None, "total": {"$sum": "$table_quantity"}}}
        ]
        result = list(db.reservations.aggregate(pipeline))
        return result[0]["total"] if result else 0

    @classmethod
    def count_confirmed_by_date(cls, table_type, reservation_date):
        """Count confirmed reservations for a date (ignoring time)."""
        db = get_db()
        return db.reservations.count_documents({
            "table_type": table_type,
            "reservation_date": reservation_date,
            "status": "confirmed",
        })

    @classmethod
    def find_by_discount_code_and_user(cls, user_id, discount_code):
        db = get_db()
        doc = db.reservations.find_one({"user_id": str(user_id), "discount_code": discount_code})
        return cls(doc) if doc else None

    @classmethod
    def get_latest_by_user(cls, user_id):
        db = get_db()
        doc = db.reservations.find_one({"user_id": str(user_id)}, sort=[("_id", -1)])
        return cls(doc) if doc else None

    def save(self):
        db = get_db()
        db.reservations.update_one(
            {"_id": _oid(self.id)},
            {"$set": {"status": self.status}}
        )


# ---------------------------------------------------------------------------
# Favorite
# ---------------------------------------------------------------------------
class Favorite:
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.user_id = str(doc.get("user_id", ""))
        self.item_id = str(doc.get("item_id", ""))
        self.created_at = doc.get("created_at", datetime.utcnow())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_id": self.item_id,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @classmethod
    def get_by_user(cls, user_id):
        db = get_db()
        docs = list(db.favorites.find({"user_id": str(user_id)}))
        return [cls(d) for d in docs]

    @classmethod
    def get_by_user_and_item(cls, user_id, item_id):
        db = get_db()
        doc = db.favorites.find_one({"user_id": str(user_id), "item_id": str(item_id)})
        return cls(doc) if doc else None

    @classmethod
    def create(cls, user_id, item_id):
        db = get_db()
        result = db.favorites.insert_one({
            "user_id": str(user_id),
            "item_id": str(item_id),
            "created_at": datetime.utcnow(),
        })
        doc = db.favorites.find_one({"_id": result.inserted_id})
        return cls(doc)

    def delete(self):
        db = get_db()
        db.favorites.delete_one({"_id": _oid(self.id)})
