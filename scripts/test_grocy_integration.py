# scripts/test_grocy_integration.py
import os
import httpx
import json

# --- Configuration ---
GROCY_API_KEY = os.getenv("GROCY_API_KEY")
GROCY_API_URL = os.getenv("GROCY_API_URL") # Changed from GROCY_URL

# --- Check Configuration ---
if not GROCY_API_KEY:
    print("Error: GROCY_API_KEY environment variable not set.")
    exit(1)
if not GROCY_API_URL:
    print("Error: GROCY_API_URL environment variable not set.") # Changed variable name
    exit(1)

# Ensure URL does NOT end with /api as the script adds it
GROCY_BASE_URL = GROCY_API_URL.strip().rstrip('/api').rstrip('/') # Get base URL
SYSTEM_INFO_ENDPOINT = f"{GROCY_BASE_URL}/api/system/info" # Construct endpoint correctly

# --- Prepare Request ---
headers = {
    "GROCY-API-KEY": GROCY_API_KEY,
    "Accept": "application/json"
}

# --- Make API Call ---
print(f"--- Testing Grocy Integration ({GROCY_BASE_URL}) ---") # Use base URL for clarity
print(f"Attempting to fetch system info from: {SYSTEM_INFO_ENDPOINT}")

try:
    with httpx.Client() as client:
        response = client.get(SYSTEM_INFO_ENDPOINT, headers=headers, timeout=10.0)

    print(f"\nStatus Code: {response.status_code}")

    # --- Process Response ---
    if response.status_code == 200:
        data = response.json()
        print("Successfully connected to Grocy.")
        print("\n--- System Info ---")
        print(json.dumps(data, indent=2))

    elif response.status_code == 401:
        print(f"Error: Unauthorized (401). Check your GROCY_API_KEY and Grocy URL ({GROCY_BASE_URL}).") # Added URL context
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

except httpx.ConnectError as exc:
     print(f"Connection Error: Could not connect to {GROCY_BASE_URL}. Is Grocy running and the URL correct?") # Use base URL
     print(f"Details: {exc}")
except httpx.RequestError as exc:
    print(f"An error occurred while requesting {exc.request.url!r}: {exc}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("\n--- Grocy Integration Test Complete ---")
