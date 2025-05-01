import pytest
from unittest.mock import patch, MagicMock
from app.inventory import filter_valid_food_ingredients

def test_filter_valid_food_ingredients():
    """Test the AI-based filtering of food ingredients"""

    # Sample inventory with mixed food and non-food items
    mixed_inventory = [
        "chicken breast",
        "paper towels",
        "rice",
        "soap",
        "tomatoes",
        "trash bags",
        "olive oil",
        "batteries"
    ]

    # Expected food items only
    expected_food_items = [
        "chicken breast",
        "rice",
        "tomatoes",
        "olive oil"
    ]

    # Mock the OpenAI client response
    with patch('app.inventory.client') as mock_client:
        # Configure mock to return correct JSON structure
        mock_response = MagicMock()
        mock_client.responses.create.return_value = mock_response
        
        # Mock the output_text property with our expected JSON result
        mock_response.output_text = '["chicken breast", "rice", "tomatoes", "olive oil"]'
        
        # Mock cache to ensure we test the AI call path
        with patch('app.inventory.get_cache', return_value=None):
            with patch('app.inventory.set_cache'):
                # Run the function
                result = filter_valid_food_ingredients(mixed_inventory)

                # Verify results
                assert sorted(result) == sorted(expected_food_items)

def test_filter_valid_food_ingredients_with_cache():
    """Test the caching of food ingredient filtering results"""
    
    mixed_inventory = ["chicken", "paper towels", "rice"]
    cached_result = ["chicken", "rice"]
    
    with patch('app.inventory.get_cache', return_value=cached_result):
        result = filter_valid_food_ingredients(mixed_inventory)
        assert result == cached_result
        
def test_filter_valid_food_ingredients_empty():
    """Test filtering with an empty inventory"""
    
    empty_inventory = []
    
    result = filter_valid_food_ingredients(empty_inventory)
    assert result == []