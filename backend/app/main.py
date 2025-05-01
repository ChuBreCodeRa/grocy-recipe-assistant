import json
from datetime import date
from fastapi import FastAPI, Body, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any

from app.models import init_db, get_db_connection, create_user
from app.inventory import sync_inventory, get_inventory
from app.recipes import suggest_recipes_with_classification
from app.feedback import handle_feedback

# Custom JSON encoder to handle date objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)

app = FastAPI()

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
async def root():
    return {"message": "Grocy Recipe Assistant API is running"}

# User Management Endpoints
@app.post("/users/create")
def create_new_user(payload: dict = Body(...)):
    """
    Create a new user in the system with optional preferences.
    """
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing required field: user_id")
        
    # Extract optional preferences if provided
    default_preferences = {
        "taste_profile": payload.get("taste_profile", {}),
        "effort_tolerance": payload.get("effort_tolerance", "moderate"),
        "liked_ingredients": payload.get("liked_ingredients", []),
        "disliked_ingredients": payload.get("disliked_ingredients", []),
        "preferred_dish_types": payload.get("preferred_dish_types", [])
    }
    
    success = create_user(user_id, default_preferences)
    if success:
        return {"status": "success", "message": f"User '{user_id}' created successfully"}
    else:
        return {"status": "error", "message": f"User '{user_id}' already exists or could not be created"}

@app.get("/users")
def list_users():
    """
    Get a list of all users in the system.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, created_at FROM users ORDER BY created_at")
    users = [{"user_id": row[0], "created_at": row[1]} for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    # Use custom encoder to handle date objects
    return JSONResponse(content=json.loads(json.dumps(users, cls=CustomJSONEncoder)),
                        media_type="application/json")

@app.get("/users/{user_id}/preferences")
def get_user_preferences_endpoint(user_id: str):
    """
    Get the preferences for a specific user.
    """
    preferences = get_user_preferences(user_id)
    if not preferences:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return preferences

@app.post("/users/{user_id}/preferences")
def update_user_preferences(user_id: str, preferences: dict = Body(...)):
    """
    Update preferences for a specific user.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if user exists
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    
    # Extract preference values
    taste_profile = preferences.get("taste_profile")
    effort_tolerance = preferences.get("effort_tolerance")
    liked_ingredients = preferences.get("liked_ingredients")
    disliked_ingredients = preferences.get("disliked_ingredients")
    preferred_dish_types = preferences.get("preferred_dish_types")
    dietary_restrictions = preferences.get("dietary_restrictions")
    
    # Build update query dynamically based on provided fields
    updates = []
    params = [user_id]  # Start with user_id for WHERE clause
    
    if taste_profile is not None:
        updates.append("taste_profile = %s")
        params.append(json.dumps(taste_profile))
        
    if effort_tolerance is not None:
        updates.append("effort_tolerance = %s")
        params.append(effort_tolerance)
        
    if liked_ingredients is not None:
        updates.append("liked_ingredients = %s")
        params.append(json.dumps(liked_ingredients))
        
    if disliked_ingredients is not None:
        updates.append("disliked_ingredients = %s")
        params.append(json.dumps(disliked_ingredients))
        
    if preferred_dish_types is not None:
        updates.append("preferred_dish_types = %s")
        params.append(json.dumps(preferred_dish_types))
        
    if dietary_restrictions is not None:
        updates.append("dietary_restrictions = %s")
        params.append(json.dumps(dietary_restrictions))
    
    if updates:
        # Add last_updated to the updates
        from datetime import datetime
        updates.append("last_updated = %s")
        params.append(datetime.now())
        
        # Construct the final query string
        query = f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = %s"

        # --- Fix parameter order ---
        # Parameters for SET clauses should come first, then user_id for WHERE
        query_params = params[1:] + [params[0]]
        # --- End of fix ---

        # Execute the update with corrected parameter order
        cur.execute(query, query_params)
        
        if cur.rowcount == 0:
            # User exists but preferences don't - create them
            taste_profile = taste_profile or {}
            effort_tolerance = effort_tolerance or "moderate"
            liked_ingredients = liked_ingredients or []
            disliked_ingredients = disliked_ingredients or []
            preferred_dish_types = preferred_dish_types or []
            dietary_restrictions = dietary_restrictions or {}
            
            cur.execute("""
                INSERT INTO user_preferences 
                (user_id, taste_profile, effort_tolerance, liked_ingredients, 
                disliked_ingredients, preferred_dish_types, dietary_restrictions, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                user_id,
                json.dumps(taste_profile),
                effort_tolerance,
                json.dumps(liked_ingredients),
                json.dumps(disliked_ingredients),
                json.dumps(preferred_dish_types),
                json.dumps(dietary_restrictions)
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "message": f"Preferences for user '{user_id}' updated successfully"}
    else:
        cur.close()
        conn.close()
        return {"status": "error", "message": "No preference fields provided for update"}

@app.post("/inventory/sync")
def trigger_inventory_sync():
    changed = sync_inventory()
    return {"synced": changed}

@app.get("/inventory")
def get_current_inventory():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT product_id, name, amount, best_before_date, last_updated FROM inventory")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    inventory = [
        {
            "product_id": r[0],
            "name": r[1],
            "amount": r[2],
            "best_before_date": r[3],
            "last_updated": r[4]
        } for r in rows
    ]
    # Use custom encoder to handle date objects
    return JSONResponse(content=json.loads(json.dumps(inventory, cls=CustomJSONEncoder)),
                        media_type="application/json")

def get_user_preferences(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # Select taste_profile, effort_tolerance, and dietary_restrictions
    cur.execute("SELECT taste_profile, effort_tolerance, dietary_restrictions FROM user_preferences WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {
            "taste_profile": row[0] if row[0] else {},
            "effort_tolerance": row[1],
            "dietary_restrictions": row[2] if row[2] else {}
        }
    # Default if no prefs found
    return {
        "taste_profile": {},
        "effort_tolerance": "moderate",
        "dietary_restrictions": {}
    }

@app.post("/ai/suggest-recipes")
def ai_suggest_recipes(
    payload: dict = Body(default={}),
    use_ai_filtering: bool = Query(True, description="Use AI to filter non-food items from inventory"),
    max_ingredients: int = Query(20, description="Maximum number of ingredients to use for recipe search"),
    max_ready_time: int = Query(None, description="Maximum preparation time in minutes")
):
    user_id = payload.get("user_id", "alyssa") # Default to 'alyssa' for now
    user_preferences = get_user_preferences(user_id)
    override = payload.get("inventory_override")
    simplified = payload.get("simplified", False)
    
    # Fetch recipes with optional filtering
    recipes = suggest_recipes_with_classification(
        user_preferences=user_preferences,
        inventory_override=override,
        use_ai_filtering=use_ai_filtering,
        max_ingredients=max_ingredients,
        max_ready_time=max_ready_time
    )
    
    # Format the recipes for better readability
    if recipes:
        from app.recipes import format_recipe_output
        formatted_recipes = format_recipe_output(recipes)
        
        # Apply simplification if requested (for lightweight results)
        if simplified:
            simplified_recipes = []
            for recipe in formatted_recipes:
                simplified_recipes.append({
                    "id": recipe.get("id"),
                    "title": recipe.get("title"),
                    "image": recipe.get("image"),
                    "readyInMinutes": recipe.get("readyInMinutes"),
                    "servings": recipe.get("servings"),
                    "fit_score": recipe.get("fit_score"),
                    "sourceUrl": recipe.get("sourceUrl")
                })
            return simplified_recipes
        
        return formatted_recipes
    
    return []

@app.post("/feedback/submit")
def submit_feedback(payload: dict = Body(...)):
    user_id = payload.get("user_id")
    recipe_id = payload.get("recipe_id")
    rating = payload.get("rating")
    review_text = payload.get("review_text")
    if not all([user_id, recipe_id, rating, review_text]):
        return {"status": "error", "message": "Missing required fields."}
    parsed = handle_feedback(user_id, recipe_id, rating, review_text)
    return {"status": "success", "parsed": parsed}
