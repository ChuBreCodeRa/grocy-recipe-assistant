import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_feedback_submission(monkeypatch):
    client = TestClient(app)
    # Mock OpenAI call - Updated to return numeric taste profile
    import app.feedback as feedback_mod
    mock_parsed_data = {
        "effort_tag": "easy",
        "sentiment": "positive",
        "taste_profile": {
            "sweetness": 15,
            "saltiness": 65,
            "sourness": 10,
            "bitterness": 5,
            "savoriness": 75,
            "fattiness": 40
        }
    }
    def mock_parse_review_with_ai(review_text):
        return mock_parsed_data
    monkeypatch.setattr(feedback_mod, "parse_review_with_ai", mock_parse_review_with_ai)
    
    # Mock DB store_feedback (optional, but good practice to prevent actual DB writes)
    def mock_store_feedback(*args, **kwargs):
        pass # Do nothing
    monkeypatch.setattr(feedback_mod, "store_feedback", mock_store_feedback)

    # Submit feedback
    payload = {
        "user_id": "alyssa",
        "recipe_id": "123",
        "rating": 5,
        "review_text": "Delicious and easy!"
    }
    resp = client.post("/feedback/submit", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    
    # Check response structure - Updated assertions
    assert "parsed" in data
    assert data["parsed"]["effort_tag"] == "easy"
    assert data["parsed"]["sentiment"] == "positive"
    assert "taste_profile" in data["parsed"]
    assert isinstance(data["parsed"]["taste_profile"], dict)
    assert data["parsed"]["taste_profile"]["savoriness"] == 75 # Example check
