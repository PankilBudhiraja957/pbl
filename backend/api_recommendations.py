from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from recommendation import (
    build_collaborative_filtering_model,
    get_content_based_recommendations,
    get_time_based_suggestions,
    cross_recommendations,
    detect_order_anomalies,
)
import logging

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')


@recommendations_bp.route('/collaborative', methods=['GET'])
@login_required
def collaborative_recommendations():
    algo = build_collaborative_filtering_model()
    if not algo:
        return jsonify({"message": "No recommendation data available"}), 404
    recs = cross_recommendations(current_user.id, algo, top_n=5)
    return jsonify([item.to_dict() for item in recs])


@recommendations_bp.route('/content', methods=['GET'])
@login_required
def content_recommendations():
    recs = get_content_based_recommendations(current_user.id, top_n=5)
    return jsonify([item.to_dict() for item in recs])


@recommendations_bp.route('/time-based', methods=['GET'])
def time_based_recommendations():
    recs = get_time_based_suggestions()
    return jsonify([item.to_dict() for item in recs])


@recommendations_bp.route('/anomalies', methods=['GET'])
@login_required
def order_anomalies():
    anomalies = detect_order_anomalies()
    return jsonify({"anomalous_order_ids": anomalies})


@recommendations_bp.route('/nutrition', methods=['GET'])
@login_required
def nutrition_recommendations():
    from modals import MenuItem
    from app import _get_user_profile

    profile = _get_user_profile(current_user.id)
    calorie_goal = profile.get("calorie_goal")
    protein_goal = profile.get("protein_goal")
    carb_goal = profile.get("carb_goal")
    fat_goal = profile.get("fat_goal")

    diet_filter = request.args.get('diet')
    category_filter = request.args.get('category')
    search_term = request.args.get('search', '').lower()
    max_price = request.args.get('max_price', type=float)

    logging.info(f"Nutrition goals for user {current_user.id}: calories={calorie_goal}, protein={protein_goal}, carbs={carb_goal}, fat={fat_goal}")

    if not all([calorie_goal, protein_goal, carb_goal, fat_goal]):
        logging.warning(f"User {current_user.id} has incomplete nutrition goals.")
        return jsonify({
            "status": "missing_goals",
            "message": "Please complete your nutrition goals in your profile first to get personalized recommendations"
        }), 200

    import re as _re
    mongo_filter = {}
    if diet_filter and diet_filter != 'All':
        mongo_filter["diet"] = _re.compile(f"^{_re.escape(diet_filter)}$", _re.IGNORECASE)
    if category_filter and category_filter != 'All':
        mongo_filter["category"] = _re.compile(f"^{_re.escape(category_filter)}$", _re.IGNORECASE)
    if max_price is not None:
        mongo_filter["price"] = {"$lte": max_price}

    items = MenuItem.get_all(mongo_filter)

    user_allergies = profile.get("allergies", "")
    allergies_list = [a.strip().lower() for a in user_allergies.split(',') if a.strip()]

    filtered_items = []
    for item in items:
        item_ingredients = (item.ingredients or "").lower()
        if any(allergy in item_ingredients for allergy in allergies_list):
            continue
        if search_term:
            if search_term not in (item.name or '').lower() and \
               search_term not in (item.description or '').lower() and \
               search_term not in item_ingredients:
                continue
        filtered_items.append(item)

    logging.info(f"Filtered menu items: {len(filtered_items)}")

    meal_calorie_limit = calorie_goal / 3
    meal_protein_limit = protein_goal / 3
    meal_carb_limit = carb_goal / 3
    meal_fat_limit = fat_goal / 3

    suitable_items = [
        item for item in filtered_items
        if (item.calories or 0) <= meal_calorie_limit
        and (item.protein or 0) <= meal_protein_limit
        and (item.carbs or 0) <= meal_carb_limit
        and (item.fat or 0) <= meal_fat_limit
    ]

    suitable_items.sort(key=lambda x: abs((x.calories or 0) - meal_calorie_limit) +
                                       abs((x.protein or 0) - meal_protein_limit) +
                                       abs((x.carbs or 0) - meal_carb_limit) +
                                       abs((x.fat or 0) - meal_fat_limit))

    recs = suitable_items[:5]
    logging.info(f"Returning {len(recs)} nutrition recommendations")
    return jsonify([item.to_dict() for item in recs])
