from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(80), nullable=False, default='customer')
    allergies = db.Column(db.Text, nullable=True, default="")
    preferences = db.Column(db.Text, nullable=True, default="")
    calorie_goal = db.Column(db.Float, nullable=True)
    protein_goal = db.Column(db.Float, nullable=True)
    carb_goal = db.Column(db.Float, nullable=True)
    fat_goal = db.Column(db.Float, nullable=True)
    orders = db.relationship('Order', backref='user', lazy=True)

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)
    def to_dict(self): return {"id": self.id, "username": self.username, "role": self.role, "allergies": self.allergies or "", "preferences": self.preferences or "", "calorie_goal": self.calorie_goal, "protein_goal": self.protein_goal, "carb_goal": self.carb_goal, "fat_goal": self.fat_goal}

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text)
    ingredients = db.Column(db.Text)
    diet = db.Column(db.String(50))
    price = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(100))
    calories = db.Column(db.Float, default=0.0)
    protein = db.Column(db.Float, default=0.0)
    carbs = db.Column(db.Float, default=0.0)
    fat = db.Column(db.Float, default=0.0)
    flavor_profile = db.Column(db.String(50))
    image_url = db.Column(db.String(500))

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description, "ingredients": self.ingredients, "diet": self.diet, "price": self.price, "category": self.category, "calories": self.calories, "protein": self.protein, "carbs": self.carbs, "fat": self.fat, "flavor_profile": self.flavor_profile, "image_url": self.image_url}

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "timestamp": self.timestamp.isoformat(), "total_price": self.total_price, "user_id": self.user_id, "items": [item.to_dict() for item in self.items]}

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(250), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)

    def to_dict(self):
        return {"item_name": self.item_name, "quantity": self.quantity, "unit_price": self.unit_price}

class InboxMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(250), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {"id": self.id, "subject": self.subject, "message": self.message, "timestamp": self.timestamp.isoformat(), "is_read": self.is_read}

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_name = db.Column(db.String(250), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id, "item_name": self.item_name, "quantity": self.quantity, "unit_price": self.unit_price}

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id, "item_id": self.item_id, "rating": self.rating, "timestamp": self.timestamp.isoformat()}
