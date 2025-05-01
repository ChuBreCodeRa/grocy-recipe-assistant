# scripts/test_openai_integration.py
import os
from openai import OpenAI, APIError, AuthenticationError

# --- Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo") # Default to a common model
TEST_PROMPT = "Suggest one simple dinner recipe using chicken and rice."

# --- Check API Key ---
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable not set.")
    exit(1)

if "dummy" in OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY seems to be a dummy key. Real API call will likely fail.")
    # Optionally exit here if you don't want to proceed with a dummy key
    # exit(1)

# --- Initialize Client ---
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    exit(1)

# --- Make API Call ---
print(f"--- Testing OpenAI Integration (Model: {OPENAI_MODEL}) ---")
print(f"Sending prompt: \"{TEST_PROMPT}\"")

try:
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": TEST_PROMPT}
        ],
        temperature=0.5,
        max_tokens=150
    )

    print("\nStatus: Success")
    print("\n--- Response Data ---")
    if response.choices:
        print("Assistant's Response:")
        print(response.choices[0].message.content)
    else:
        print("No choices returned in the response.")

    print("\nFull Response Object (excluding choices for brevity if present):")
    response_dict = response.model_dump()
    if response.choices:
         response_dict.pop("choices", None) # Remove choices for cleaner output
    import json
    print(json.dumps(response_dict, indent=2))


except AuthenticationError as e:
    print(f"\nError: OpenAI Authentication Failed ({e.status_code}). Check your OPENAI_API_KEY.")
    print(f"Response body: {e.body}")
except APIError as e:
    print(f"\nError: OpenAI API Error ({e.status_code}).")
    print(f"Response body: {e.body}")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")

print("\n--- OpenAI Integration Test Complete ---")
