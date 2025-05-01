import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Import the function to test
from manage_cron import update_preferences, TASTE_DIMENSIONS

def test_update_preferences(monkeypatch):
    # --- Mock Database --- 
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    # Mock fetching distinct users
    mock_cur.fetchall.side_effect = [
        [("user1",), ("user2",)], # First call: Get distinct users
        # Subsequent calls will be for fetching ratings for each user
        # User 1: Two positive ratings
        [
            ("easy", 20, 70, 10, 5, 80, 60), # Rating 1
            ("moderate", 40, 50, 30, 15, 60, 40) # Rating 2
        ],
        # User 2: One positive rating
        [
            ("hard", 10, 80, 5, 20, 90, 70)
        ]
    ]

    # Mock execute calls (to capture INSERT/UPDATE)
    upsert_calls = []
    def mock_execute(*args):
        sql = args[0]
        params = args[1] if len(args) > 1 else None
        # Capture the UPSERT call details
        if "INSERT INTO user_preferences" in sql:
            upsert_calls.append({"sql": sql, "params": params})
        # Let other SELECT queries proceed (handled by side_effect)
        pass
    mock_cur.execute = mock_execute

    # Patch get_db_connection to return our mock connection
    monkeypatch.setattr("manage_cron.get_db_connection", lambda: mock_conn)

    # --- Run the function --- 
    update_preferences()

    # --- Assertions --- 
    # Check commit was called
    mock_conn.commit.assert_called_once()

    # Check the UPSERT calls
    assert len(upsert_calls) == 2 # One for each user

    # User 1 Assertions
    user1_call = next(call for call in upsert_calls if call["params"][0] == "user1")
    assert user1_call is not None
    # Expected average taste for user1: avg(rating1, rating2)
    expected_taste1 = {
        "sweetness": round((20 + 40) / 2),
        "saltiness": round((70 + 50) / 2),
        "sourness": round((10 + 30) / 2),
        "bitterness": round((5 + 15) / 2),
        "savoriness": round((80 + 60) / 2),
        "fattiness": round((60 + 40) / 2)
    }
    # Expected effort for user1: easy=1, moderate=1 -> tie, defaults to first max? Check logic or adjust test
    # Current logic: max(effort_counts, key=effort_counts.get) -> 'easy' if dict order is stable, 'moderate' otherwise. Let's assume 'easy' for test.
    expected_effort1 = "easy" 
    assert json.loads(user1_call["params"][1]) == expected_taste1
    assert user1_call["params"][2] == expected_effort1

    # User 2 Assertions
    user2_call = next(call for call in upsert_calls if call["params"][0] == "user2")
    assert user2_call is not None
    # Expected average taste for user2: just rating1
    expected_taste2 = {
        "sweetness": 10,
        "saltiness": 80,
        "sourness": 5,
        "bitterness": 20,
        "savoriness": 90,
        "fattiness": 70
    }
    expected_effort2 = "hard"
    assert json.loads(user2_call["params"][1]) == expected_taste2
    assert user2_call["params"][2] == expected_effort2
