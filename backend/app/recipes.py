import json
import os
import logging
import httpx
import re
from openai import OpenAI
from app.cache import get_cache, set_cache
from app.models import get_db_connection
from app.scoring import score_and_sort_recipes
from app.inventory import get_inventory_ingredient_names
from typing import List, Optional, Dict, Any

def clean_ingredient_name(ingredient_name: str) -> str:
    """
    Remove packaging size, weight, or quantity information from ingredient names.
    
    This function cleans ingredient names that may include size information after a hyphen.
    For example: "Beef Stew - 20oz" becomes "Beef Stew"
    
    Args:
        ingredient_name: The raw ingredient name that may contain sizing information
        
    Returns:
        The cleaned ingredient name without sizing information
    """
    if not ingredient_name:
        return ""
    
    # Pattern to match: text - number + optional units or "pack"/"Pack"
    # This regex matches: " - 20oz", " - 510g", " - 4 Pack", " - 10", etc.
    pattern = r'\s+-\s+\d+(?:\s*(?:oz|OZ|g|ml|ML|pack|Pack|lb|LB))?\s*$'
    
    # Replace the pattern with an empty string
    cleaned = re.sub(pattern, '', ingredient_name)
    
    return cleaned

# Add default values for tests/when env vars aren't available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy_key_for_testing")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "dummy_key_for_testing")  
SPOONACULAR_API_URL = os.getenv("SPOONACULAR_API_URL", "https://api.spoonacular.com/recipes/complexSearch")

# Only set up OpenAI client if we have a real API key
if "dummy" not in OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

INGREDIENT_CLASSIFICATION_PROMPT = '''
You are a culinary assistant.
Given a recipe, classify each ingredient as:
- Essential: Defines the dish; cannot omit.
- Important: Strongly affects flavor or texture.
- Optional: Can be omitted with little impact.
Also mark whether the user has this ingredient.
Output strictly as JSON array:
[
  {
    "ingredient": "ingredient name",
    "category": "Essential | Important | Optional",
    "in_inventory": true | false,
    "confidence": 0.0 to 1.0
  },
  ...
]
Recipe: {recipe_name}
Instructions: {instructions}
Ingredients: {ingredients_list}
User Inventory: {user_inventory_list}
'''

SPOONACULAR_RECIPE_INFO_URL = "https://api.spoonacular.com/recipes/{id}/information"
SPOONACULAR_TASTE_URL = "https://api.spoonacular.com/recipes/{id}/tasteWidget.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_recipes_from_spoonacular(ingredients, number=10, max_ready_time=None, dietary_restrictions=None):
    """
    Fetch recipes from Spoonacular API based on available ingredients.
    
    Args:
        ingredients: List of ingredients to include in the search
        number: Maximum number of recipes to return (default: 10)
        max_ready_time: Maximum preparation time in minutes (optional)
        dietary_restrictions: Dictionary of dietary restrictions (optional)
        
    Returns:
        List of recipes matching the search criteria
    """
    # If we have many ingredients, don't require all of them in each recipe
    if len(ingredients) > 4:
        logger.info(f"Using intelligent ingredient grouping for {len(ingredients)} ingredients")
        
        # We'll search with multiple intelligent combinations and merge unique results
        all_results = []
        results_ids = set()  # Track IDs to avoid duplicates
        
        # Get meaningful ingredient combinations using AI
        ingredient_groups = get_meaningful_ingredient_combinations(ingredients)
        
        # Limit to a reasonable number of groups
        max_groups = min(8, len(ingredient_groups))
        ingredient_groups = ingredient_groups[:max_groups]
        
        # Run searches for each group
        for group in ingredient_groups:
            logger.info(f"Searching Spoonacular with ingredient combination: {group}")
            # Get cached or fetch new results for this group
            group_results = _fetch_recipes_for_ingredient_group(
                group, 
                number=max(3, number // max_groups), 
                max_ready_time=max_ready_time,
                dietary_restrictions=dietary_restrictions
            )
            
            # Add unique results to our collection
            for recipe in group_results:
                if recipe["id"] not in results_ids:
                    all_results.append(recipe)
                    results_ids.add(recipe["id"])
            
            # If we have enough results already, stop making more API calls
            if len(all_results) >= number:
                break
                
        logger.info(f"Combined intelligent search found {len(all_results)} unique recipes")
        return all_results[:number]
    else:
        # For small ingredient lists (≤ 4), use the original direct method
        logger.info(f"Using direct Spoonacular search with {len(ingredients)} ingredients")
        return _fetch_recipes_for_ingredient_group(ingredients, number, max_ready_time, dietary_restrictions)

def get_meaningful_ingredient_combinations(ingredients):
    """
    Use AI to generate meaningful combinations of ingredients that could go well together in recipes.
    
    Args:
        ingredients: List of ingredients available in inventory
        
    Returns:
        List of ingredient combination groups (lists)
    """
    # Check cache first
    cache_key = f"ai:ingredient_combinations:{','.join(sorted(ingredients))}"
    cached = get_cache(cache_key)
    if cached:
        logger.info("Using cached ingredient combinations")
        return cached
    
    # If we don't have OpenAI access, fall back to heuristics
    if "dummy" in OPENAI_API_KEY or client is None:
        logger.warning("No valid OpenAI API key - using heuristic ingredient combinations")
        return _create_heuristic_ingredient_combinations(ingredients)
    
    try:
        # Craft a prompt asking the AI to create logical ingredient combinations
        prompt = f"""
You are a culinary expert. Given a list of ingredients, identify 5-8 meaningful combinations that would work well together in actual recipes.

Don't just group ingredients arbitrarily. Consider:
1. Which ingredients naturally complement each other in cooking
2. Common recipe patterns (protein + starch + vegetable, etc.)
3. Cuisine-specific combinations
4. The main ingredient plus supporting ingredients

For each combination, include 3-5 ingredients. Don't try to use every ingredient - focus on combinations that would make sense in real recipes.

Available ingredients: {', '.join(ingredients)}

Response format: A JSON array of arrays, where each sub-array is a logical ingredient combination.
Example: [["pasta", "tomato sauce", "cheese"], ["tuna", "mayonnaise", "bread"], ...]
"""

        # Make the AI call
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            temperature=0.3,
            store=True
        )
        
        result_text = response.output_text
        
        # Simple debug logging without complex escaping
        logger.info(f"Raw ingredient combinations response starts with: {result_text[:50]}")
        
        # Try multiple parsing approaches
        result = None
        
        # First, try direct JSON parsing after removing whitespace
        try:
            result = json.loads(result_text.strip())
            logger.info("Standard JSON parsing successful for ingredient combinations")
        except json.JSONDecodeError:
            # Direct parsing failed, try other approaches
            pass
            
        # If direct parsing failed, try to find a complete JSON array
        if result is None:
            try:
                import re
                # Look for array pattern
                json_match = re.search(r'\[\s*\[.*\]\s*\]', result_text, re.DOTALL)
                if json_match:
                    array_text = json_match.group(0)
                    result = json.loads(array_text)
                    logger.info("JSON array extraction successful for ingredient combinations")
            except Exception:
                # Array extraction failed
                pass
                
        # Last resort: Extract individual arrays manually
        if result is None:
            try:
                import re
                # Look for inner arrays
                inner_arrays = re.findall(r'\[\s*"[^"]+(?:",\s*"[^"]+")*"\s*\]', result_text)
                
                if inner_arrays:
                    result = []
                    for array_str in inner_arrays:
                        try:
                            inner_array = json.loads(array_str)
                            if isinstance(inner_array, list) and all(isinstance(i, str) for i in inner_array):
                                result.append(inner_array)
                        except:
                            pass
                    
                    if result:
                        logger.info(f"Successfully extracted {len(result)} ingredient combinations manually")
            except Exception as e:
                logger.error(f"Manual extraction failed: {e}")
        
        # If all parsing attempts failed, use a fallback
        if not result:
            logger.warning("All parsing attempts failed for ingredient combinations, using fallback")
            return _create_heuristic_ingredient_combinations(ingredients)
        
        # Validate the result is a list of ingredient lists
        if not isinstance(result, list) or not all(isinstance(group, list) for group in result):
            logger.warning(f"Expected list of lists but got {type(result)}")
            return _create_heuristic_ingredient_combinations(ingredients)
            
        # Flatten any incorrectly nested lists and ensure all items are strings
        cleaned_result = []
        for group in result:
            if not group:  # Skip empty groups
                continue
                
            # Handle case where group might be a nested list or contain non-string elements
            cleaned_group = []
            for item in group:
                if isinstance(item, list):  # Handle nested lists
                    cleaned_group.extend([str(i) for i in item])
                elif item:  # Add non-empty items, converting to string if needed
                    cleaned_group.append(str(item))
                    
            if cleaned_group:  # Only add non-empty groups
                cleaned_result.append(cleaned_group)
                
        # Cache the result for future use
        if cleaned_result:
            set_cache(cache_key, cleaned_result, ex=86400)  # Cache for 1 day
            return cleaned_result
        else:
            logger.warning("No valid ingredient combinations after cleaning")
            return _create_heuristic_ingredient_combinations(ingredients)
            
    except Exception as e:
        logger.error(f"Error generating ingredient combinations: {str(e)}")
        return _create_heuristic_ingredient_combinations(ingredients)

def format_recipe_output(recipes):
    """
    Format the recipe results to be more user-friendly and display better matching info.
    
    Args:
        recipes: List of recipe results from Spoonacular with used/missed ingredient info
        
    Returns:
        List of cleaned up recipe dictionaries with better fit information
    """
    formatted_recipes = []
    
    for recipe in recipes:
        # Calculate the fit score - how well this matches what's in inventory
        total_ingredients = recipe.get("usedIngredientCount", 0) + recipe.get("missedIngredientCount", 0)
        if total_ingredients > 0:
            fit_percentage = (recipe.get("usedIngredientCount", 0) / total_ingredients) * 100
        else:
            fit_percentage = 0
            
        # Extract the essential info about ingredients
        used_ingredients = [
            {
                "name": ing.get("name", "unknown"),
                "amount": f"{ing.get('amount', '?')} {ing.get('unit', '')}"
            }
            for ing in recipe.get("usedIngredients", [])
        ]
        
        missed_ingredients = [
            {
                "name": ing.get("name", "unknown"),
                "amount": f"{ing.get('amount', '?')} {ing.get('unit', '')}"
            }
            for ing in recipe.get("missedIngredients", [])
        ]
        
        # Create cleaned up representation
        formatted_recipe = {
            "id": recipe.get("id"),
            "title": recipe.get("title"),
            "image": recipe.get("image"),
            "readyInMinutes": recipe.get("readyInMinutes"),
            "servings": recipe.get("servings"),
            "sourceUrl": recipe.get("sourceUrl"),
            "fit_score": {
                "percentage": round(fit_percentage, 1),
                "have": recipe.get("usedIngredientCount", 0),
                "need_to_buy": recipe.get("missedIngredientCount", 0),
                "total": total_ingredients
            },
            "ingredients": {
                "have": used_ingredients,
                "need_to_buy": missed_ingredients
            },
            "summary": recipe.get("summary"),
            "instructions": recipe.get("instructions")
        }
        
        formatted_recipes.append(formatted_recipe)
    
    # Sort by fit score (highest percentage first)
    return sorted(formatted_recipes, key=lambda r: r["fit_score"]["percentage"], reverse=True)

def suggest_recipes_with_classification(
    user_preferences,
    inventory_override=None,
    use_ai_filtering=True,
    max_ingredients=20,
    max_ready_time=None
):
    """
    Main function to suggest recipes with AI classification of ingredients.
    
    Args:
        user_preferences: User's preference dictionary
        inventory_override: Optional list of ingredients to use instead of fetching from Grocy
        use_ai_filtering: Whether to use AI to filter non-food items from inventory
        max_ingredients: Maximum number of ingredients to use in recipe search
        max_ready_time: Maximum recipe preparation time in minutes
        
    Returns:
        List of recipe dictionaries with scores and classified ingredients
    """
    # 1. Get inventory ingredients (from override or Grocy)
    if inventory_override:
        available_ingredients = inventory_override
        logger.info(f"Using inventory override with {len(available_ingredients)} ingredients")
    else:
        available_ingredients = get_inventory_ingredient_names(
            use_ai_filtering=use_ai_filtering,
            max_ingredients=max_ingredients
        )
        logger.info(f"Fetched {len(available_ingredients)} ingredients from inventory")
        
    if not available_ingredients:
        logger.warning("No ingredients found in inventory")
        return []
        
    # 2. Get dietary restrictions if user has them
    dietary_restrictions = user_preferences.get("dietary_restrictions")
    
    # 3. Fetch recipe suggestions from Spoonacular
    recipes = fetch_recipes_from_spoonacular(
        available_ingredients,
        number=10,
        max_ready_time=max_ready_time,
        dietary_restrictions=dietary_restrictions
    )
    
    if not recipes:
        logger.warning("No recipes found from Spoonacular")
        return []
        
    logger.info(f"Found {len(recipes)} recipes from Spoonacular")
    
    # 4. Get detailed info for each recipe
    for recipe in recipes:
        # Get full recipe details if not already included
        if "instructions" not in recipe:
            recipe_id = recipe.get("id")
            details = fetch_recipe_details(recipe_id)
            if details:
                recipe.update(details)
                
        # Get taste profile if not already included
        if "taste_profile" not in recipe:
            recipe_id = recipe.get("id")
            taste = fetch_recipe_taste_profile(recipe_id)
            if taste:
                recipe["taste_profile"] = taste
                
    # 5. Extract ingredient names from each recipe
    for recipe in recipes:
        # Extract ingredient names
        ingredients_list = [
            ing.get("name", "").lower() 
            for ing in recipe.get("extendedIngredients", [])
        ]
        recipe["ingredients_list"] = ingredients_list
        
        # Classify ingredients with AI
        classified = classify_ingredients_with_ai(
            recipe,
            available_ingredients,
            ingredients_list
        )
        recipe["classified_ingredients"] = classified
        
        # Convert classified ingredients to used/missed format
        recipe = convert_classified_to_used_missed(recipe, available_ingredients)
        
    # 6. Score and sort recipes
    scored_recipes = score_and_sort_recipes(recipes, available_ingredients, user_preferences)
    
    return scored_recipes

def classify_ingredients_with_ai(recipe, user_inventory, recipe_ingredients_list):
    """
    Use AI to classify recipe ingredients as Essential, Important, or Optional.
    
    Args:
        recipe: Recipe dictionary with details
        user_inventory: List of ingredients available in user's inventory
        recipe_ingredients_list: List of ingredient names from the recipe
        
    Returns:
        List of dictionaries with ingredient classifications
    """
    # Create cache key based on recipe ID and inventory hash
    recipe_id = recipe.get("id")
    inventory_hash = hash(tuple(sorted(user_inventory)))
    cache_key = f"ai:ingredient_classification:{recipe_id}:{inventory_hash}"
    
    # Check cache first
    cached = get_cache(cache_key)
    if cached:
        logger.info(f"Using cached ingredient classification for recipe {recipe_id}")
        return cached
    
    # If we don't have OpenAI access, fall back to simple classification
    if "dummy" in OPENAI_API_KEY or client is None:
        logger.warning(f"No valid OpenAI API key - using simple classification for recipe {recipe_id}")
        return _create_simple_ingredient_classification(recipe_ingredients_list, user_inventory)
    
    try:
        # Format the recipe details for the prompt
        recipe_name = recipe.get("title", "Unknown Recipe")
        instructions = recipe.get("instructions", "Not available")
        ingredients_text = ", ".join(recipe_ingredients_list)
        inventory_text = ", ".join(user_inventory)
        
        # Prepare the prompt
        prompt = INGREDIENT_CLASSIFICATION_PROMPT.format(
            recipe_name=recipe_name,
            instructions=instructions,
            ingredients_list=ingredients_text,
            user_inventory_list=inventory_text
        )
        
        # Make the AI call
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            temperature=0.2,
            store=True
        )
        
        result_text = response.output_text
        
        # Try to parse the result
        try:
            # Direct JSON parsing
            result = json.loads(result_text)
            if isinstance(result, list):
                logger.info(f"Successfully classified {len(result)} ingredients for recipe {recipe_id}")
                
                # Validate and clean each item
                valid_items = []
                for item in result:
                    if isinstance(item, dict) and "ingredient" in item and "category" in item:
                        valid_item = {
                            "ingredient": str(item.get("ingredient", "")),
                            "category": str(item.get("category", "Optional")),
                            "in_inventory": bool(item.get("in_inventory", False)),
                            "confidence": float(item.get("confidence", 0.5))
                        }
                        valid_items.append(valid_item)
                
                # Cache the result for 24 hours
                if valid_items:
                    set_cache(cache_key, valid_items, ex=86400)
                    return valid_items
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response as JSON for recipe {recipe_id}")
            # Try regex or other parsing approaches
        
        # If we got here, there was a parsing failure
        logger.warning(f"Falling back to simple classification for recipe {recipe_id}")
        return _create_simple_ingredient_classification(recipe_ingredients_list, user_inventory)
            
    except Exception as e:
        logger.error(f"Error classifying ingredients with AI for recipe {recipe_id}: {str(e)}")
        return _create_simple_ingredient_classification(recipe_ingredients_list, user_inventory)

def convert_classified_to_used_missed(recipe, available_ingredients):
    """
    Convert AI classified ingredients into the format expected by format_recipe_output.
    
    Args:
        recipe: Recipe dictionary with classified_ingredients field
        available_ingredients: List of ingredients available in inventory
        
    Returns:
        Updated recipe with usedIngredients and missedIngredients fields
    """
    classified = recipe.get("classified_ingredients", [])
    if not classified:
        return recipe
    
    # Initialize used and missed ingredient lists
    used_ingredients = []
    missed_ingredients = []
    
    # Get extended ingredients for amounts and units
    extended_ingredients = recipe.get("extendedIngredients", [])
    ingredient_details = {}
    for ing in extended_ingredients:
        name = ing.get("name", "").lower()
        ingredient_details[name] = {
            "amount": ing.get("amount", 0),
            "unit": ing.get("unit", "")
        }
    
    # Process each classified ingredient
    for ing in classified:
        name = ing.get("ingredient", "").lower()
        in_inventory = ing.get("in_inventory", False)
        
        # Get details for this ingredient
        details = ingredient_details.get(name, {"amount": 0, "unit": ""})
        
        ingredient_info = {
            "name": name,
            "amount": details["amount"],
            "unit": details["unit"]
        }
        
        # Add to appropriate list
        if in_inventory:
            used_ingredients.append(ingredient_info)
        else:
            missed_ingredients.append(ingredient_info)
    
    # Update the recipe with used and missed ingredient counts and lists
    recipe["usedIngredientCount"] = len(used_ingredients)
    recipe["missedIngredientCount"] = len(missed_ingredients)
    recipe["usedIngredients"] = used_ingredients
    recipe["missedIngredients"] = missed_ingredients
    
    return recipe

def _create_simple_ingredient_classification(ingredient_list, user_inventory):
    """
    Create a simple ingredient classification without AI.
    Assumes first few ingredients are Essential, middle ones are Important, rest are Optional.
    
    Args:
        ingredient_list: List of ingredient names
        user_inventory: List of ingredients in user's inventory
        
    Returns:
        List of classification dictionaries
    """
    classifications = []
    
    # Simple heuristic - first 1/3 are Essential, next 1/3 are Important, rest Optional
    total = len(ingredient_list)
    essential_count = max(1, total // 3)
    important_count = max(1, total // 3)
    
    for i, ingredient in enumerate(ingredient_list):
        in_inventory = any(inv_item.lower() in ingredient.lower() or ingredient.lower() in inv_item.lower() 
                          for inv_item in user_inventory)
        
        if i < essential_count:
            category = "Essential"
            confidence = 0.8
        elif i < essential_count + important_count:
            category = "Important" 
            confidence = 0.7
        else:
            category = "Optional"
            confidence = 0.6
            
        classifications.append({
            "ingredient": ingredient,
            "category": category,
            "in_inventory": in_inventory,
            "confidence": confidence
        })
        
    return classifications

def _fetch_recipes_for_ingredient_group(ingredients, number=5, max_ready_time=None, dietary_restrictions=None):
    """
    Helper function to fetch recipes from Spoonacular for a specific set of ingredients.
    
    Args:
        ingredients: List of ingredients to search with
        number: Maximum number of recipes to return
        max_ready_time: Maximum preparation time in minutes (optional)
        dietary_restrictions: Dictionary of dietary restrictions (optional)
        
    Returns:
        List of recipe results from Spoonacular API
    """
    # Check cache first
    cache_key = f"spoon:recipes:{','.join(sorted(ingredients))}"
    if max_ready_time:
        cache_key += f":time{max_ready_time}"
    if dietary_restrictions:
        diet_str = "_".join([f"{k}:{v}" for k, v in sorted(dietary_restrictions.items())])
        cache_key += f":diet{diet_str}"
    cached = get_cache(cache_key)
    if cached:
        logger.info(f"Using cached recipe results for {len(ingredients)} ingredients")
        return cached
    
    # No cache, do API call
    try:
        # Build query parameters
        comma_ingredients = ",".join(ingredients)
        params = {
            "apiKey": SPOONACULAR_API_KEY,
            "ingredients": comma_ingredients,
            "number": number,
            "ranking": 2, # maximize used ingredients
            "ignorePantry": False, # count pantry items
            "fillIngredients": True, # get detailed ingredient info
            "addRecipeInformation": True # get full recipe details
        }
        
        # Add optional parameters
        if max_ready_time:
            params["maxReadyTime"] = max_ready_time
            
        # Add dietary restrictions if provided
        if dietary_restrictions:
            # Handle diet (vegetarian, vegan, etc.)
            if "diet" in dietary_restrictions:
                params["diet"] = dietary_restrictions["diet"]
                
            # Handle intolerances (dairy, gluten, etc.)
            if "intolerances" in dietary_restrictions:
                params["intolerances"] = ",".join(dietary_restrictions["intolerances"])
        
        # Make the API request
        logger.info(f"Calling Spoonacular API for {len(ingredients)} ingredients")
        response = httpx.get(SPOONACULAR_API_URL, params=params)
        
        # Check for errors
        if response.status_code != 200:
            logger.error(f"Spoonacular API error: {response.status_code}, {response.text}")
            return []
            
        # Parse response
        data = response.json()
        results = data.get("results", [])
        logger.info(f"Spoonacular returned {len(results)} recipes")
        
        # Cache results
        if results:
            set_cache(cache_key, results, ex=3600)  # Cache for 1 hour
            
        return results
        
    except Exception as e:
        logger.error(f"Error fetching recipes from Spoonacular: {str(e)}")
        return []

def _create_heuristic_ingredient_combinations(ingredients):
    """
    Create meaningful ingredient combinations using simple heuristics when AI is not available.
    
    Args:
        ingredients: List of ingredients available in inventory
        
    Returns:
        List of ingredient combination groups (lists)
    """
    # Cap the total number of combinations to avoid excessive API calls
    max_combinations = min(8, len(ingredients) // 2)
    combinations = []
    
    # Add all ingredients as a single group first (important for small inventory lists)
    if len(ingredients) <= 6:
        combinations.append(ingredients)
    else:
        # For larger lists, create smaller groupings
        # First a group with the first 5-6 ingredients
        combinations.append(ingredients[:6])
    
    # Add protein-focused combinations
    proteins = ["chicken", "beef", "pork", "fish", "tofu", "beans", "lentils", 
                "turkey", "salmon", "tuna", "shrimp", "eggs"]
    starches = ["rice", "pasta", "potato", "bread", "quinoa", "couscous", "noodle"]
    vegetables = ["tomato", "onion", "carrot", "spinach", "lettuce", "broccoli", 
                 "pepper", "cucumber", "zucchini"]
    
    # Find proteins in inventory
    for protein in proteins:
        protein_matches = [ing for ing in ingredients if protein in ing.lower()]
        if protein_matches:
            # Match protein with some starches and vegetables if available
            starch_matches = [ing for ing in ingredients if any(s in ing.lower() for s in starches)]
            veg_matches = [ing for ing in ingredients if any(v in ing.lower() for v in vegetables)]
            
            # Create protein + starch + veg combination
            combo = protein_matches[:1]
            if starch_matches:
                combo.extend(starch_matches[:1])
            if veg_matches:
                combo.extend(veg_matches[:2])
                
            if len(combo) >= 2:  # Only add if we have at least 2 ingredients
                combinations.append(combo)
    
    # Create pasta-based combinations
    pasta_matches = [ing for ing in ingredients if "pasta" in ing.lower() or "noodle" in ing.lower()]
    if pasta_matches:
        sauce_matches = [ing for ing in ingredients if any(s in ing.lower() 
                        for s in ["sauce", "tomato", "cream", "cheese"])]
        combo = pasta_matches[:1]
        if sauce_matches:
            combo.extend(sauce_matches[:2])
        if len(combo) >= 2:
            combinations.append(combo)
    
    # If we don't have enough combos yet, add some random groups
    if len(combinations) < max_combinations and len(ingredients) > 6:
        import random
        for _ in range(max_combinations - len(combinations)):
            # Get 3-5 random ingredients
            sample_size = min(random.randint(3, 5), len(ingredients))
            random_combo = random.sample(ingredients, sample_size)
            combinations.append(random_combo)
    
    # Ensure no duplicates and return
    unique_combinations = []
    seen = set()
    for combo in combinations:
        combo_key = "-".join(sorted(combo))
        if combo_key not in seen:
            seen.add(combo_key)
            unique_combinations.append(combo)
    
    return unique_combinations[:max_combinations]

def fetch_recipe_details(recipe_id):
    """
    Fetch detailed information for a single recipe from Spoonacular.
    
    Args:
        recipe_id: The ID of the recipe to fetch details for
        
    Returns:
        Dictionary with detailed recipe information
    """
    cache_key = f"spoon:recipe_details:{recipe_id}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    try:
        url = SPOONACULAR_RECIPE_INFO_URL.format(id=recipe_id)
        params = {
            "apiKey": SPOONACULAR_API_KEY,
            "includeNutrition": False
        }
        
        response = httpx.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Error fetching recipe details: {response.status_code}, {response.text}")
            return None
            
        recipe_details = response.json()
        set_cache(cache_key, recipe_details, ex=86400)  # Cache for 1 day
        return recipe_details
        
    except Exception as e:
        logger.error(f"Exception fetching recipe details: {str(e)}")
        return None

def fetch_recipe_taste_profile(recipe_id):
    """
    Fetch the taste profile for a recipe from Spoonacular.
    
    Args:
        recipe_id: The ID of the recipe to fetch taste profile for
        
    Returns:
        Dictionary with taste attributes (sweetness, saltiness, etc.)
    """
    cache_key = f"spoon:recipe_taste:{recipe_id}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    try:
        url = SPOONACULAR_TASTE_URL.format(id=recipe_id)
        params = {
            "apiKey": SPOONACULAR_API_KEY
        }
        
        response = httpx.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Error fetching recipe taste profile: {response.status_code}, {response.text}")
            return {}
            
        taste_profile = response.json()
        set_cache(cache_key, taste_profile, ex=86400)  # Cache for 1 day
        return taste_profile
        
    except Exception as e:
        logger.error(f"Exception fetching recipe taste profile: {str(e)}")
        return {}
