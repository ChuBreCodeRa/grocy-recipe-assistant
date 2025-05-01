import pytest
from unittest.mock import MagicMock, patch
import json

from app.recipes import fetch_recipes_from_spoonacular

def test_dietary_restrictions_in_spoonacular_request():
    """Test that dietary restrictions are properly included in Spoonacular API calls."""
    
    # Mock ingredients and preferences
    ingredients = ["tomato", "chicken", "rice"]
    dietary_restrictions = {
        "diet": "vegetarian",
        "intolerances": ["dairy", "shellfish"]
    }
    
    # Mock httpx response
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"results": []}
    
    # Mock function dependencies
    with patch('app.recipes.get_cache', return_value=None):
        with patch('app.recipes.set_cache'):
            with patch('httpx.get', return_value=mock_response) as mock_get:
                
                # Call the function with dietary restrictions
                fetch_recipes_from_spoonacular(ingredients, dietary_restrictions=dietary_restrictions)
                
                # Check that the API was called with correct parameters
                args, kwargs = mock_get.call_args
                params = kwargs.get('params', {})
                
                # Verify dietary restrictions were included
                assert params.get('diet') == 'vegetarian'
                assert params.get('intolerances') == 'dairy,shellfish'
                assert params.get('includeIngredients') == 'tomato,chicken,rice'

def test_dietary_restrictions_caching():
    """Test that different dietary restrictions produce different cache keys."""
    
    ingredients = ["potato", "onion"]
    
    # Define two different dietary restriction sets
    vegetarian = {
        "diet": "vegetarian",
        "intolerances": ["gluten"]
    }
    
    vegan = {
        "diet": "vegan", 
        "intolerances": ["nuts"]
    }
    
    # Mock cache and response
    mock_cache = {}
    
    def mock_get_cache(key):
        return mock_cache.get(key)
        
    def mock_set_cache(key, value, ex=None):
        mock_cache[key] = value
    
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"results": [{"id": 1, "title": "Test Recipe"}]}
    
    # Test with first dietary restriction
    with patch('app.recipes.get_cache', mock_get_cache):
        with patch('app.recipes.set_cache', mock_set_cache):
            with patch('httpx.get', return_value=mock_response):
                result1 = fetch_recipes_from_spoonacular(ingredients, dietary_restrictions=vegetarian)
                
    # Test with second dietary restriction
    with patch('app.recipes.get_cache', mock_get_cache):
        with patch('app.recipes.set_cache', mock_set_cache):
            with patch('httpx.get', return_value=mock_response):
                result2 = fetch_recipes_from_spoonacular(ingredients, dietary_restrictions=vegan)
    
    # We should have two different cache entries
    assert len(mock_cache) == 2
    
    # Both results should match the mock data
    assert result1 == [{"id": 1, "title": "Test Recipe"}]
    assert result2 == [{"id": 1, "title": "Test Recipe"}]

def test_user_preferences_integration():
    """Test integration of user preferences with recipe suggestion."""
    
    from app.main import app, get_user_preferences
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Mock the get_user_preferences function to return dietary restrictions
    def mock_get_preferences(user_id):
        return {
            "taste_profile": {"sweetness": 50, "saltiness": 50},
            "effort_tolerance": "moderate",
            "dietary_restrictions": {"diet": "vegetarian", "intolerances": ["gluten"]}
        }
    
    # Also mock suggest_recipes_with_classification to verify dietary restrictions are passed
    mock_recipes = [{"id": 123, "title": "Vegetarian Test Recipe"}]
    
    with patch('app.main.get_user_preferences', mock_get_preferences):
        with patch('app.main.suggest_recipes_with_classification', return_value=mock_recipes) as mock_suggest:
            response = client.post("/ai/suggest-recipes", json={"user_id": "test_user"})
            
            # Check that API returned success
            assert response.status_code == 200
            
            # Check that the dietary restrictions were passed to suggest_recipes
            args, kwargs = mock_suggest.call_args
            user_prefs = kwargs.get('user_preferences', {})
            assert user_prefs.get('dietary_restrictions', {}).get('diet') == 'vegetarian'
            assert 'gluten' in user_prefs.get('dietary_restrictions', {}).get('intolerances', [])
            
            # Check that we got our mock recipe in response
            assert response.json()[0]['title'] == 'Vegetarian Test Recipe'