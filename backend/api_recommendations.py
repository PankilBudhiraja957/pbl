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
    from app import MenuItem
    algo = build_collaborative_filtering_model()
    if not algo:
        return jsonify({"message": "No recommendation data available"}), 404
    recs = cross_recommendations(current_user.id, algo, top_n=5)
    return jsonify([item.to_dict() for item in recs])

@recommendations_bp.route('/content', methods=['GET'])
@login_required
def content_recommendations():
    from app import MenuItem
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
    from app import MenuItem, User

    # Reload user from DB to get fresh nutrition goals
    user = User.query.get(current_user.id)
    calorie_goal = user.calorie_goal
    protein_goal = user.protein_goal
    carb_goal = user.carb_goal
    fat_goal = user.fat_goal

    # Get filters from request
    diet_filter = request.args.get('diet')
    category_filter = request.args.get('category')
    search_term = request.args.get('search', '').lower()
    max_price = request.args.get('max_price', type=float)

    logging.info(f"Nutrition goals for user {user.id}: calories={calorie_goal}, protein={protein_goal}, carbs={carb_goal}, fat={fat_goal}")

    if not all([calorie_goal, protein_goal, carb_goal, fat_goal]):
        logging.warning(f"User {user.id} has incomplete nutrition goals.")
        return jsonify({
            "status": "missing_goals",
            "message": "Please complete your nutrition goals in your profile first to get personalized recommendations"
        }), 200

    query = MenuItem.query

    # Apply Filters
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

    if max_price is not None:
        query = query.filter(MenuItem.price <= max_price)

    items = query.all()

    # Apply search filter and allergy check (if needed, though nutrition recommendations might be safer without allergies unless requested, but let's keep it consistent)
    user_allergies = user.allergies or ""
    allergies_list = [allergy.strip().lower() for allergy in user_allergies.split(',') if allergy.strip()]

    filtered_items = []
    for item in items:
        item_ingredients = (item.ingredients or "").lower()
        # Filter by allergies
        if any(allergy in item_ingredients for allergy in allergies_list):
            continue
            
        # Filter by search term
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

    suitable_items = []
    for item in filtered_items:
        if (item.calories <= meal_calorie_limit and
            item.protein <= meal_protein_limit and
            item.carbs <= meal_carb_limit and
            item.fat <= meal_fat_limit):
            suitable_items.append(item)

    logging.info(f"Suitable items count: {len(suitable_items)}")

    suitable_items.sort(key=lambda x: abs(x.calories - meal_calorie_limit) +
                                       abs(x.protein - meal_protein_limit) +
                                       abs(x.carbs - meal_carb_limit) +
                                       abs(x.fat - meal_fat_limit))

    recs = suitable_items[:5]
    logging.info(f"Returning {len(recs)} nutrition recommendations")
    return jsonify([item.to_dict() for item in recs])
