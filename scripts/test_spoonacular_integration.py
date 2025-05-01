# scripts/test_spoonacular_integration.py
import os
import httpx
import json

# --- Configuration ---
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")
SPOONACULAR_API_URL = "https://api.spoonacular.com/recipes/complexSearch"
TEST_INGREDIENTS = ["chicken", "rice", "onion"] # Sample ingredients
NUM_RECIPES = 3 # Number of recipes to request

# --- Check API Key ---
if not SPOONACULAR_API_KEY:
    print("Error: SPOONACULAR_API_KEY environment variable not set.")
    exit(1)

if "dummy" in SPOONACULAR_API_KEY:
    print("Warning: SPOONACULAR_API_KEY seems to be a dummy key. Real API call will likely fail.")

# --- Prepare Request ---
params = {
    "apiKey": SPOONACULAR_API_KEY,
    "ingredients": ",".join(TEST_INGREDIENTS),
    "number": NUM_RECIPES,
    "ranking": 2, # Maximize used ingredients
    "ignorePantry": False,
    "fillIngredients": True, # Get detailed ingredient info
    "addRecipeInformation": True # Get full recipe details
}

# --- Make API Call ---
print(f"--- Testing Spoonacular Integration ({SPOONACULAR_API_URL}) ---")
print(f"Searching for {NUM_RECIPES} recipes with ingredients: {', '.join(TEST_INGREDIENTS)}")

try:
    with httpx.Client() as client:
        response = client.get(SPOONACULAR_API_URL, params=params, timeout=30.0) # Increased timeout

    print(f"\nStatus Code: {response.status_code}")

    # --- Process Response ---
    if response.status_code == 200:
        data = response.json()
        print(f"Successfully received {len(data.get('results', []))} recipes.")
        print("\n--- Sample Response Data (first recipe if available) ---")
        if data.get("results"):
            # Pretty print the first recipe
            print(json.dumps(data["results"][0], indent=2))
        else:
            print("No recipes found in the response.")
            print("\nFull Response:")
            print(json.dumps(data, indent=2)) # Print the full response if results are empty

    elif response.status_code == 401:
        print("Error: Unauthorized (401). Check your SPOONACULAR_API_KEY.")
        try:
            print("Response Body:", response.json())
        except Exception:
            print("Response Body:", response.text)
    elif response.status_code == 402:
         print("Error: Payment Required (402). You might have exceeded your Spoonacular API quota.")
         try:
            print("Response Body:", response.json())
         except Exception:
            print("Response Body:", response.text)
    else:
        print(f"Error: Received status code {response.status_code}")
        try:
            print("Response Body:", response.json())
        except Exception:
            print("Response Body:", response.text)

except httpx.RequestError as exc:
    print(f"An error occurred while requesting {exc.request.url!r}: {exc}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("\n--- Spoonacular Integration Test Complete ---")
