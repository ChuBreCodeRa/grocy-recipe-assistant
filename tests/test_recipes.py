import pytest
from app.recipes import clean_ingredient_name

def test_clean_ingredient_name_with_oz():
    assert clean_ingredient_name("Beef Stew - 20oz") == "Beef Stew"
    assert clean_ingredient_name("beef stew - 15OZ") == "beef stew" # Case insensitive

def test_clean_ingredient_name_with_g():
    # Use the updated name format from Grocy
    assert clean_ingredient_name("Sweet Baby Rays bbq Sauce - 510g") == "Sweet Baby Rays bbq Sauce"

def test_clean_ingredient_name_with_pack():
    assert clean_ingredient_name("Spaghetti and Meatballs - 4 Pack") == "Spaghetti and Meatballs"
    assert clean_ingredient_name("Mini beef ravioli - 4 pack") == "Mini beef ravioli" # Case insensitive

def test_clean_ingredient_name_with_number_only():
    assert clean_ingredient_name("Some Item - 10") == "Some Item"

def test_clean_ingredient_name_no_size():
    assert clean_ingredient_name("Tuna in water") == "Tuna in water"
    assert clean_ingredient_name("Cut Green Beans") == "Cut Green Beans"

def test_clean_ingredient_name_hyphen_in_name():
    # Ensure hyphens in the actual name aren't removed
    assert clean_ingredient_name("Ready-to-eat Soup - 12oz") == "Ready-to-eat Soup"
    assert clean_ingredient_name("Ready-to-eat Soup") == "Ready-to-eat Soup"

def test_clean_ingredient_name_empty_string():
    assert clean_ingredient_name("") == ""

def test_clean_ingredient_name_just_size():
    # Unlikely case, but test robustness
    assert clean_ingredient_name(" - 10oz") == ""
    assert clean_ingredient_name(" - 5 Pack") == ""

def test_format_recipe_output():
    from app.recipes import format_recipe_output
    
    # Sample recipe data similar to what Spoonacular would return
    test_recipes = [
        {
            "id": 123456,
            "title": "Test Recipe",
            "image": "http://example.com/image.jpg",
            "readyInMinutes": 25,
            "servings": 4,
            "sourceUrl": "http://example.com/recipe",
            "usedIngredientCount": 2,
            "missedIngredientCount": 3,
            "usedIngredients": [
                {"name": "pasta", "amount": 8.0, "unit": "oz"},
                {"name": "tomato sauce", "amount": 0.5, "unit": "cup"}
            ],
            "missedIngredients": [
                {"name": "basil", "amount": 2.0, "unit": "tbsp"},
                {"name": "garlic", "amount": 3.0, "unit": "cloves"},
                {"name": "parmesan", "amount": 0.25, "unit": "cup"}
            ],
            "summary": "A test recipe summary",
            "instructions": "Test recipe instructions"
        },
        {
            "id": 789012,
            "title": "Better Match Recipe",
            "image": "http://example.com/image2.jpg",
            "readyInMinutes": 15,
            "servings": 2,
            "sourceUrl": "http://example.com/recipe2",
            "usedIngredientCount": 3,
            "missedIngredientCount": 1,
            "usedIngredients": [
                {"name": "chicken", "amount": 12.0, "unit": "oz"},
                {"name": "rice", "amount": 1.0, "unit": "cup"},
                {"name": "soy sauce", "amount": 2.0, "unit": "tbsp"}
            ],
            "missedIngredients": [
                {"name": "green onion", "amount": 2.0, "unit": ""}
            ],
            "summary": "Another test recipe summary",
            "instructions": "Another test recipe instructions"
        }
    ]
    
    # Call the function with our test data
    formatted_recipes = format_recipe_output(test_recipes)
    
    # Assert the formatting was done correctly
    assert len(formatted_recipes) == 2
    
    # Recipes should be sorted by fit score (highest percentage first)
    # First recipe should be "Better Match Recipe" with 75% fit
    assert formatted_recipes[0]["title"] == "Better Match Recipe"
    assert formatted_recipes[0]["fit_score"]["percentage"] == 75.0
    assert formatted_recipes[0]["fit_score"]["have"] == 3
    assert formatted_recipes[0]["fit_score"]["need_to_buy"] == 1
    assert formatted_recipes[0]["fit_score"]["total"] == 4
    
    # Second recipe should be "Test Recipe" with 40% fit
    assert formatted_recipes[1]["title"] == "Test Recipe"
    assert formatted_recipes[1]["fit_score"]["percentage"] == 40.0
    assert formatted_recipes[1]["fit_score"]["have"] == 2
    assert formatted_recipes[1]["fit_score"]["need_to_buy"] == 3
    assert formatted_recipes[1]["fit_score"]["total"] == 5
    
    # Check the structure of the ingredients
    assert "have" in formatted_recipes[0]["ingredients"]
    assert "need_to_buy" in formatted_recipes[0]["ingredients"]
    assert len(formatted_recipes[0]["ingredients"]["have"]) == 3
    assert len(formatted_recipes[0]["ingredients"]["need_to_buy"]) == 1

def test_format_recipe_output_empty_list():
    from app.recipes import format_recipe_output
    
    # Test with empty list
    formatted_recipes = format_recipe_output([])
    
    # Should return empty list
    assert formatted_recipes == []
    
def test_format_recipe_output_missing_fields():
    from app.recipes import format_recipe_output
    
    # Test with recipe missing some fields
    test_recipe = [
        {
            "id": 123456,
            "title": "Incomplete Recipe",
            "usedIngredientCount": 1,
            # Missing other fields
        }
    ]
    
    formatted_recipes = format_recipe_output(test_recipe)
    
    # Should handle missing fields gracefully
    assert len(formatted_recipes) == 1
    assert formatted_recipes[0]["title"] == "Incomplete Recipe"
    assert formatted_recipes[0]["fit_score"]["have"] == 1
    assert "image" in formatted_recipes[0]  # Field should exist even if None
    assert "instructions" in formatted_recipes[0]

def test_heuristic_ingredient_combinations():
    from app.recipes import _create_heuristic_ingredient_combinations
    
    # Test with a mix of ingredient types
    test_ingredients = [
        "chicken breast",
        "pasta",
        "tomato sauce",
        "rice",
        "beef stew",
        "garlic",
        "cheese"
    ]
    
    combinations = _create_heuristic_ingredient_combinations(test_ingredients)
    
    # Verify we get reasonable combinations back
    assert isinstance(combinations, list)
    assert len(combinations) > 0
    
    # Check that our combinations are lists of ingredients
    for combo in combinations:
        assert isinstance(combo, list)
        # Each combination should contain at least one ingredient
        assert len(combo) > 0
        # Each combination should contain only ingredients from our input list
        for ingredient in combo:
            assert ingredient in test_ingredients

def test_heuristic_ingredient_combinations_small_list():
    from app.recipes import _create_heuristic_ingredient_combinations
    
    # Test with just a few ingredients
    test_ingredients = ["pasta", "cheese"]
    
    combinations = _create_heuristic_ingredient_combinations(test_ingredients)
    
    # Should still get some combinations back
    assert isinstance(combinations, list)
    assert len(combinations) > 0
    
    # With a small list, we expect to see the pair as a combination
    assert ["pasta", "cheese"] in combinations

def test_get_meaningful_ingredient_combinations_with_cache():
    import pytest
    from unittest.mock import patch
    from app.recipes import get_meaningful_ingredient_combinations
    
    # Mock the cache to return a predefined result
    test_combinations = [["pasta", "tomato sauce", "cheese"], ["chicken", "rice", "garlic"]]
    
    with patch('app.recipes.get_cache', return_value=test_combinations):
        result = get_meaningful_ingredient_combinations(["pasta", "tomato sauce", "cheese", "chicken", "rice", "garlic"])
    
    # Should return the cached combinations
    assert result == test_combinations

def test_get_meaningful_ingredient_combinations_fallback():
    import pytest
    from unittest.mock import patch
    from app.recipes import get_meaningful_ingredient_combinations, _create_heuristic_ingredient_combinations
    
    # Ensure we don't have a real OpenAI client for this test
    test_ingredients = ["pasta", "cheese", "chicken"]
    
    # Create a dummy result that heuristic combinations would return
    heuristic_result = [["pasta", "cheese"], ["chicken"]]
    
    # Mock the functions to ensure we use the fallback
    with patch('app.recipes.client', None):
        # Also mock the heuristic function to verify it gets called
        with patch('app.recipes._create_heuristic_ingredient_combinations', return_value=heuristic_result):
            result = get_meaningful_ingredient_combinations(test_ingredients)
    
    # Should return the result from the heuristic fallback
    assert result == heuristic_result

def test_api_suggest_recipes_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    from unittest.mock import patch
    import json
    
    client = TestClient(app)
    
    # Create mock data for our test
    mock_recipe_data = [
        {
            "id": 123456,
            "title": "Test Recipe",
            "image": "http://example.com/image.jpg",
            "readyInMinutes": 25,
            "servings": 4,
            "sourceUrl": "http://example.com/recipe",
            "usedIngredientCount": 2,
            "missedIngredientCount": 3,
            "usedIngredients": [
                {"name": "pasta", "amount": 8.0, "unit": "oz"},
                {"name": "tomato sauce", "amount": 0.5, "unit": "cup"}
            ],
            "missedIngredients": [
                {"name": "basil", "amount": 2.0, "unit": "tbsp"},
                {"name": "garlic", "amount": 3.0, "unit": "cloves"},
                {"name": "parmesan", "amount": 0.25, "unit": "cup"}
            ],
            "summary": "A test recipe summary",
            "instructions": "Test recipe instructions"
        }
    ]
    
    # Mock the suggest_recipes_with_classification function
    with patch('app.main.suggest_recipes_with_classification', return_value=mock_recipe_data):
        # Test the endpoint with normal output format
        response = client.post("/ai/suggest-recipes", json={"user_id": "testuser"})
        
        # Check the response
        assert response.status_code == 200
        
        # Parse the response data
        data = response.json()
        
        # Verify the output is formatted as expected
        assert len(data) == 1
        assert "fit_score" in data[0]
        assert "ingredients" in data[0]
        assert "have" in data[0]["ingredients"]
        assert "need_to_buy" in data[0]["ingredients"]
        
        # Verify specific fields in the formatted output
        assert data[0]["id"] == 123456
        assert data[0]["fit_score"]["have"] == 2
        assert data[0]["fit_score"]["need_to_buy"] == 3
        assert data[0]["fit_score"]["percentage"] == 40.0
        
        # Test with simplified=true parameter
        response_simple = client.post("/ai/suggest-recipes", json={"user_id": "testuser", "simplified": True})
        
        # Check the response
        assert response_simple.status_code == 200
        
        # Parse the response data
        simple_data = response_simple.json()
        
        # Verify the output is simplified as expected
        assert len(simple_data) == 1
        assert "fit_score" in simple_data[0]
        assert "ingredients" not in simple_data[0]
        assert "instructions" not in simple_data[0]
        assert "summary" not in simple_data[0]
        
        # Essential fields should still be present
        assert simple_data[0]["id"] == 123456
        assert simple_data[0]["title"] == "Test Recipe"
        assert simple_data[0]["fit_score"]["percentage"] == 40.0

def test_suggest_recipes_with_classification():
    import pytest
    from unittest.mock import patch, MagicMock, call
    from app.recipes import suggest_recipes_with_classification

    # --- Mock Data ---
    test_user_preferences = {
        "taste_profile": {"sweetness": 30, "saltiness": 60, "sourness": 20, "bitterness": 10, "savoriness": 70, "fattiness": 50},
        "effort_tolerance": "easy",
        "dietary_restrictions": {"diet": "none", "intolerances": []}
    }
    test_available_ingredients = ["chicken", "rice", "garlic", "onion", "soy sauce"]
    test_recipes = [
        {
            "id": 123, "title": "Simple Chicken and Rice", "readyInMinutes": 30,
            "extendedIngredients": [
                {"name": "chicken", "amount": 1, "unit": "lb"}, {"name": "rice", "amount": 1, "unit": "cup"},
                {"name": "garlic", "amount": 2, "unit": "cloves"}, {"name": "soy sauce", "amount": 2, "unit": "tbsp"},
                {"name": "sesame oil", "amount": 1, "unit": "tbsp"}
            ]
        },
        {
            "id": 456, "title": "Complex Dish", "readyInMinutes": 75,
            "extendedIngredients": [
                {"name": "chicken", "amount": 1, "unit": "lb"}, {"name": "truffle oil", "amount": 1, "unit": "tbsp"},
                {"name": "saffron", "amount": 1, "unit": "pinch"}
            ]
        }
    ]
    test_taste_profiles = {
        123: {"sweetness": 20, "saltiness": 60, "sourness": 10, "bitterness": 5, "savoriness": 80, "fattiness": 50},
        456: {"sweetness": 10, "saltiness": 30, "sourness": 5, "bitterness": 20, "savoriness": 60, "fattiness": 70}
    }
    # Base classifications (used by initial run and as template for override)
    test_classified_ingredients = {
        123: [
            {"ingredient": "chicken", "category": "Essential", "in_inventory": True, "confidence": 0.9},
            {"ingredient": "rice", "category": "Essential", "in_inventory": True, "confidence": 0.9},
            {"ingredient": "garlic", "category": "Important", "in_inventory": True, "confidence": 0.8},
            {"ingredient": "soy sauce", "category": "Important", "in_inventory": True, "confidence": 0.8},
            {"ingredient": "sesame oil", "category": "Optional", "in_inventory": False, "confidence": 0.7}
        ],
        456: [
            {"ingredient": "chicken", "category": "Essential", "in_inventory": True, "confidence": 0.9},
            {"ingredient": "truffle oil", "category": "Essential", "in_inventory": False, "confidence": 0.9},
            {"ingredient": "saffron", "category": "Important", "in_inventory": False, "confidence": 0.8}
        ]
    }

    # --- Mock Logic Definitions ---
    def mock_details(recipe_id):
        if recipe_id == 123:
            return {"id": 123, "title": "Simple Chicken and Rice", "instructions": "Mock instructions 123", "extendedIngredients": test_recipes[0]["extendedIngredients"]}
        elif recipe_id == 456:
            return {"id": 456, "title": "Complex Dish", "instructions": "Mock instructions 456", "extendedIngredients": test_recipes[1]["extendedIngredients"]}
        return None

    def mock_convert_logic(recipe, available_ingredients):
        recipe_id = recipe.get("id")
        # Use classification attached to recipe by mock_classify, fallback to base for safety
        classified = recipe.get("classified_ingredients", test_classified_ingredients.get(recipe_id, []))
        
        # Recalculate in_inventory based on the *current* available_ingredients
        recalculated_classified = []
        for ing_data in classified:
            ingredient_name = ing_data.get("ingredient", "").lower()
            in_inventory_now = any(avail_ing.lower() == ingredient_name for avail_ing in available_ingredients)
            recalculated_classified.append({**ing_data, "in_inventory": in_inventory_now})

        # Update recipe in place
        recipe["usedIngredientCount"] = sum(1 for ing in recalculated_classified if ing["in_inventory"])
        recipe["missedIngredientCount"] = len(recalculated_classified) - recipe["usedIngredientCount"]
        recipe["usedIngredients"] = [{"name": i["ingredient"], "amount": 1, "unit": ""} for i in recalculated_classified if i["in_inventory"]]
        recipe["missedIngredients"] = [{"name": i["ingredient"], "amount": 1, "unit": ""} for i in recalculated_classified if not i["in_inventory"]]
        recipe["classified_ingredients"] = recalculated_classified # Ensure updated classification is on the object
        return recipe

    def mock_score_logic(recipes, *args):
        for recipe in recipes:
            recipe["score"] = recipe.get("usedIngredientCount", 0) * 10
        return sorted(recipes, key=lambda r: r.get("score", 0), reverse=True)

    # --- Outer Patches (Active for both runs) ---
    with patch('app.recipes.fetch_recipes_from_spoonacular', return_value=test_recipes), \
         patch('app.recipes.fetch_recipe_details', side_effect=mock_details), \
         patch('app.recipes.fetch_recipe_taste_profile', side_effect=lambda id: test_taste_profiles.get(id)), \
         patch('app.recipes.convert_classified_to_used_missed', side_effect=mock_convert_logic), \
         patch('app.recipes.score_and_sort_recipes', side_effect=mock_score_logic):

        # --- Test Initial Run ---
        # Mock inventory and AI classification specifically for this run
        with patch('app.recipes.get_inventory_ingredient_names', return_value=test_available_ingredients) as mock_get_inv, \
             patch('app.recipes.classify_ingredients_with_ai') as mock_classify_initial:
            
            # Define side effect for classify_ingredients_with_ai for the initial run
            def classify_initial_run(recipe, user_inv, recipe_ing):
                recipe_id = recipe.get("id")
                classification = test_classified_ingredients.get(recipe_id)
                # Attach classification to recipe object for mock_convert_logic
                recipe["classified_ingredients"] = classification 
                return classification
            mock_classify_initial.side_effect = classify_initial_run

            result = suggest_recipes_with_classification(test_user_preferences)

            # Assertions for initial run
            mock_get_inv.assert_called_once() # Ensure inventory was fetched
            assert mock_classify_initial.call_count == len(test_recipes) # Ensure classify was called for each recipe
            # Check inventory passed to classify_ingredients_with_ai
            first_call_args, _ = mock_classify_initial.call_args_list[0]
            assert first_call_args[1] == test_available_ingredients 

            assert len(result) == 2
            assert result[0]["id"] == 123, "Initial run: Recipe 123 should be first"
            assert result[0]["title"] == "Simple Chicken and Rice"
            assert result[0]["score"] == 40, f"Initial run score mismatch: {result[0].get('score')}"
            assert result[0]["usedIngredientCount"] == 4, f"Initial run used count mismatch: {result[0].get('usedIngredientCount')}"
            assert result[0]["missedIngredientCount"] == 1
            assert result[1]["id"] == 456, "Initial run: Recipe 456 should be second"
            assert result[1]["score"] == 10
            assert result[1]["usedIngredientCount"] == 1
            assert result[1]["missedIngredientCount"] == 2

        # --- Test Override Run ---
        override_ingredients = ["chicken", "truffle oil"]
        # Mock AI classification specifically for the override run
        with patch('app.recipes.classify_ingredients_with_ai') as mock_classify_override:
            
            # Define side effect for classify_ingredients_with_ai for the override run
            def classify_override_run(recipe, user_inv, recipe_ing):
                recipe_id = recipe.get("id")
                base_classification = test_classified_ingredients.get(recipe_id, [])
                # Generate classification based on override_ingredients (user_inv)
                override_classification = [
                    {**ing, "in_inventory": ing["ingredient"].lower() in user_inv}
                    for ing in base_classification
                ]
                # Attach classification to recipe object for mock_convert_logic
                recipe["classified_ingredients"] = override_classification
                return override_classification
            mock_classify_override.side_effect = classify_override_run

            # Note: get_inventory_ingredient_names is NOT called when inventory_override is provided
            result_with_override = suggest_recipes_with_classification(
                test_user_preferences,
                inventory_override=override_ingredients
            )

            # Assertions for override run
            assert mock_classify_override.call_count == len(test_recipes) # Ensure classify was called
            # Check inventory passed to classify_ingredients_with_ai
            first_call_args_override, _ = mock_classify_override.call_args_list[0]
            assert first_call_args_override[1] == override_ingredients, "Override inventory not passed to classify"

            assert len(result_with_override) == 2
            assert result_with_override[0]["id"] == 456, "Override run: Recipe 456 should be first"
            assert result_with_override[0]["score"] == 20, f"Override run score mismatch (456): {result_with_override[0].get('score')}" # chicken, truffle oil
            assert result_with_override[0]["usedIngredientCount"] == 2, f"Override run used count mismatch (456): {result_with_override[0].get('usedIngredientCount')}"
            assert result_with_override[0]["missedIngredientCount"] == 1 # saffron
            assert result_with_override[1]["id"] == 123, "Override run: Recipe 123 should be second"
            assert result_with_override[1]["score"] == 10, f"Override run score mismatch (123): {result_with_override[1].get('score')}" # just chicken
            assert result_with_override[1]["usedIngredientCount"] == 1, f"Override run used count mismatch (123): {result_with_override[1].get('usedIngredientCount')}"
            assert result_with_override[1]["missedIngredientCount"] == 4

    # --- Test Edge Case: No Inventory ---
    # This needs its own patch context as it has a different expected flow
    with patch('app.recipes.get_inventory_ingredient_names', return_value=[]) as mock_get_empty_inv:
        result_no_inventory = suggest_recipes_with_classification(test_user_preferences)
        mock_get_empty_inv.assert_called_once()
        assert result_no_inventory == [], "Should return empty list for no inventory"

def test_suggest_recipes_no_recipes_found():
    from unittest.mock import patch
    from app.recipes import suggest_recipes_with_classification
    
    # Test when Spoonacular returns no recipes
    with patch('app.recipes.get_inventory_ingredient_names', return_value=["chicken", "rice"]):
        with patch('app.recipes.fetch_recipes_from_spoonacular', return_value=[]):
            result = suggest_recipes_with_classification({})
            
            # Should return empty list when no recipes found
            assert result == []

def test_suggest_recipes_with_classification_full(monkeypatch):
    """Test the main recipe suggestion function with ingredient classification"""
    from app.recipes import suggest_recipes_with_classification
    import app.recipes as recipes_mod
    
    # --- Mock data ---
    mock_inventory = ["chicken", "rice", "pasta", "tomato sauce", "onion", "garlic"]
    mock_user_preferences = {
        "taste_profile": {
            "sweetness": 30, 
            "saltiness": 60, 
            "sourness": 20, 
            "bitterness": 10, 
            "savoriness": 70, 
            "fattiness": 50
        },
        "effort_tolerance": "moderate",
        "dietary_restrictions": {
            "diet": "none",
            "intolerances": ["shellfish"]
        }
    }
    
    # Mock recipes returned from Spoonacular
    mock_recipes = [
        {
            "id": 1001,
            "title": "Simple Pasta Dish",
            "image": "https://example.com/pasta.jpg",
            "usedIngredientCount": 2,
            "missedIngredientCount": 1,
            "usedIngredients": [
                {"name": "pasta", "amount": 8, "unit": "oz"},
                {"name": "tomato sauce", "amount": 1, "unit": "cup"}
            ],
            "missedIngredients": [
                {"name": "basil", "amount": 2, "unit": "tbsp"}
            ]
        },
        {
            "id": 1002,
            "title": "Chicken and Rice",
            "image": "https://example.com/chicken.jpg",
            "usedIngredientCount": 3,
            "missedIngredientCount": 2,
            "usedIngredients": [
                {"name": "chicken", "amount": 12, "unit": "oz"},
                {"name": "rice", "amount": 1, "unit": "cup"},
                {"name": "onion", "amount": 1, "unit": "medium"}
            ],
            "missedIngredients": [
                {"name": "peas", "amount": 0.5, "unit": "cup"},
                {"name": "carrots", "amount": 2, "unit": "medium"}
            ]
        }
    ]
    
    # Mock recipe details
    mock_details = {
        1001: {
            "instructions": "Cook pasta. Add sauce. Serve.",
            "extendedIngredients": [
                {"name": "pasta", "amount": 8, "unit": "oz"},
                {"name": "tomato sauce", "amount": 1, "unit": "cup"},
                {"name": "basil", "amount": 2, "unit": "tbsp"}
            ]
        },
        1002: {
            "instructions": "Cook rice. Cook chicken. Mix with vegetables.",
            "extendedIngredients": [
                {"name": "chicken", "amount": 12, "unit": "oz"},
                {"name": "rice", "amount": 1, "unit": "cup"},
                {"name": "onion", "amount": 1, "unit": "medium"},
                {"name": "peas", "amount": 0.5, "unit": "cup"},
                {"name": "carrots", "amount": 2, "unit": "medium"}
            ]
        }
    }
    
    # Mock taste profiles
    mock_taste_profiles = {
        1001: {"sweetness": 20, "saltiness": 50, "sourness": 30, "bitterness": 10, "savoriness": 40, "fattiness": 30},
        1002: {"sweetness": 10, "saltiness": 60, "sourness": 10, "bitterness": 5, "savoriness": 80, "fattiness": 50}
    }
    
    # Mock AI classifications
    mock_classifications = {
        1001: [
            {"ingredient": "pasta", "category": "Essential", "in_inventory": True, "confidence": 0.9},
            {"ingredient": "tomato sauce", "category": "Essential", "in_inventory": True, "confidence": 0.8},
            {"ingredient": "basil", "category": "Optional", "in_inventory": False, "confidence": 0.7}
        ],
        1002: [
            {"ingredient": "chicken", "category": "Essential", "in_inventory": True, "confidence": 0.9},
            {"ingredient": "rice", "category": "Essential", "in_inventory": True, "confidence": 0.9},
            {"ingredient": "onion", "category": "Important", "in_inventory": True, "confidence": 0.8},
            {"ingredient": "peas", "category": "Optional", "in_inventory": False, "confidence": 0.6},
            {"ingredient": "carrots", "category": "Optional", "in_inventory": False, "confidence": 0.7}
        ]
    }
    
    # --- Mock functions ---
    # Mock inventory function
    def mock_get_inventory(use_ai_filtering=True, max_ingredients=20):
        return mock_inventory
    
    # Mock recipe fetching function
    def mock_fetch_recipes(ingredients, number=10, max_ready_time=None, dietary_restrictions=None):
        # Validate dietary restrictions are passed correctly
        if dietary_restrictions:
            assert dietary_restrictions.get("intolerances") == ["shellfish"]
        return mock_recipes
    
    # Mock recipe details function
    def mock_fetch_details(recipe_id):
        return mock_details.get(recipe_id)
    
    # Mock taste profile function
    def mock_fetch_taste(recipe_id):
        return mock_taste_profiles.get(recipe_id)
    
    # Mock AI classification function
    def mock_classify_ingredients(recipe, user_inventory, recipe_ingredients_list):
        return mock_classifications.get(recipe.get("id"))

    # Mock conversion function
    def mock_convert(recipe, available_ingredients):
        recipe_id = recipe.get("id")
        # Get the base classification structure
        base_classified = mock_classifications.get(recipe_id, [])
        
        # Recalculate in_inventory based on the provided available_ingredients
        recalculated_classified = []
        for ing_data in base_classified:
            ingredient_name = ing_data.get("ingredient", "").lower()
            # Check if the ingredient is in the current available list
            in_inventory_now = any(avail_ing.lower() == ingredient_name for avail_ing in available_ingredients)
            recalculated_classified.append({
                **ing_data,
                "in_inventory": in_inventory_now
            })

        # Calculate counts and lists based on the recalculated status
        used_count = sum(1 for ing in recalculated_classified if ing["in_inventory"])
        missed_count = len(recalculated_classified) - used_count
        used_ings = [{"name": ing["ingredient"], "amount": 1, "unit": ""} for ing in recalculated_classified if ing["in_inventory"]]
        missed_ings = [{"name": ing["ingredient"], "amount": 1, "unit": ""} for ing in recalculated_classified if not ing["in_inventory"]]
        
        # Add the fields directly to the recipe dictionary
        recipe["usedIngredientCount"] = used_count
        recipe["missedIngredientCount"] = missed_count
        recipe["usedIngredients"] = used_ings
        recipe["missedIngredients"] = missed_ings
        # Also add the recalculated classified ingredients
        recipe["classified_ingredients"] = recalculated_classified 
        return recipe # Return the modified recipe

    # Mock scoring and sorting function
    def mock_score_sort(recipes, available_ingredients, user_preferences):
        for recipe in recipes:
            # Apply simple scoring based on used ingredients
            recipe["score"] = recipe.get("usedIngredientCount", 0) * 10 
        # Sort by score, highest first
        return sorted(recipes, key=lambda r: r["score"], reverse=True)
    
    # Apply all mocks
    monkeypatch.setattr(recipes_mod, "get_inventory_ingredient_names", mock_get_inventory)
    monkeypatch.setattr(recipes_mod, "fetch_recipes_from_spoonacular", mock_fetch_recipes)
    monkeypatch.setattr(recipes_mod, "fetch_recipe_details", mock_fetch_details)
    monkeypatch.setattr(recipes_mod, "fetch_recipe_taste_profile", mock_fetch_taste)
    monkeypatch.setattr(recipes_mod, "classify_ingredients_with_ai", mock_classify_ingredients)
    # Add the new mocks
    monkeypatch.setattr(recipes_mod, "convert_classified_to_used_missed", mock_convert)
    monkeypatch.setattr(recipes_mod, "score_and_sort_recipes", mock_score_sort)
    
    # --- Test normal case ---
    results = suggest_recipes_with_classification(
        user_preferences=mock_user_preferences,
        max_ready_time=30
    )
    
    # Verify results
    assert len(results) == 2
    
    # Results should be sorted by score (Chicken and Rice should be first based on ingredient match and taste profile)
    assert results[0]["id"] == 1002
    assert results[0]["title"] == "Chicken and Rice"
    assert "score" in results[0]
    assert "classified_ingredients" in results[0]
    assert results[0]["classified_ingredients"] == mock_classifications[1002]
    
    # Check conversion to used/missed format worked
    assert "usedIngredientCount" in results[0]
    assert "missedIngredientCount" in results[0]
    assert results[0]["usedIngredientCount"] == 3
    assert results[0]["missedIngredientCount"] == 2
    
    # --- Test with inventory override ---
    override_results = suggest_recipes_with_classification(
        user_preferences=mock_user_preferences,
        inventory_override=["pasta", "tomato sauce"]
    )
    
    # Should still get results but with different scores
    assert len(override_results) == 2
    # Pasta dish should now be the better match
    assert override_results[0]["id"] == 1001
    
    # --- Test with empty inventory ---
    def mock_empty_inventory(*args, **kwargs):
        return []
    
    monkeypatch.setattr(recipes_mod, "get_inventory_ingredient_names", mock_empty_inventory)
    
    empty_results = suggest_recipes_with_classification(
        user_preferences=mock_user_preferences
    )
    
    # Should return empty list when no inventory is available
    assert empty_results == []
