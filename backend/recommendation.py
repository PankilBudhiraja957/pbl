from sklearn.ensemble import IsolationForest
from sklearn.neighbors import NearestNeighbors
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Global variables for ML models
collaborative_model_data = None
content_vectorizer = None
anomaly_detector = None


def build_collaborative_filtering_model():
    """Builds a collaborative filtering model using sklearn NearestNeighbors."""
    from modals import Rating
    global collaborative_model_data
    if collaborative_model_data is not None:
        return collaborative_model_data

    ratings = Rating.get_all()
    if not ratings:
        return None

    data = [(r.user_id, r.item_id, r.rating) for r in ratings]
    df = pd.DataFrame(data, columns=['user_id', 'item_id', 'rating'])
    user_item_matrix = df.pivot_table(index='user_id', columns='item_id', values='rating', fill_value=0)

    n_users = len(user_item_matrix)
    if n_users < 2:
        return None  # Need at least 2 users for collaborative filtering

    # n_neighbors must be <= number of samples
    n_neighbors = min(6, n_users)
    model = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=n_neighbors)
    model.fit(user_item_matrix.values)

    collaborative_model_data = (model, user_item_matrix)
    return collaborative_model_data


def get_content_based_recommendations(user_id, top_n=5):
    """Provides content-based recommendations based on user's preferences and past orders."""
    from modals import User, Order, MenuItem
    global content_vectorizer

    user = User.get_by_id(user_id)
    if not user:
        return []

    orders = Order.get_by_user(user_id)
    ordered_items = set()
    for order in orders:
        for item in order.items:
            ordered_items.add(item.item_name)

    all_items = MenuItem.get_all()
    if not all_items:
        return []

    item_texts = []
    for item in all_items:
        text = f"{item.name} {item.description or ''} {item.ingredients or ''} {item.category or ''}"
        item_texts.append(text)

    if content_vectorizer is None:
        content_vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = content_vectorizer.fit_transform(item_texts)
    else:
        tfidf_matrix = content_vectorizer.transform(item_texts)

    # Get profile from MongoDB
    from app import _get_user_profile
    profile = _get_user_profile(user_id)
    user_profile = f"{profile.get('preferences', '')} {profile.get('allergies', '')}"

    if user_profile.strip():
        user_vector = content_vectorizer.transform([user_profile])
        similarities = cosine_similarity(user_vector, tfidf_matrix).flatten()
    else:
        similarities = np.mean(cosine_similarity(tfidf_matrix), axis=0)

    item_scores = list(zip(all_items, similarities))
    item_scores.sort(key=lambda x: x[1], reverse=True)

    recommendations = []
    for item, score in item_scores:
        if item.name not in ordered_items:
            recommendations.append(item)
            if len(recommendations) >= top_n:
                break

    return recommendations


def cross_recommendations(user_id, algo, top_n=5):
    """Generates collaborative filtering recommendations for a user."""
    from modals import MenuItem
    if not algo:
        return []

    model, user_item_matrix = algo

    if user_id not in user_item_matrix.index:
        return []

    user_idx = user_item_matrix.index.get_loc(user_id)
    user_vector = user_item_matrix.iloc[user_idx].values.reshape(1, -1)
    n_neighbors = min(6, len(user_item_matrix))
    distances, indices = model.kneighbors(user_vector, n_neighbors=n_neighbors)

    similar_users = [user_item_matrix.index[i] for i in indices[0] if user_item_matrix.index[i] != user_id]

    recommendations = {}
    for sim_user in similar_users:
        sim_user_ratings = user_item_matrix.loc[sim_user]
        for item_id, rating in sim_user_ratings.items():
            if rating > 3 and user_item_matrix.loc[user_id, item_id] == 0:
                if item_id not in recommendations:
                    recommendations[item_id] = 0
                recommendations[item_id] += rating

    sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)

    recommended_items = []
    for item_id, _ in sorted_recs[:top_n]:
        item = MenuItem.get_by_id(str(item_id))
        if item:
            recommended_items.append(item)

    return recommended_items


def get_time_based_suggestions():
    """Provides time-based suggestions based on popular items from recent orders."""
    from modals import Order, MenuItem
    week_ago = datetime.utcnow() - timedelta(days=7)

    from modals import get_db
    db = get_db()
    recent_order_docs = list(db.orders.find({"timestamp": {"$gte": week_ago}}))

    item_counts = {}
    for doc in recent_order_docs:
        order_id = str(doc["_id"])
        order_item_docs = list(db.order_items.find({"order_id": order_id}))
        for oi in order_item_docs:
            name = oi.get("item_name", "")
            item_counts[name] = item_counts.get(name, 0) + oi.get("quantity", 1)

    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)

    suggestions = []
    for item_name, _ in sorted_items[:5]:
        item = MenuItem.find_ilike(item_name)
        if item:
            suggestions.append(item)

    return suggestions


def detect_order_anomalies():
    """Detects anomalous orders using Isolation Forest."""
    from modals import Order
    global anomaly_detector

    orders = Order.get_all()
    if len(orders) < 10:
        return []

    features = []
    for order in orders:
        num_items = len(order.items)
        avg_price = order.total_price / num_items if num_items > 0 else 0
        features.append([order.total_price, num_items, avg_price])

    if anomaly_detector is None:
        anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        anomaly_detector.fit(features)

    predictions = anomaly_detector.predict(features)

    anomalous_orders = []
    for i, pred in enumerate(predictions):
        if pred == -1:
            anomalous_orders.append(orders[i].id)

    return anomalous_orders
