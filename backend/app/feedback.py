import logging
import json
import os
import re
from openai import OpenAI
from app.models import get_db_connection
from app.cache import get_cache, set_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use default dummy key if not provided to prevent errors during testing
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy_key_for_tests")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14")

# Set up OpenAI client if we have a real API key
if "dummy" not in OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

# Updated prompt to extract numeric taste scores (0-100)
REVIEW_PARSING_PROMPT = """
You are a meal review interpreter.
Task: Parse a user's natural language review of a meal to extract:
- Effort perception: "easy", "moderate", or "hard"
- Overall sentiment: "positive", "neutral", or "negative"
- Estimated taste profile scores (0-100): sweetness, saltiness, sourness, bitterness, savoriness, fattiness.

Respond strictly in JSON format:
{
  "effort_tag": "...",
  "sentiment": "...",
  "taste_profile": {
    "sweetness": <0-100>,
    "saltiness": <0-100>,
    "sourness": <0-100>,
    "bitterness": <0-100>,
    "savoriness": <0-100>,
    "fattiness": <0-100>
  }
}

Review: {review_text}
"""


def parse_review_with_ai(review_text):
    cache_key = f"ai:review:numeric:{hash(review_text)}"  # Updated cache key
    cached = get_cache(cache_key)
    if cached:
        return cached

    # Skip API calls if we're using a dummy key or have no client
    if "dummy" in OPENAI_API_KEY or client is None:
        logger.warning("Using dummy OpenAI API key - returning empty review parsing")
        return {"effort_tag": None, "sentiment": None, "taste_profile": None}

    try:
        prompt_content = REVIEW_PARSING_PROMPT.format(review_text=review_text)

        # --- Corrected OpenAI API Call ---
        response = client.responses.create(
            model=OPENAI_MODEL, input=prompt_content, temperature=0.2, store=True
        )

        # Extract the JSON string from the response
        result_text = response.output_text

        # Try to parse the response as JSON
        try:
            # Attempt to load the JSON directly
            result = json.loads(result_text)

            # More robust validation
            if (
                not isinstance(result, dict)
                or "taste_profile" not in result
                or not isinstance(result["taste_profile"], dict)
                or "effort_tag" not in result
                or "sentiment" not in result
            ):
                raise ValueError("Parsed JSON missing required keys or has incorrect structure")

            # Validate taste profile contents (optional but good)
            required_tastes = [
                "sweetness",
                "saltiness",
                "sourness",
                "bitterness",
                "savoriness",
                "fattiness",
            ]
            if not all(
                k in result["taste_profile"]
                and isinstance(result["taste_profile"][k], (int, float))
                for k in required_tastes
            ):
                raise ValueError("Taste profile missing keys or has non-numeric values")

            set_cache(cache_key, result, ex=86400)
            return result

        except Exception as e:
            logger.error(f"Error parsing AI review response: {e}. Response text: {result_text}")
            return {"effort_tag": None, "sentiment": None, "taste_profile": None}

    except Exception as e:
        logger.error(f"AI review parsing failed: {e}")
        return {"effort_tag": None, "sentiment": None, "taste_profile": None}


# Updated to handle taste_profile dictionary
def store_feedback(user_id, recipe_id, rating, review_text, effort_tag, sentiment, taste_profile):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Note: Assumes user_ratings table will have columns for each taste score
        cur.execute(
            """
            INSERT INTO user_ratings (user_id, recipe_id, rating, review_text, effort_tag, sentiment, 
                                      sweetness, saltiness, sourness, bitterness, savoriness, fattiness)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                user_id,
                recipe_id,
                rating,
                review_text,
                effort_tag,
                sentiment,
                taste_profile.get("sweetness"),
                taste_profile.get("saltiness"),
                taste_profile.get("sourness"),
                taste_profile.get("bitterness"),
                taste_profile.get("savoriness"),
                taste_profile.get("fattiness"),
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Storing feedback failed: {e}")


def handle_feedback(user_id, recipe_id, rating, review_text):
    parsed = parse_review_with_ai(review_text)
    if parsed.get("taste_profile"):
        store_feedback(
            user_id,
            recipe_id,
            rating,
            review_text,
            parsed.get("effort_tag"),
            parsed.get("sentiment"),
            parsed.get("taste_profile"),
        )
    return parsed
