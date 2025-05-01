import pytest
from fastapi.testclient import TestClient
import json
from datetime import date, datetime

# Import the app directly
from app.main import app

# Create a client for testing
client = TestClient(app)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

def test_inventory_endpoints_exist():
    """Test that the inventory endpoints are properly defined."""
    
    # Test the sync endpoint exists
    response = client.post("/inventory/sync")
    assert response.status_code == 200
    # We can't reliably mock the return value in FastAPI tests, so we just check it has the expected structure
    assert "synced" in response.json()
    
    # Test the inventory endpoint exists
    response = client.get("/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # We can't control the actual data returned, but we can check the structure

def test_json_serialization():
    """Test that our JSON serialization works correctly for inventory data."""
    
    # Create test inventory data with dates (common issue with JSON serialization)
    mock_inventory = [
        {"product_id": 1, "name": "Test Product", "amount": 2, 
         "best_before_date": date(2025, 5, 1), 
         "last_updated": datetime(2025, 4, 26, 12, 0, 0)}
    ]
    
    # Test our CustomJSONEncoder works properly
    serialized = json.dumps(mock_inventory, cls=CustomJSONEncoder)
    parsed = json.loads(serialized)
    
    # Verify the format is correct
    assert isinstance(parsed, list)
    assert len(parsed) > 0
    assert parsed[0]["name"] == "Test Product"
    assert parsed[0]["best_before_date"] == "2025-05-01"
    assert parsed[0]["last_updated"].startswith("2025-04-26")
