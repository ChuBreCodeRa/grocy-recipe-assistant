import json
import logging
import os
import re
from datetime import datetime
import httpx
from openai import OpenAI
from app.cache import get_cache, set_cache
from app.models import get_db_connection

# Use default values for testing when environment variables aren't set
GROCY_API_URL = os.getenv("GROCY_API_URL", "https://demo-grocy.example.com/api")
GROCY_API_KEY = os.getenv("GROCY_API_KEY", "dummy_key_for_testing")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy_key_for_testing")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14")

HEADERS = {"GROCY-API-KEY": GROCY_API_KEY}

DB_CHANGED_TIME_ENDPOINT = (
    f"{GROCY_API_URL}/system/db-changed-time" if GROCY_API_URL else ""
)
INVENTORY_ENDPOINT = f"{GROCY_API_URL}/stock" if GROCY_API_URL else ""

# Only set up OpenAI client if we have a real API key
if "dummy" not in OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_last_changed_time():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT last_changed_time FROM inventory_sync_metadata ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def set_last_changed_time(changed_time):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO inventory_sync_metadata (last_changed_time) VALUES (%s)",
        (changed_time,),
    )
    conn.commit()
    cur.close()
    conn.close()


def update_inventory_table(inventory):
    conn = get_db_connection()
    cur = conn.cursor()

    # Get a list of all product IDs received from Grocy API
    grocy_product_ids = {item["product_id"] for item in inventory}

    # Update or Insert items from Grocy API data
    for item in inventory:
        product_id = item["product_id"]
        name = item["product"]["name"]
        amount = item["amount"]
        best_before_date = item["best_before_date"]
        cur.execute(
            """
            INSERT INTO inventory (product_id, name, amount, best_before_date, last_updated)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (product_id) DO UPDATE SET
                name = EXCLUDED.name,
                amount = EXCLUDED.amount,
                best_before_date = EXCLUDED.best_before_date,
                last_updated = NOW()
        """,
            (product_id, name, amount, best_before_date),
        )

    # --- Add Deletion Step ---
    # Delete items from local DB that are NOT in the latest Grocy data
    if grocy_product_ids:
        # Create placeholders for the list of IDs
        placeholders = ",".join(["%s"] * len(grocy_product_ids))
        delete_query = f"DELETE FROM inventory WHERE product_id NOT IN ({placeholders})"
        cur.execute(delete_query, list(grocy_product_ids))
        logger.info(
            "Removed %d items from local inventory that are no longer in Grocy.",
            cur.rowcount
        )
    else:
        # If Grocy returned an empty list, delete everything from local inventory
        cur.execute("DELETE FROM inventory")
        logger.warning(
            "Grocy API returned empty inventory, clearing local inventory table."
        )
    # --- End Deletion Step ---

    conn.commit()
    cur.close()
    conn.close()


def sync_inventory():
    try:
        resp = httpx.get(DB_CHANGED_TIME_ENDPOINT, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        changed_time = resp.json()["changed_time"]
        last_changed_time = get_last_changed_time()

        # --- Restore Timestamp Check ---
        if last_changed_time and str(last_changed_time) == changed_time:
            logger.info("No inventory change detected. Skipping sync.")
            return False
        # --- End Restore ---

        inv_resp = httpx.get(INVENTORY_ENDPOINT, headers=HEADERS, timeout=20)
        inv_resp.raise_for_status()
        inventory = inv_resp.json()
        update_inventory_table(inventory)
        set_last_changed_time(changed_time)
        logger.info("Inventory sync completed.")
        return True
    except Exception as e:
        logger.error("Inventory sync failed: %s", e)
        return False


def get_inventory():
    """
    Fetch all inventory items from the local database.
    Returns:
        list: List of inventory items with their details
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT product_id, name, amount, best_before_date, last_updated
            FROM inventory 
            WHERE amount > 0
        """
        )
        columns = ["product_id", "name", "amount", "best_before_date", "last_updated"]
        results = []
        for row in cur.fetchall():
            item = {}
            for i, col in enumerate(columns):
                item[col] = row[i]
            results.append(item)
        cur.close()
        conn.close()
        return results
    except Exception as e:
        logger.error("Error fetching inventory: %s", e)
        return []


def filter_valid_food_ingredients(inventory_items, max_ingredients=20):
    """
    Filter inventory items to identify valid food ingredients, preserving original names.
    Only filters out non-food items without generalizing food item names.
    
    Args:
        inventory_items: List of inventory item names
        max_ingredients: Maximum number of ingredients to return (default: 20)
        
    Returns:
        List of valid food ingredient names (preserving original names)
    """
    if not inventory_items:
        return []
        
    # Convert inventory items to a list of names only
    item_names = [
        item["name"] if isinstance(item, dict) else item for item in inventory_items
    ]

    # Create cache key based on inventory names (sorted for consistency)
    cache_key = f"filtered_ingredients:{','.join(sorted(item_names))}"
    cached = get_cache(cache_key)
    if cached:
        logger.info("Using cached filtered ingredients (%d items)", len(cached))
        return cached[:max_ingredients]
    
    # If we don't have OpenAI access, fall back to simple heuristics
    if "dummy" in OPENAI_API_KEY or client is None:
        logger.warning("No valid OpenAI API key - using heuristic food filtering")
        return _heuristic_food_filtering(item_names, max_ingredients)

    try:
        # Use a more precise prompt that focuses on identification NOT generalization
        prompt = """You are a food ingredient specialist assisting with recipe searches.
Analyze this inventory list and return ONLY a JSON array containing the original names of valid food items.

Guidelines:
- Return the EXACT original names of food items without generalizing them
- Only filter out non-food items (paper products, cleaning supplies, etc.)
- INCLUDE prepared food items like "taco dinner kit" or "pasta sauce mix" 
- INCLUDE all original ingredients even if they contain brand names or packaging details
- Do not combine or group similar items

Inventory items: {inventory_items}"""

        formatted_prompt = prompt.format(inventory_items=", ".join(item_names))

        # Make the AI call with lower temperature for more consistent results
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=formatted_prompt,
            temperature=0.1,  # Lower temperature for consistent results
            store=True,
        )

        result_text = response.output_text
        logger.info("Raw food ingredients response starts with: %s", result_text[:50])

        # Try to parse the result as JSON
        try:
            # Try to extract the JSON array if it's embedded in text
            import re

            array_match = re.search(r'\[\s*"[^"]+(?:",\s*"[^"]+")*"\s*\]', result_text)
            if array_match:
                result_text = array_match.group(0)

            result = json.loads(result_text)
            if isinstance(result, list):
                # Keep only the first max_ingredients
                filtered = result[:max_ingredients]
                logger.info(
                    "AI filtered %d items down to %d food ingredients",
                    len(item_names),
                    len(filtered)
                )

                # Cache the result for 24 hours
                set_cache(cache_key, filtered, ex=86400)
                return filtered

        except json.JSONDecodeError:
            logger.error("Failed to parse AI response as JSON for food ingredients")
            # Fall back to heuristic filtering
            return _heuristic_food_filtering(item_names, max_ingredients)

    except Exception as e:
        logger.error("Error filtering food ingredients with AI: %s", str(e))
        return _heuristic_food_filtering(item_names, max_ingredients)

    # If we get here, the AI didn't return a valid list
    return _heuristic_food_filtering(item_names, max_ingredients)


def _heuristic_food_filtering(item_names, max_ingredients=20):
    """
    Fallback method to filter food ingredients without normalizing or generalizing them.
    Simply removes non-food items while preserving the original names.

    Args:
        item_names: List of inventory item names
        max_ingredients: Maximum number of ingredients to return

    Returns:
        List of food ingredient names with original names preserved
    """
    # Common non-food items to filter out
    non_food_keywords = [
        "detergent", "soap", "cleaner", "toilet", "paper", "towel", "napkin", 
        "plate", "cup", "fork", "spoon", "knife", "dish", "sponge", "trash", 
        "bag", "container", "battery", "bulb", "light", "pen", "pencil", 
        "marker", "tape", "glue", "scissors", "tool", "wrench", "screwdriver",
    ]

    # Clean inventory items - ONLY filter out non-food items, no generalization
    cleaned_items = []
    for name in item_names:
        # Skip obvious non-food items
        if any(keyword in name.lower() for keyword in non_food_keywords):
            continue

        # Clean up the name (just remove size/weight if present)
        clean_name = name.lower()
        if " - " in clean_name:
            clean_name = clean_name.split(" - ")[0].strip()

        # Add to our list if not already there
        if clean_name and clean_name not in cleaned_items:
            cleaned_items.append(clean_name)

    logger.info(
        "Heuristic filtering: %d items → %d food ingredients (original names preserved)",
        len(item_names),
        len(cleaned_items)
    )
    return cleaned_items[:max_ingredients]


def get_inventory_ingredient_names(use_ai_filtering=True, max_ingredients=20):
    """
    Fetch available ingredient names from the inventory database.
    Optionally filter with AI to include only valid food ingredients.

    Args:
        use_ai_filtering: Whether to use AI to filter out non-food items
        max_ingredients: Maximum number of ingredients to return

    Returns:
        List of ingredient names
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM inventory WHERE amount > 0")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Extract names from database results
        all_items = [row[0].lower() for row in rows]

        # Apply AI filtering if requested
        if use_ai_filtering and all_items:
            logger.info("Applying AI filtering to %d inventory items", len(all_items))
            filtered_items = filter_valid_food_ingredients(all_items, max_ingredients)
            return filtered_items
        else:
            # Just return first max_ingredients
            return all_items[:max_ingredients]

    except Exception as e:
        logger.error("Error fetching inventory ingredients: %s", e)
        return []
