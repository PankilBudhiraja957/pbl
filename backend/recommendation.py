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
    """
    Builds a collaborative filtering model using sklearn NearestNeighbors.
    """
    from app import Rating
    global collaborative_model_data
    if collaborative_model_data is not None:
        return collaborative_model_data

    # Fetch ratings data
    ratings = Rating.query.all()
    if not ratings:
        return None

    data = [(r.user_id, r.item_id, r.rating) for r in ratings]
    df = pd.DataFrame(data, columns=['user_id', 'item_id', 'rating'])

    # Create user-item matrix
    user_item_matrix = df.pivot_table(index='user_id', columns='item_id', values='rating', fill_value=0)

    # Fit KNN model
    model = NearestNeighbors(metric='cosine', algorithm='brute')
    model.fit(user_item_matrix.values)

    collaborative_model_data = (model, user_item_matrix)
    return collaborative_model_data

def get_content_based_recommendations(user_id, top_n=5):
    """
    Provides content-based recommendations based on user's preferences and past orders.
    """
    global content_vectorizer
    user = User.query.get(user_id)
    if not user:
        return []

    # Get user's past orders
    orders = Order.query.filter_by(user_id=user_id).all()
    ordered_items = set()
    for order in orders:
        for item in order.items:
            ordered_items.add(item.item_name)

    # Get all menu items
    all_items = MenuItem.query.all()
    if not all_items:
        return []

    # Prepare content features
    item_texts = []
    for item in all_items:
        text = f"{item.name} {item.description or ''} {item.ingredients or ''} {item.category or ''}"
        item_texts.append(text)

    if content_vectorizer is None:
        content_vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = content_vectorizer.fit_transform(item_texts)
    else:
        tfidf_matrix = content_vectorizer.transform(item_texts)

    # Calculate similarity with user's preferences
    user_profile = f"{user.preferences or ''} {user.allergies or ''}"
    if user_profile.strip():
        user_vector = content_vectorizer.transform([user_profile])
        similarities = cosine_similarity(user_vector, tfidf_matrix).flatten()
    else:
        # If no preferences, use average similarity
        similarities = np.mean(cosine_similarity(tfidf_matrix), axis=0)

    # Rank items
    item_scores = list(zip(all_items, similarities))
    item_scores.sort(key=lambda x: x[1], reverse=True)

    # Filter out already ordered items and return top recommendations
    recommendations = []
    for item, score in item_scores:
        if item.name not in ordered_items:
            recommendations.append(item)
            if len(recommendations) >= top_n:
                break

    return recommendations

def cross_recommendations(user_id, algo, top_n=5):
    """
    Generates collaborative filtering recommendations for a user.
    """
    from app import MenuItem
    if not algo:
        return []

    model, user_item_matrix = algo

    # Check if user exists in matrix
    if user_id not in user_item_matrix.index:
        return []

    # Get user's index
    user_idx = user_item_matrix.index.get_loc(user_id)
    user_vector = user_item_matrix.iloc[user_idx].values.reshape(1, -1)

    # Find similar users
    distances, indices = model.kneighbors(user_vector, n_neighbors=6)  # 5 neighbors + self

    # Get similar users (exclude self)
    similar_users = [user_item_matrix.index[i] for i in indices[0] if user_item_matrix.index[i] != user_id]

    # Collect recommendations
    recommendations = {}
    for sim_user in similar_users:
        sim_user_ratings = user_item_matrix.loc[sim_user]
        for item_id, rating in sim_user_ratings.items():
            if rating > 3 and user_item_matrix.loc[user_id, item_id] == 0:  # High rating and not rated by user
                if item_id not in recommendations:
                    recommendations[item_id] = 0
                recommendations[item_id] += rating

    # Sort by score
    sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)

    # Get top recommended items
    recommended_items = []
    for item_id, _ in sorted_recs[:top_n]:
        item = MenuItem.query.get(item_id)
        if item:
            recommended_items.append(item)

    return recommended_items

def get_time_based_suggestions():
    """
    Provides time-based suggestions (e.g., popular items from recent orders).
    """
    # Get orders from the last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_orders = Order.query.filter(Order.timestamp >= week_ago).all()

    item_counts = {}
    for order in recent_orders:
        for item in order.items:
            item_counts[item.item_name] = item_counts.get(item.item_name, 0) + item.quantity

    # Sort by popularity
    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)

    # Return top 5 popular items
    suggestions = []
    for item_name, _ in sorted_items[:5]:
        item = MenuItem.query.filter_by(name=item_name).first()
        if item:
            suggestions.append(item)

    return suggestions

def detect_order_anomalies():
    """
    Detects anomalous orders using Isolation Forest.
    """
    global anomaly_detector

    # Get order data
    orders = Order.query.all()
    if len(orders) < 10:  # Need minimum data for anomaly detection
        return []

    # Prepare features: total_price, number of items, average item price
    features = []
    for order in orders:
        num_items = len(order.items)
        avg_price = order.total_price / num_items if num_items > 0 else 0
        features.append([order.total_price, num_items, avg_price])

    if anomaly_detector is None:
        anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        anomaly_detector.fit(features)

    # Predict anomalies
    predictions = anomaly_detector.predict(features)

    # Return IDs of anomalous orders
    anomalous_orders = []
    for i, pred in enumerate(predictions):
        if pred == -1:  # Anomalous
            anomalous_orders.append(orders[i].id)

    return anomalous_orders
