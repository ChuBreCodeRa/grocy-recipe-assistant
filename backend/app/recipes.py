import json
import os
import logging
import re
import httpx
from openai import OpenAI
from app.cache import get_cache, set_cache
from app.scoring import score_and_sort_recipes
from app.inventory import get_inventory_ingredient_names


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
    pattern = r"\s+-\s+\d+(?:\s*(?:oz|OZ|g|ml|ML|pack|Pack|lb|LB))?\s*$"

    # Replace the pattern with an empty string
    cleaned = re.sub(pattern, "", ingredient_name)

    return cleaned


# Add default values for tests/when env vars aren't available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy_key_for_testing")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "dummy_key_for_testing")
SPOONACULAR_API_URL = os.getenv(
    "SPOONACULAR_API_URL", "https://api.spoonacular.com/recipes/complexSearch"
)

# Only set up OpenAI client if we have a real API key
if "dummy" not in OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

INGREDIENT_CLASSIFICATION_PROMPT = """
You are a culinary assistant.
Given a recipe, classify each ingredient as:
- Essential: Defines the dish; cannot omit.
- Important: Strongly affects flavor or texture.
- Optional: Can be omitted with little impact.

Also mark whether the user has this ingredient in their inventory. You must match inventory items to recipe ingredients exactly by name or by recognizing when an inventory item contains the recipe ingredient.

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
"""

SPOONACULAR_RECIPE_INFO_URL = "https://api.spoonacular.com/recipes/{id}/information"
SPOONACULAR_TASTE_URL = "https://api.spoonacular.com/recipes/{id}/tasteWidget.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_recipes_from_spoonacular(
    ingredients, number=10, max_ready_time=None, dietary_restrictions=None
):
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
        logger.info("Using intelligent ingredient grouping for %d ingredients", len(ingredients))

        # We'll search with multiple intelligent combinations and merge unique results
        all_results = []
        results_ids = set()  # Track IDs to avoid duplicates

        # Get meaningful ingredient combinations using heuristics
        ingredient_groups = get_meaningful_ingredient_combinations(ingredients)

        # Limit to a reasonable number of groups
        max_groups = min(8, len(ingredient_groups))
        ingredient_groups = ingredient_groups[:max_groups]

        # Run searches for each group
        for group in ingredient_groups:
            logger.info("Searching Spoonacular with ingredient combination: %s", group)
            # Get cached or fetch new results for this group
            group_results = _fetch_recipes_for_ingredient_group(
                group,
                number=max(3, number // max_groups),
                max_ready_time=max_ready_time,
                dietary_restrictions=dietary_restrictions,
            )

            # Add unique results to our collection
            for recipe in group_results:
                if recipe["id"] not in results_ids:
                    all_results.append(recipe)
                    results_ids.add(recipe["id"])

            # If we have enough results already, stop making more API calls
            if len(all_results) >= number:
                break

        logger.info("Combined intelligent search found %d unique recipes", len(all_results))
        return all_results[:number]
    else:
        # For small ingredient lists (≤ 4), use the original direct method
        logger.info("Using direct Spoonacular search with %d ingredients", len(ingredients))
        return _fetch_recipes_for_ingredient_group(
            ingredients, number, max_ready_time, dietary_restrictions
        )


def _fetch_recipes_for_ingredient_group(
    ingredients, number=5, max_ready_time=None, dietary_restrictions=None
):
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
        diet_str = "_".join(
            [f"{k}:{v}" for k, v in sorted(dietary_restrictions.items())]
        )
        cache_key += f":diet{diet_str}"
    cached = get_cache(cache_key)
    if cached:
        logger.info("Using cached recipe results for %d ingredients", len(ingredients))
        return cached

    # No cache, do API call
    try:
        # Extract essential ingredient terms for better Spoonacular matching
        # This helps when dealing with very specific product names
        simplified_ingredients = []
        for ing in ingredients:
            # Extract the main part of the ingredient before any size info
            if " - " in ing:
                main_part = ing.split(" - ")[0].strip()
            else:
                main_part = ing
                
            # Clean up common packaging terms
            clean_ing = (main_part.replace("campbell's", "")
                                 .replace(" in water", "")
                                 .replace(" in vegetable oil", "")
                                 .strip())
                
            if clean_ing:
                simplified_ingredients.append(clean_ing)
        
        # Build query parameters - use a mix of exact and simplified ingredients
        # Use the original ingredients for exact matching and the simplified ones for better recall
        all_ingredients = list(set(ingredients + simplified_ingredients))
        comma_ingredients = ",".join(all_ingredients)
        
        params = {
            "apiKey": SPOONACULAR_API_KEY,
            "ingredients": comma_ingredients,
            "number": number,
            "ranking": 1,  # Changed from 2 (maximize used) to 1 (maximize used ingredients first, minimize missing ingredients second)
            "ignorePantry": False,  # count pantry items
            "fillIngredients": True,  # get detailed ingredient info
            "addRecipeInformation": True,  # get full recipe details
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
        logger.info("Calling Spoonacular API for %d ingredients", len(all_ingredients))
        response = httpx.get(SPOONACULAR_API_URL, params=params)

        # Check for errors
        if response.status_code != 200:
            logger.error(
                "Spoonacular API error: %d, %s", response.status_code, response.text
            )
            return []

        # Parse response
        data = response.json()
        results = data.get("results", [])
        logger.info("Spoonacular returned %d recipes", len(results))

        # Cache results
        if results:
            set_cache(cache_key, results, ex=3600)  # Cache for 1 hour

        return results

    except Exception as e:
        logger.error("Error fetching recipes from Spoonacular: %s", str(e))
        return []


def get_meaningful_ingredient_combinations(ingredients):
    """
    Create meaningful combinations of ingredients that could go well together in recipes.
    Uses a hybrid approach that minimizes AI usage while maintaining quality combinations.

    Args:
        ingredients: List of ingredients available in inventory

    Returns:
        List of ingredient combination groups (lists)
    """
    # Check cache first
    cache_key = f"ingredient_combinations:{','.join(sorted(ingredients))}"
    cached = get_cache(cache_key)
    if cached:
        logger.info("Using cached ingredient combinations")
        return cached

    # Try AI first if available, but with more specific culinary guidance
    if "dummy" not in OPENAI_API_KEY and client is not None:
        try:
            # Craft a more specific prompt focused on culinary knowledge and original names
            prompt = f"""You are a professional chef creating recipe ingredient combinations.
Create 4-5 realistic ingredient combinations for recipes using EXACTLY these items:
{', '.join(ingredients)}

Important guidelines:
1. Use the EXACT ingredient names provided - do not generalize or rename them
2. Group ingredients that would work well together in traditional recipes
3. Each group should form the basis of a cohesive dish that makes culinary sense
4. For prepared foods like "beef stew" or "tuna helper", consider what would complement them

Examples of good groupings with exact names:
- If given "chunk light tuna in vegetable oil", "pasta", "cheese" → keep those exact names
- If given "spaghetti & meatballs in tomato sauce", pair it with "cheese" not "side dish"

Return only a JSON array of arrays with the exact ingredient names:
[["ingredient1", "ingredient2", "ingredient3"], ["ingredient4", "ingredient5", "ingredient6"], ...]"""

            # Make the AI call with controlled temperature
            response = client.responses.create(
                model=OPENAI_MODEL, input=prompt, temperature=0.3, store=True
            )

            result_text = response.output_text
            logger.info(
                "Raw ingredient combinations response starts with: %s", result_text[:50]
            )

            # Parse the result using our standard approach
            result = None

            # First try: Direct JSON parsing
            try:
                result = json.loads(result_text.strip())
                logger.info(
                    "Standard JSON parsing successful for ingredient combinations"
                )
            except json.JSONDecodeError:
                # Direct parsing failed, try other approaches
                logger.warning("Direct JSON parsing failed, trying alternative methods")

            # Second try: Find and extract JSON array
            if result is None:
                try:
                    json_match = re.search(r"\[\s*\[.*\]\s*\]", result_text, re.DOTALL)
                    if json_match:
                        array_text = json_match.group(0)
                        result = json.loads(array_text)
                        logger.info(
                            "JSON array extraction successful for ingredient combinations"
                        )
                except Exception as e:
                    logger.warning("JSON array extraction failed: %s", e)

            # If we successfully parsed the result
            if (
                isinstance(result, list)
                and len(result) > 0
                and all(isinstance(group, list) for group in result)
            ):
                logger.info(
                    "Successfully generated %d ingredient combinations with AI",
                    len(result),
                )

                # Validate the groups
                valid_groups = []
                for group in result:
                    if isinstance(group, list) and len(group) >= 2:
                        # Ensure all items are strings and in the original ingredients list
                        valid_group = [
                            str(item) for item in group if str(item) in ingredients
                        ]
                        if len(valid_group) >= 2:
                            valid_groups.append(valid_group)

                if valid_groups:
                    # Add all ingredients as a final group to ensure thorough search
                    if len(ingredients) <= 8:
                        valid_groups.append(ingredients)
                    
                    # Cache and return
                    set_cache(cache_key, valid_groups, ex=86400)  # Cache for 1 day
                    return valid_groups
        except Exception as e:
            logger.error("Error generating AI ingredient combinations: %s", str(e))

    # Fall back to culinarily informed heuristic method
    logger.info("Using culinarily informed heuristic combinations")
    result = _create_culinary_ingredient_combinations(ingredients)
    set_cache(cache_key, result, ex=86400)  # Cache for 1 day
    return result


def _create_culinary_ingredient_combinations(ingredients):
    """
    Create meaningful ingredient combinations using culinary knowledge.
    Makes more sensible groupings than the basic heuristic approach.
    
    Args:
        ingredients: List of ingredients available in inventory
        
    Returns:
        List of culinarily sensible ingredient combinations
    """
    # Cap total combinations to avoid excessive API calls
    max_combinations = min(8, max(4, len(ingredients) // 2))
    combinations = []
    
    # Always include all ingredients as one group for small inventories
    if len(ingredients) <= 6:
        combinations.append(ingredients)
    
    # Clean and normalize ingredient names for better matching
    clean_ingredients = [ing.lower().strip() for ing in ingredients]
    
    # Define ingredient categories and common pairings
    protein_sources = ["chicken", "beef", "pork", "tuna", "fish", "tofu", "beans", "lentils", "eggs"]
    starches = ["pasta", "rice", "potato", "bread", "noodle", "macaroni", "spaghetti"]
    vegetables = ["tomato", "onion", "carrot", "broccoli", "spinach", "lettuce", "pepper", "green beans"]
    dairy = ["cheese", "milk", "cream", "yogurt", "butter"]
    condiments = ["sauce", "bbq", "gravy", "oil", "vinegar", "mayonnaise", "mustard"]
    
    # Make an ingredient type lookup for each ingredient
    ing_types = {}
    for ing in clean_ingredients:
        if any(p in ing for p in protein_sources):
            ing_types[ing] = "protein"
        elif any(s in ing for s in starches):
            ing_types[ing] = "starch"
        elif any(v in ing for v in vegetables):
            ing_types[ing] = "vegetable" 
        elif any(d in ing for d in dairy):
            ing_types[ing] = "dairy"
        elif any(c in ing for c in condiments):
            ing_types[ing] = "condiment"
        else:
            ing_types[ing] = "other"
            
    # 1. Classic pasta combinations
    pasta_items = [ing for ing in ingredients if any(s in ing.lower() for s in ["pasta", "spaghetti", "macaroni", "noodle"])]
    if pasta_items:
        pasta_combo = pasta_items[:1]  # Start with one pasta item
        
        # Look for tomato-based sauces
        tomato_items = [ing for ing in ingredients if "tomato" in ing.lower() or "sauce" in ing.lower()]
        if tomato_items:
            pasta_combo.extend(tomato_items[:1])
            
        # Add cheese if available
        cheese_items = [ing for ing in ingredients if "cheese" in ing.lower()]
        if cheese_items:
            pasta_combo.extend(cheese_items[:1])
            
        # Consider adding a protein
        protein_items = [ing for ing in ingredients if any(p in ing.lower() for p in protein_sources)]
        if protein_items and len(pasta_combo) < 4:
            pasta_combo.extend(protein_items[:1])
            
        if len(pasta_combo) >= 2:
            combinations.append(pasta_combo)
            
    # 2. Protein + Starch + Vegetable (classic meal structure)
    protein_items = [ing for ing in ingredients if any(p in ing.lower() for p in protein_sources)]
    for protein in protein_items[:2]:  # Limit to 2 protein sources to avoid too many combinations
        meal_combo = [protein]
        
        # Add a starch
        starch_items = [ing for ing in ingredients if any(s in ing.lower() for s in starches) and ing not in meal_combo]
        if starch_items:
            meal_combo.append(starch_items[0])
            
        # Add a vegetable
        veg_items = [ing for ing in ingredients if any(v in ing.lower() for v in vegetables) and ing not in meal_combo]
        if veg_items:
            meal_combo.append(veg_items[0])
            
        # Add a sauce/condiment if we have room
        if len(meal_combo) < 4:
            sauce_items = [ing for ing in ingredients if any(c in ing.lower() for c in condiments) and ing not in meal_combo]
            if sauce_items:
                meal_combo.append(sauce_items[0])
                
        if len(meal_combo) >= 2:
            combinations.append(meal_combo)
    
    # 3. Soup-based combination
    soup_items = [ing for ing in ingredients if "soup" in ing.lower()]
    if soup_items:
        soup_combo = soup_items[:1]
        
        # Add beans, vegetables, or protein to soup
        soup_additions = [
            ing for ing in ingredients 
            if any(item in ing.lower() for item in ["beans", "vegetable", "carrot", "onion", "chicken", "beef"]) 
            and ing not in soup_combo
        ]
        
        if soup_additions:
            soup_combo.extend(soup_additions[:2])
            
        if len(soup_combo) >= 2:
            combinations.append(soup_combo)
    
    # 4. Pre-made meal combinations (look for meal kits or prepared items)
    meal_kits = [
        ing for ing in ingredients 
        if any(term in ing.lower() for term in ["kit", "mix", "helper", "dinner", "meal"])
    ]
    
    for kit in meal_kits:
        kit_combo = [kit]
        
        # Look for complementary ingredients based on the kit type
        kit_lower = kit.lower()
        if "taco" in kit_lower:
            complements = [ing for ing in ingredients if any(c in ing.lower() for c in ["cheese", "salsa", "tomato", "lettuce"])]
        elif "pasta" in kit_lower or "spaghetti" in kit_lower:
            complements = [ing for ing in ingredients if any(c in ing.lower() for c in ["cheese", "tomato", "beef", "sauce"])]
        elif "rice" in kit_lower:
            complements = [ing for ing in ingredients if any(c in ing.lower() for c in ["vegetable", "chicken", "beef", "soy"])]
        elif "potato" in kit_lower:
            complements = [ing for ing in ingredients if any(c in ing.lower() for c in ["cheese", "cream", "butter", "bacon"])]
        else:
            complements = []
            
        if complements:
            kit_combo.extend(complements[:2])
            
        if len(kit_combo) >= 2:
            combinations.append(kit_combo)
    
    # 5. Ensure each ingredient appears in at least one combination
    all_included = set()
    for combo in combinations:
        all_included.update(combo)
        
    missing_ingredients = [ing for ing in ingredients if ing not in all_included]
    
    if missing_ingredients:
        # Try to create sensible combinations with missing ingredients
        for ing in missing_ingredients:
            # Find possible companions based on ingredient type
            ing_lower = ing.lower()
            if any(p in ing_lower for p in protein_sources):
                companions = [i for i in ingredients if any(s in i.lower() for s in starches + vegetables)]
            elif any(s in ing_lower for s in starches):
                companions = [i for i in ingredients if any(p in i.lower() for p in protein_sources + condiments)]
            elif any(v in ing_lower for v in vegetables):
                companions = [i for i in ingredients if i != ing]  # Most things go with vegetables
            else:
                companions = [i for i in ingredients if i != ing]
                
            if companions:
                extra_combo = [ing] + companions[:2]
                if len(extra_combo) >= 2:
                    combinations.append(extra_combo)
    
    # Remove duplicates by converting to frozen sets and back
    unique_combinations = []
    seen = set()
    for combo in combinations:
        combo_key = frozenset(combo)
        if combo_key not in seen:
            seen.add(combo_key)
            unique_combinations.append(combo)
    
    # Limit to max combinations
    return unique_combinations[:max_combinations]


def _prioritize_cooking_ingredients(ingredients, max_count=15):
    """
    Prioritize ingredients that are commonly used in cooking to reduce the complexity
    of AI prompts while maintaining quality ingredient combinations.

    Args:
        ingredients: Full list of ingredients
        max_count: Maximum number of ingredients to return

    Returns:
        Prioritized list of ingredients (limited to max_count)
    """
    # Common cooking ingredient categories with priority order
    priority_categories = [
        # Proteins (highest priority)
        [
            "chicken",
            "beef",
            "pork",
            "fish",
            "tuna",
            "shrimp",
            "tofu",
            "beans",
            "lentils",
        ],
        # Starches/Grains
        ["rice", "pasta", "potato", "bread", "noodle", "quinoa"],
        # Vegetables
        [
            "onion",
            "garlic",
            "tomato",
            "carrot",
            "broccoli",
            "spinach",
            "lettuce",
            "pepper",
        ],
        # Dairy
        ["cheese", "milk", "yogurt", "cream", "butter"],
        # Condiments/Sauces
        ["sauce", "oil", "vinegar", "mayonnaise", "mustard", "ketchup", "salsa"],
    ]

    # Score each ingredient based on its presence in priority categories
    scored_ingredients = []
    for ing in ingredients:
        ing_lower = ing.lower()

        # Start with a low base score
        score = 0

        for i, category in enumerate(priority_categories):
            category_score = 5 - i  # Highest score for first category
            if any(keyword in ing_lower for keyword in category):
                score = category_score
                break

        scored_ingredients.append((ing, score))

    # Sort by score (descending) and return limited list
    sorted_ingredients = [
        item[0] for item in sorted(scored_ingredients, key=lambda x: x[1], reverse=True)
    ]
    return sorted_ingredients[:max_count]


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
        total_ingredients = (
            recipe.get("usedIngredientCount", 0) + recipe.get("missedIngredientCount", 0)
        )
        if total_ingredients > 0:
            fit_percentage = (recipe.get("usedIngredientCount", 0) / total_ingredients) * 100
        else:
            fit_percentage = 0

        # Extract the essential info about ingredients
        used_ingredients = [
            {
                "name": ing.get("name", "unknown"),
                "amount": f"{ing.get('amount', '?')} {ing.get('unit', '')}",
            }
            for ing in recipe.get("usedIngredients", [])
        ]

        missed_ingredients = [
            {
                "name": ing.get("name", "unknown"),
                "amount": f"{ing.get('amount', '?')} {ing.get('unit', '')}",
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
                "total": total_ingredients,
            },
            "ingredients": {
                "have": used_ingredients,
                "need_to_buy": missed_ingredients,
            },
            "summary": recipe.get("summary"),
            "instructions": recipe.get("instructions"),
        }

        formatted_recipes.append(formatted_recipe)

    # Sort by fit score (highest percentage first)
    return sorted(
        formatted_recipes, key=lambda r: r["fit_score"]["percentage"], reverse=True
    )


def suggest_recipes_with_classification(
    user_preferences,
    inventory_override=None,
    use_ai_filtering=True,
    max_ingredients=20,
    max_ready_time=None,
):
    """
    Main function to suggest recipes with ingredient classification.
    Balances sophisticated AI features with reliable performance.

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
        logger.info(
            "Using inventory override with %d ingredients", len(available_ingredients)
        )
    else:
        available_ingredients = get_inventory_ingredient_names(
            use_ai_filtering=use_ai_filtering, max_ingredients=max_ingredients
        )
        logger.info("Fetched %d ingredients from inventory", len(available_ingredients))

    if not available_ingredients:
        logger.warning("No ingredients found in inventory")
        return []

    # 2. Get dietary restrictions if user has them
    dietary_restrictions = user_preferences.get("dietary_restrictions")

    # 3. Fetch recipe suggestions from Spoonacular using intelligent combinations
    recipes = fetch_recipes_from_spoonacular(
        available_ingredients,
        number=10,
        max_ready_time=max_ready_time,
        dietary_restrictions=dietary_restrictions,
    )

    # 4. If Spoonacular didn't return any recipes, fall back to AI recipe generation
    if not recipes:
        logger.warning("No recipes found from Spoonacular, trying AI fallback")
        ai_recipe = generate_ai_recipe_suggestion(
            available_ingredients, 
            user_preferences,
            max_ready_time
        )
        if ai_recipe:
            logger.info("Successfully generated an AI recipe suggestion")
            recipes = [ai_recipe]
        else:
            logger.warning("AI recipe generation failed as well")
            return []

    logger.info("Found %d recipes", len(recipes))

    # 5. Get detailed info for each recipe
    for recipe in recipes:
        # Get full recipe details if not already included and not an AI-generated recipe
        if "instructions" not in recipe and not recipe.get("ai_generated", False):
            recipe_id = recipe.get("id")
            details = fetch_recipe_details(recipe_id)
            if details:
                recipe.update(details)

        # Get taste profile if not already included and not an AI-generated recipe
        if "taste_profile" not in recipe and not recipe.get("ai_generated", False):
            recipe_id = recipe.get("id")
            taste = fetch_recipe_taste_profile(recipe_id)
            if taste:
                recipe["taste_profile"] = taste

    # 6. Extract ingredient names from each recipe
    for recipe in recipes:
        # Extract ingredient names if not already done for AI-generated recipes
        if "ingredients_list" not in recipe:
            ingredients_list = [
                ing.get("name", "").lower() for ing in recipe.get("extendedIngredients", [])
            ]
            recipe["ingredients_list"] = ingredients_list

        # Classify ingredients using the optimized AI function or smart fallback
        classified = classify_ingredients_with_ai(
            recipe, available_ingredients, recipe.get("ingredients_list", [])
        )
        recipe["classified_ingredients"] = classified

        # Convert classified ingredients to used/missed format
        recipe = convert_classified_to_used_missed(recipe, available_ingredients)

    # 7. Score and sort recipes
    scored_recipes = score_and_sort_recipes(
        recipes, available_ingredients, user_preferences
    )
    
    # 8. Check if best recipe has a very low fit score (0-10%) and generate AI recipe as alternative
    if scored_recipes and not any(r.get("ai_generated", False) for r in scored_recipes):
        best_recipe_fit = scored_recipes[0].get("fit_score", {}).get("percentage", 0)
        
        if best_recipe_fit <= 10:
            logger.warning("Best recipe has only %.1f%% fit score, generating AI alternative", best_recipe_fit)
            ai_recipe = generate_ai_recipe_suggestion(
                available_ingredients, 
                user_preferences,
                max_ready_time
            )
            
            if ai_recipe:
                # Process the AI recipe like other recipes
                ai_recipe["ingredients_list"] = [
                    ing.get("name", "").lower() for ing in ai_recipe.get("extendedIngredients", [])
                ]
                
                # Classify ingredients (will likely use fallback method)
                classified = classify_ingredients_with_ai(
                    ai_recipe, available_ingredients, ai_recipe.get("ingredients_list", [])
                )
                ai_recipe["classified_ingredients"] = classified
                
                # Convert classified ingredients to used/missed format
                ai_recipe = convert_classified_to_used_missed(ai_recipe, available_ingredients)
                
                # Prepend the AI recipe to the results
                ai_recipe_scored = score_and_sort_recipes([ai_recipe], available_ingredients, user_preferences)[0]
                scored_recipes.insert(0, ai_recipe_scored)
                logger.info("Added AI-generated recipe alternative at the top of results")

    return scored_recipes


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
            "unit": ing.get("unit", ""),
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
            "unit": details["unit"],
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
        params = {"apiKey": SPOONACULAR_API_KEY, "includeNutrition": False}

        response = httpx.get(url, params=params)

        if response.status_code != 200:
            logger.error(
                "Error fetching recipe details: %d, %s", response.status_code, response.text
            )
            return None

        recipe_details = response.json()
        set_cache(cache_key, recipe_details, ex=86400)  # Cache for 1 day
        return recipe_details

    except Exception as e:
        logger.error("Exception fetching recipe details: %s", str(e))
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
        params = {"apiKey": SPOONACULAR_API_KEY}

        response = httpx.get(url, params=params)

        if response.status_code != 200:
            logger.error(
                "Error fetching recipe taste profile: %d, %s", response.status_code, response.text
            )
            return {}

        taste_profile = response.json()
        set_cache(cache_key, taste_profile, ex=86400)  # Cache for 1 day
        return taste_profile

    except Exception as e:
        logger.error("Exception fetching recipe taste profile: %s", str(e))
        return {}


def classify_ingredients_with_ai(recipe, user_inventory, recipe_ingredients_list):
    """
    Use AI to classify recipe ingredients as Essential, Important, or Optional.
    Optimized for more reliable JSON parsing while maintaining the core functionality.

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
        logger.info("Using cached ingredient classification for recipe %d", recipe_id)
        return cached

    # If we don't have OpenAI access, fall back to simple classification
    if "dummy" in OPENAI_API_KEY or client is None:
        logger.warning(
            "No valid OpenAI API key - using simple classification for recipe %d",
            recipe_id,
        )
        return _create_simple_ingredient_classification(
            recipe_ingredients_list, user_inventory
        )

    try:
        # Format the recipe details for the prompt
        recipe_name = recipe.get("title", "Unknown Recipe")
        instructions = recipe.get("instructions", "Not available")
        ingredients_text = ", ".join(recipe_ingredients_list)
        inventory_text = ", ".join(user_inventory)

        # Prepare the prompt with the EXACT template from documentation for consistency
        # Add an extra instruction to ensure proper JSON formatting
        prompt = INGREDIENT_CLASSIFICATION_PROMPT.format(
            recipe_name=recipe_name,
            instructions=instructions,
            ingredients_list=ingredients_text,
            user_inventory_list=inventory_text,
        )
        prompt += "\n\nIMPORTANT: Your response must be valid JSON starting with '[' and contain no additional text before or after the JSON array."

        # Make the AI call
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            temperature=0.2,  # Lower temperature for more consistent formatting
            store=True,
        )

        result_text = response.output_text
        logger.info("Raw classification response starts with: %s", result_text[:50])

        # TEMPORARY SOLUTION: If we're getting this specific error pattern, use fallback
        if '\n    "ingredient"' in result_text or result_text.strip().startswith(
            '"ingredient"'
        ):
            logger.warning(
                "Detected problematic AI response format, using fallback for recipe %d",
                recipe_id,
            )
            return _create_simple_ingredient_classification(
                recipe_ingredients_list, user_inventory
            )

        # Enhanced JSON parsing with multiple fallback approaches
        result = None

        # First try: Direct JSON parsing with whitespace cleanup
        try:
            cleaned_text = result_text.strip()
            result = json.loads(cleaned_text)
            logger.info("Successfully parsed JSON directly for recipe %d", recipe_id)
        except json.JSONDecodeError:
            # Direct parsing failed, try alternative approaches
            pass

        # Second try: Extract JSON array if it's embedded in text
        if result is None:
            try:
                array_match = re.search(r"\[\s*\{.*\}\s*\]", result_text, re.DOTALL)
                if array_match:
                    array_text = array_match.group(0)
                    result = json.loads(array_text)
                    logger.info(
                        "Successfully extracted JSON array for recipe %d", recipe_id
                    )
            except Exception as e:
                logger.warning("JSON array extraction failed: %s", e)

        # If we successfully parsed the JSON and it's a valid list
        if isinstance(result, list):
            # Process valid items
            valid_items = []
            for item in result:
                if isinstance(item, dict) and "ingredient" in item:
                    valid_item = {
                        "ingredient": str(item.get("ingredient", "")),
                        "category": str(item.get("category", "Optional")),
                        "in_inventory": bool(item.get("in_inventory", False)),
                        "confidence": float(item.get("confidence", 0.5)),
                    }
                    valid_items.append(valid_item)

            # Cache and return valid results
            if valid_items:
                logger.info(
                    "Successfully classified %d ingredients for recipe %d",
                    len(valid_items),
                    recipe_id,
                )
                set_cache(cache_key, valid_items, ex=86400)  # Cache for 1 day
                return valid_items

        # If all parsing attempts failed, use the fallback
        logger.warning(
            "Failed to parse AI classification response for recipe %d, using fallback",
            recipe_id,
        )
        return _create_simple_ingredient_classification(
            recipe_ingredients_list, user_inventory
        )

    except Exception as e:
        logger.error(
            "Error classifying ingredients with AI for recipe %d: %s", recipe_id, str(e)
        )
        return _create_simple_ingredient_classification(
            recipe_ingredients_list, user_inventory
        )


def _create_simple_ingredient_classification(ingredient_list, user_inventory):
    """
    Create a simple but improved ingredient classification without AI.
    Uses enhanced fuzzy matching to find ingredients in inventory.

    Args:
        ingredient_list: List of ingredient names from the recipe
        user_inventory: List of ingredients available in user's inventory

    Returns:
        List of classification dictionaries
    """
    # Handle empty cases gracefully
    if not ingredient_list:
        return []
    
    # Log that we're using the fallback method
    logger.info("Using fallback ingredient classification method for %d ingredients", len(ingredient_list))
    
    classifications = []

    # Simple heuristic - first 1/3 are Essential, next 1/3 are Important, rest Optional
    total = len(ingredient_list)
    essential_count = max(1, total // 3)
    important_count = max(1, total // 3)

    # Clean up ingredients for better matching
    clean_recipe_ingredients = [
        ingredient.lower().strip() for ingredient in ingredient_list
    ]
    
    # First create simplified versions of inventory items to improve matching
    clean_inventory = []
    simplified_inventory = []
    
    for item in user_inventory:
        # Clean the original item
        clean_item = item.lower().strip()
        clean_inventory.append(clean_item)
        
        # Create simplified version for better matching
        simplified = clean_item
        
        # Remove packaging and brand details for matching
        if " - " in simplified:
            simplified = simplified.split(" - ")[0].strip()
            
        simplified = (simplified.replace("campbell's", "")
                             .replace(" in water", "")
                             .replace(" in vegetable oil", "")
                             .replace(" in tomato & meat sauce", "")
                             .replace(" in tomato sauce", "")
                             .strip())
                             
        if simplified and simplified not in simplified_inventory:
            simplified_inventory.append(simplified)

    # Common ingredient words to ignore when matching (articles, measurements, etc.)
    common_words = {
        "fresh", "dried", "frozen", "canned", "sliced", "diced", "chopped",
        "minced", "ground", "whole", "the", "and", "or", "with", "without",
        "of", "a", "an", "cup", "tablespoon", "teaspoon"
    }

    # Set up keywords for the core ingredients to help with matching
    core_ingredients = {
        "tuna": ["tuna", "chunk light", "albacore"],
        "beef": ["beef", "steak", "stew", "ground beef"],
        "chicken": ["chicken", "poultry"],
        "pasta": ["pasta", "spaghetti", "macaroni", "noodle", "ravioli", "shells"],
        "tomato": ["tomato", "tomatoes", "tomato sauce"],
        "cheese": ["cheese", "cheddar", "mozzarella", "parmesan"],
        "beans": ["beans", "green beans", "kidney beans"],
        "soup": ["soup", "stew", "chowder"],
        "gravy": ["gravy", "sauce"]
    }

    for i, ingredient in enumerate(clean_recipe_ingredients):
        # Default assumption: ingredient not in inventory
        in_inventory = False
        matched_item = None

        # 1. Try exact match with original and simplified inventory
        for inv_item in clean_inventory + simplified_inventory:
            if inv_item == ingredient:
                in_inventory = True
                matched_item = inv_item
                break

        # 2. Try substring match if no exact match
        if not in_inventory:
            for inv_item in clean_inventory:
                if (inv_item in ingredient or ingredient in inv_item):
                    in_inventory = True
                    matched_item = inv_item
                    break
                    
            # Try with simplified inventory too
            if not in_inventory:
                for inv_item in simplified_inventory:
                    if (inv_item in ingredient or ingredient in inv_item):
                        in_inventory = True
                        matched_item = inv_item
                        break

        # 3. Try core ingredient matching if still no match
        if not in_inventory:
            ingredient_words = set(ingredient.split())
            
            # Find relevant core ingredients in this ingredient
            relevant_cores = []
            for core, keywords in core_ingredients.items():
                if any(keyword in ingredient for keyword in keywords):
                    relevant_cores.append(core)
            
            # Check if we have any of these core ingredients in inventory
            if relevant_cores:
                for core in relevant_cores:
                    keywords = core_ingredients[core]
                    for inv_item in clean_inventory + simplified_inventory:
                        if any(keyword in inv_item for keyword in keywords):
                            in_inventory = True
                            matched_item = inv_item
                            break
                    if in_inventory:
                        break

        # Set category based on position in the list
        if i < essential_count:
            category = "Essential"
            confidence = 0.8
        elif i < essential_count + important_count:
            category = "Important"
            confidence = 0.7
        else:
            category = "Optional"
            confidence = 0.6
            
        # Log match for debugging
        if in_inventory:
            logger.debug("Matched recipe ingredient '%s' to inventory item '%s'", 
                        ingredient, matched_item)

        classifications.append({
            "ingredient": ingredient_list[i],  # Use original name for consistency
            "category": category,
            "in_inventory": in_inventory,
            "confidence": confidence
        })

    return classifications


def generate_ai_recipe_suggestion(available_ingredients, user_preferences, max_ready_time=None):
    """
    Generate a custom recipe suggestion using AI when Spoonacular doesn't return results.
    
    Args:
        available_ingredients: List of ingredients available in user's inventory
        user_preferences: User's preference dictionary (including dietary restrictions)
        max_ready_time: Maximum preparation time in minutes (optional)
        
    Returns:
        A recipe dictionary with AI-generated content or None if generation fails
    """
    # Skip if we don't have valid OpenAI credentials
    if "dummy" in OPENAI_API_KEY or client is None:
        logger.warning("No valid OpenAI API key - cannot generate AI recipe")
        return None
        
    # Create a cache key based on ingredients and preferences
    dietary_restrictions = user_preferences.get("dietary_restrictions", {})
    diet_str = ""
    if dietary_restrictions:
        diet_parts = []
        if "diet" in dietary_restrictions:
            diet_parts.append(f"diet:{dietary_restrictions['diet']}")
        if "intolerances" in dietary_restrictions and dietary_restrictions["intolerances"]:
            diet_parts.append(f"int:{','.join(sorted(dietary_restrictions['intolerances']))}")
        diet_str = "_".join(diet_parts)
    
    # Create cache key
    cache_key = f"ai:recipe:{','.join(sorted(available_ingredients))}"
    if max_ready_time:
        cache_key += f":time{max_ready_time}"
    if diet_str:
        cache_key += f":diet{diet_str}"
    
    # Check cache first
    cached = get_cache(cache_key)
    if cached:
        logger.info("Using cached AI recipe suggestion")
        return cached
    
    try:
        # Prepare dietary restriction string for the prompt
        diet_instructions = ""
        if "diet" in dietary_restrictions:
            diet_instructions += f"This recipe must be {dietary_restrictions['diet']}. "
        if "intolerances" in dietary_restrictions and dietary_restrictions["intolerances"]:
            intolerances = ", ".join(dietary_restrictions["intolerances"])
            diet_instructions += f"The recipe must avoid these allergens/intolerances: {intolerances}. "
            
        # Add time constraint if specified
        time_constraint = ""
        if max_ready_time:
            time_constraint = f"The recipe should take no more than {max_ready_time} minutes to prepare. "
        
        # Generate a unique ID using timestamp to avoid collisions
        import time
        unique_id = f"{int(time.time())}-{hash(str(available_ingredients)) % 10000}"
        
        # Craft the prompt for recipe generation with more explicit JSON formatting instructions
        prompt = f"""You are a creative chef. Create a recipe using only ingredients from this inventory list.
        
Available ingredients: {', '.join(available_ingredients)}

{diet_instructions}
{time_constraint}
Your recipe must:
1. Only use ingredients from the available list (plus basic salt, pepper, water)
2. Include a title, cooking time, servings, ingredient list with amounts, and step-by-step instructions
3. Be practical and reasonable to make at home
4. Maximize the use of available ingredients

Return your recipe in this JSON format EXACTLY as shown, with proper JSON syntax:
{{
  "id": "ai-recipe-{unique_id}",
  "title": "Recipe Name",
  "readyInMinutes": 30,
  "servings": 4,
  "image": null,
  "summary": "Brief description of the recipe",
  "extendedIngredients": [
    {{ "name": "ingredient1", "amount": 1, "unit": "cup" }},
    {{ "name": "ingredient2", "amount": 2, "unit": "tablespoon" }}
  ],
  "instructions": "Step-by-step cooking instructions",
  "ai_generated": true
}}

IMPORTANT: Ensure your JSON is valid with proper commas between all objects in arrays and double quotes around all string values."""

        # Make the AI call
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            temperature=0.7,  # Higher temperature for creativity
            store=True
        )
        
        result_text = response.output_text
        logger.info("Raw AI recipe response starts with: %s", result_text[:50])
        
        # Parse the result with enhanced error handling
        try:
            # First try to extract JSON if it's embedded in markdown or other text
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                json_text = json_match.group(0)
                
                # Try to clean up common JSON formatting issues before parsing
                # Fix missing commas after closing braces in arrays
                json_text = re.sub(r'(\})\s*(\{)', r'\1,\2', json_text)
                # Fix missing commas after quotes in arrays
                json_text = re.sub(r'("\s*)\n\s*(\{)', r'\1,\2', json_text)
                # Fix missing commas between array items
                json_text = re.sub(r'("\s*)\n\s*(")', r'\1,\2', json_text)
                
                try:
                    recipe = json.loads(json_text)
                    
                    # Validate the recipe has the minimum required fields
                    required_fields = ["id", "title", "readyInMinutes", "servings", "extendedIngredients", "instructions"]
                    if all(field in recipe for field in required_fields):
                        # Ensure the recipe has the ai_generated flag
                        recipe["ai_generated"] = True
                        
                        # Create ingredients_list for consistency with Spoonacular recipes
                        recipe["ingredients_list"] = [
                            ing.get("name", "").lower() for ing in recipe.get("extendedIngredients", [])
                        ]
                        
                        # Add a default taste profile since we can't get one from Spoonacular
                        # This helps with scoring consistency
                        recipe["taste_profile"] = {
                            "sweetness": 50,
                            "saltiness": 50,
                            "sourness": 50,
                            "bitterness": 50,
                            "savoriness": 50,
                            "fattiness": 50
                        }
                        
                        # Ensure fit score is set to higher value than Spoonacular
                        recipe["usedIngredientCount"] = len(recipe.get("extendedIngredients", []))
                        recipe["missedIngredientCount"] = 0
                        
                        # Cache the recipe
                        set_cache(cache_key, recipe, ex=86400)  # Cache for 1 day
                        return recipe
                except json.JSONDecodeError as json_err:
                    logger.error(f"JSON parsing error details: {str(json_err)}")
                    logger.error(f"Problematic JSON: {json_text[:100]}...")
                    
                    # As a last resort, try to manually construct a recipe
                    if "title" in json_text and "instructions" in json_text:
                        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', json_text)
                        instructions_match = re.search(r'"instructions"\s*:\s*"([^"]+)"', json_text)
                        
                        if title_match and instructions_match:
                            # Create a manually constructed recipe
                            manual_recipe = {
                                "id": f"ai-recipe-{unique_id}",
                                "title": title_match.group(1),
                                "readyInMinutes": 30,
                                "servings": 4,
                                "instructions": instructions_match.group(1),
                                "extendedIngredients": [
                                    {"name": ingredient, "amount": 1, "unit": "serving"}
                                    for ingredient in available_ingredients[:5]
                                ],
                                "ai_generated": True,
                                "summary": f"Recipe made with {', '.join(available_ingredients[:3])}",
                                "taste_profile": {
                                    "sweetness": 50,
                                    "saltiness": 50,
                                    "sourness": 50,
                                    "bitterness": 50,
                                    "savoriness": 50,
                                    "fattiness": 50
                                }
                            }
                            
                            manual_recipe["ingredients_list"] = [
                                ing.get("name", "").lower() for ing in manual_recipe.get("extendedIngredients", [])
                            ]
                            
                            logger.info("Created manual recipe as fallback")
                            set_cache(cache_key, manual_recipe, ex=86400)  # Cache for 1 day
                            return manual_recipe
        except Exception as e:
            logger.error("Error parsing AI recipe response: %s", str(e))
    
    except Exception as e:
        logger.error("Error generating AI recipe: %s", str(e))
    
    return None
