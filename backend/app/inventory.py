import os
import httpx
import logging
import json
from datetime import datetime
from openai import OpenAI
from app.models import get_db_connection
from app.cache import get_cache, set_cache

# Use default values for testing when environment variables aren't set
GROCY_API_URL = os.getenv("GROCY_API_URL", "https://demo-grocy.example.com/api")
GROCY_API_KEY = os.getenv("GROCY_API_KEY", "dummy_key_for_testing")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy_key_for_testing")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14")

HEADERS = {"GROCY-API-KEY": GROCY_API_KEY}

DB_CHANGED_TIME_ENDPOINT = f"{GROCY_API_URL}/system/db-changed-time" if GROCY_API_URL else ""
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
    cur.execute("SELECT last_changed_time FROM inventory_sync_metadata ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def set_last_changed_time(changed_time):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO inventory_sync_metadata (last_changed_time) VALUES (%s)", (changed_time,))
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
        cur.execute('''
            INSERT INTO inventory (product_id, name, amount, best_before_date, last_updated)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (product_id) DO UPDATE SET
                name = EXCLUDED.name,
                amount = EXCLUDED.amount,
                best_before_date = EXCLUDED.best_before_date,
                last_updated = NOW()
        ''', (product_id, name, amount, best_before_date))
        
    # --- Add Deletion Step --- 
    # Delete items from local DB that are NOT in the latest Grocy data
    if grocy_product_ids:
        # Create placeholders for the list of IDs
        placeholders = ",".join(["%s"] * len(grocy_product_ids))
        delete_query = f"DELETE FROM inventory WHERE product_id NOT IN ({placeholders})"
        cur.execute(delete_query, list(grocy_product_ids))
        logger.info(f"Removed {cur.rowcount} items from local inventory that are no longer in Grocy.")
    else:
        # If Grocy returned an empty list, delete everything from local inventory
        cur.execute("DELETE FROM inventory")
        logger.warning("Grocy API returned empty inventory, clearing local inventory table.")
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
        logger.error(f"Inventory sync failed: {e}")
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
        cur.execute("""
            SELECT product_id, name, amount, best_before_date, last_updated
            FROM inventory 
            WHERE amount > 0
        """)
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
        logger.error(f"Error fetching inventory: {e}")
        return []


def filter_valid_food_ingredients(inventory_items, max_ingredients=20):
    """
    Use AI to filter inventory items to only include valid food ingredients.
    This prevents non-food items from being included in recipe searches.
    
    Args:
        inventory_items: List of inventory item names
        max_ingredients: Maximum number of ingredients to return (default: 20)
        
    Returns:
        List of valid food ingredient names
    """
    if not inventory_items:
        return []
        
    # Convert inventory items to a list of names only
    item_names = [item["name"] if isinstance(item, dict) else item for item in inventory_items]
    
    # Create cache key based on inventory names (sorted for consistency)
    cache_key = f"filtered_ingredients:{','.join(sorted(item_names))}"
    cached = get_cache(cache_key)
    if cached:
        logger.info(f"Using cached filtered ingredients ({len(cached)} items)")
        return cached[:max_ingredients]
    
    # Skip AI filtering if no valid OpenAI client
    if "dummy" in OPENAI_API_KEY or client is None:
        logger.warning("No valid OpenAI API key - returning unfiltered ingredients")
        # Just return the raw names, trimmed to max_ingredients
        return item_names[:max_ingredients]
    
    try:
        # --- Updated Prompt for Generalization --- 
        prompt = f"""
You are a food ingredient specialist assisting with recipe searches.
Analyze this inventory list:
1. Identify items that are valid food ingredients suitable for cooking.
2. For each valid food ingredient, generalize its name to a common term used in recipes. Remove brand names, specific preparations (like 'frosted'), or packaging details (like 'tall can'). Examples: 'poptarts frosted brown sugar' -> 'toaster pastry' or 'pastry'; 'sweet baby rays BBQ sauce' -> 'BBQ sauce'; 'tuna helper cheeseburger macaroni' -> 'macaroni and cheese mix' or 'pasta mix'.
3. Skip any non-food items, tools, containers, or generic descriptions.
4. Return ONLY a JSON array of the generalized food ingredient strings.

Inventory items: {', '.join(item_names)}

Return only a JSON array of generalized food ingredient strings:
"""
        # --- End of Updated Prompt ---

        # --- Corrected OpenAI API Call --- 
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            temperature=0.2,
            store=True
        )
        
        # Extract the JSON string from the response
        result_text = response.output_text
        
        # Try to parse the response
        try:
            # Attempt to load the JSON directly first
            parsed_json = json.loads(result_text)
            
            # Check if the response is a dictionary containing the expected array
            # (Some models might wrap the array in a key like "ingredients")
            if isinstance(parsed_json, dict):
                # Look for a key that holds a list
                list_key = next((k for k, v in parsed_json.items() if isinstance(v, list)), None)
                if list_key:
                    filtered_ingredients = parsed_json[list_key]
                else:
                    raise ValueError("JSON response is a dict but contains no list")
            elif isinstance(parsed_json, list):
                filtered_ingredients = parsed_json
            else:
                 raise ValueError("JSON response is not a list or a dict containing a list")

            # Ensure all items in the list are strings
            if not all(isinstance(item, str) for item in filtered_ingredients):
                raise ValueError("JSON list contains non-string items")

            logger.info(f"AI filtered {len(item_names)} items down to {len(filtered_ingredients)} food ingredients")
            
            # Cache the result for 1 day
            set_cache(cache_key, filtered_ingredients, ex=86400)
            
            # Return filtered list, limited to max_ingredients
            return filtered_ingredients[:max_ingredients]
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}. Response text: {result_text}")
            # Fall back to raw list if parsing fails
            return item_names[:max_ingredients]
            
    except Exception as e:
        logger.error(f"Error filtering ingredients with AI: {e}")
        # Fall back to raw list if AI call fails
        return item_names[:max_ingredients]


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
            logger.info(f"Applying AI filtering to {len(all_items)} inventory items")
            filtered_items = filter_valid_food_ingredients(all_items, max_ingredients)
            return filtered_items
        else:
            # Just return first max_ingredients
            return all_items[:max_ingredients]
            
    except Exception as e:
        logger.error(f"Error fetching inventory ingredients: {e}")
        return []
