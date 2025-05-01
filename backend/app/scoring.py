import math

TASTE_DIMENSIONS = ["sweetness", "saltiness", "sourness", "bitterness", "savoriness", "fattiness"]

def map_minutes_to_effort(minutes):
    if minutes is None:
        return "moderate" # Default if unknown
    if minutes <= 30:
        return "easy"
    if minutes <= 60:
        return "moderate"
    return "hard"

def calculate_effort_score(recipe_effort, user_effort_preference):
    if user_effort_preference is None:
        return 0.5 # Neutral score if no preference
    if recipe_effort == user_effort_preference:
        return 1.0
    # Allow adjacent matches (e.g., user wants easy, recipe is moderate)
    effort_levels = ["easy", "moderate", "hard"]
    try:
        recipe_idx = effort_levels.index(recipe_effort)
        pref_idx = effort_levels.index(user_effort_preference)
        if abs(recipe_idx - pref_idx) == 1:
            return 0.6 # Slightly lower score for adjacent match
    except ValueError:
        pass # Should not happen if mapping is correct
    return 0.1 # Low score for poor match

def calculate_flavor_score(recipe_taste, user_taste_pref):
    if not recipe_taste or not user_taste_pref:
        return 0.5 # Neutral score if data is missing
    
    total_difference = 0
    dimensions_counted = 0
    for dim in TASTE_DIMENSIONS:
        recipe_val = recipe_taste.get(dim)
        pref_val = user_taste_pref.get(dim)
        
        if recipe_val is not None and pref_val is not None:
            total_difference += abs(recipe_val - pref_val)
            dimensions_counted += 1
        
    if dimensions_counted == 0:
        return 0.5 # Neutral if no dimensions could be compared
    
    # Normalize difference (0-100 scale per dimension)
    max_possible_difference = dimensions_counted * 100
    normalized_difference = total_difference / max_possible_difference
    
    # Convert difference to similarity (1 = perfect match, 0 = max difference)
    similarity = 1.0 - normalized_difference
    return similarity

def score_recipe(recipe, available_ingredients, user_preferences):
    # 1. Inventory Score (Weight: 0.4)
    inventory_score = 0.0
    recipe_ingredients = set(ing["name"].lower() for ing in recipe.get("extendedIngredients", []))
    if recipe_ingredients:
        available_count = sum(1 for ing_name in recipe_ingredients if ing_name in available_ingredients)
        inventory_score = available_count / len(recipe_ingredients)

    # 2. Effort Score (Weight: 0.3)
    recipe_minutes = recipe.get("readyInMinutes")
    recipe_effort = map_minutes_to_effort(recipe_minutes)
    user_effort_pref = user_preferences.get("effort_tolerance", "moderate")
    effort_score = calculate_effort_score(recipe_effort, user_effort_pref)

    # 3. Flavor Score (Weight: 0.3)
    recipe_taste = recipe.get("taste_profile")
    user_taste_pref = user_preferences.get("taste_profile") # Fetched in main.py
    flavor_score = calculate_flavor_score(recipe_taste, user_taste_pref)

    # 4. Combined Weighted Score
    combined_score = (inventory_score * 0.4) + (effort_score * 0.3) + (flavor_score * 0.3)
    return combined_score

def score_and_sort_recipes(recipes, available_ingredients, user_preferences):
    # Score each recipe using combined score and sort descending
    for recipe in recipes:
        recipe["score"] = score_recipe(recipe, available_ingredients, user_preferences)
    return sorted(recipes, key=lambda r: r["score"], reverse=True)
