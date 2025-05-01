# API Reference

This document provides a detailed reference of all endpoints available in the Grocy AI Recipe Assistant API.

## Authentication

No authentication is required for development purposes. In production, you would use API keys or another authentication method.

## Base URL

For local development: `http://localhost:8000`

## Endpoints

### 1. Recipe Suggestions

#### POST `/ai/suggest-recipes`

**Description**:  
Suggests recipes based on available inventory items, filtered by AI to identify food ingredients. Uses intelligent ingredient combinations to find the best matching recipes.

**Request Body**:
```json
{
  "user_id": "alyssa",
  "inventory_override": ["pasta", "cheese", "tomatoes"],
  "simplified": false
}
```

**Query Parameters**:  
- `use_ai_filtering`: (boolean, default: `true`) Whether to use AI to filter non-food items from inventory
- `max_ingredients`: (integer, default: `20`) Maximum number of ingredients to include in recipe search 
- `max_ready_time`: (integer, optional) Maximum recipe preparation time in minutes

**Response**:  
Default format (with detailed recipe information):
```json
[
  {
    "id": 654959,
    "title": "Pasta With Tuna",
    "image": "https://spoonacular.com/recipeImages/654959-556x370.jpg",
    "readyInMinutes": 20,
    "servings": 4,
    "sourceUrl": "http://www.foodista.com/recipe/DMXBRSGT/pasta-with-tuna",
    "fit_score": {
      "percentage": 66.7,
      "have": 2,
      "need_to_buy": 1,
      "total": 3
    },
    "ingredients": {
      "have": [
        {
          "name": "pasta",
          "amount": "1 pound"
        },
        {
          "name": "canned tuna",
          "amount": "6 ounces"
        }
      ],
      "need_to_buy": [
        {
          "name": "fresh parsley",
          "amount": "0.25 cup"
        }
      ]
    },
    "summary": "Recipe summary text...",
    "instructions": "Step-by-step instructions..."
  }
]
```

Simplified format (when `simplified=true`):
```json
[
  {
    "id": 654959,
    "title": "Pasta With Tuna",
    "image": "https://spoonacular.com/recipeImages/654959-556x370.jpg",
    "readyInMinutes": 20,
    "servings": 4,
    "fit_score": {
      "percentage": 66.7,
      "have": 2,
      "need_to_buy": 1,
      "total": 3
    },
    "sourceUrl": "http://www.foodista.com/recipe/DMXBRSGT/pasta-with-tuna"
  }
]
```

**Notes**:  
- Uses AI to intelligently group ingredients into meaningful combinations for better recipe matches
- Results are sorted by fit score (how well the recipe matches available ingredients)
- When `user_id` is provided, dietary restrictions and preferences will be applied
- Empty response array `[]` means no matching recipes were found
- The `inventory_override` parameter is optional and can be used for testing
- Use `simplified=true` for lightweight results suitable for list views

### 2. Inventory Management

#### POST `/inventory/sync`

**Description**:  
Triggers a manual synchronization from Grocy API to the local database.

**Response**:
```json
{
  "synced": true|false
}
```

**Notes**:
- Syncs all inventory items from Grocy, maintaining a local copy for quick access.
- Optimized to only sync when changes are detected.

#### GET `/inventory`

**Description**:  
Returns the current inventory from the local database.

**Response**:
```json
[
  {
    "product_id": 123,
    "name": "Chicken Breast",
    "amount": 2,
    "best_before_date": "2025-05-01",
    "last_updated": "2025-04-26T12:00:00"
  }
]
```

### 3. User Preferences

#### POST `/users/create`

**Description**:  
Creates a new user in the system with optional preference settings.

**Request Body**:
```json
{
  "user_id": "username123", // Required
  "taste_profile": { // Optional
    "sweetness": 50,
    "saltiness": 60,
    "sourness": 30,
    "bitterness": 20,
    "savoriness": 80,
    "fattiness": 40
  },
  "effort_tolerance": "moderate", // Optional, defaults to "moderate"
  "liked_ingredients": ["chicken", "garlic"], // Optional
  "disliked_ingredients": ["cilantro"], // Optional
  "preferred_dish_types": ["main course", "dinner"] // Optional
}
```

**Response**:
```json
{
  "status": "success",
  "message": "User 'username123' created successfully"
}
```

#### GET `/users`

**Description**:  
Returns a list of all users in the system.

**Response**:
```json
[
  {
    "user_id": "alyssa",
    "created_at": "2025-03-15T12:30:45"
  },
  {
    "user_id": "brendan",
    "created_at": "2025-03-16T10:15:20"
  }
]
```

#### GET `/users/{user_id}/preferences`

**Description**:  
Gets the preferences for a specific user.

**Response**:
```json
{
  "taste_profile": {
    "sweetness": 50,
    "saltiness": 60,
    "sourness": 30,
    "bitterness": 20,
    "savoriness": 80,
    "fattiness": 40
  },
  "effort_tolerance": "moderate"
}
```

**Notes**:
- Returns 404 if user is not found

#### POST `/users/{user_id}/preferences`

**Description**:  
Updates preferences for a specific user.

**Request Body**:
```json
{
  "taste_profile": {
    "sweetness": 40,
    "saltiness": 70,
    "sourness": 30,
    "bitterness": 10,
    "savoriness": 90,
    "fattiness": 40
  },
  "effort_tolerance": "hard",
  "dietary_restrictions": {
    "diet": "vegetarian",
    "intolerances": ["shellfish", "dairy"]
  }
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Preferences for user 'username123' updated successfully"
}
```

**Notes**:
- Returns 404 if user is not found
- Only specified fields will be updated; omitted fields remain unchanged
- If the user exists but has no preferences yet, a preferences record will be created
- Supported diet types include: vegetarian, vegan, pescetarian, gluten-free, ketogenic, paleo
- Supported intolerances include: dairy, egg, gluten, grain, peanut, seafood, sesame, shellfish, soy, sulfite, tree nut, and wheat

### 4. Feedback

#### POST `/feedback/submit`

**Description**:  
Accepts post-meal user feedback to update preference profiles.

**Request Body**:
```json
{
  "user_id": "alyssa",
  "recipe_id": "123456",
  "rating": 4,
  "review_text": "Tasty, but a little too spicy."
}
```

**Response**:
```json
{
  "status": "success",
  "parsed": {
    "effort_tag": "moderate",
    "sentiment": "positive",
    "taste_profile": {
      "sweetness": 20,
      "saltiness": 65,
      "sourness": 10,
      "bitterness": 5,
      "savoriness": 75,
      "fattiness": 40
    }
  }
}
```

**Notes**:
- Triggers AI parsing to extract effort level, sentiment, and taste profile from freeform reviews.
- Automatically updates user preferences based on this feedback.
- Uses the latest GPT-4.1-Nano model to analyze review text.

---

## Advanced Spoonacular API Parameters

Our recipe suggestion system uses the Spoonacular API's complexSearch endpoint. While we've implemented the most important features for our use case, the API offers many additional filtering options that could be incorporated in future updates:

### Dietary Restrictions
- `diet`: Filter by dietary requirements (vegetarian, vegan, gluten-free, etc.)
- `intolerances`: Filter out recipes with specific allergens
- `excludeIngredients`: Specify ingredients to exclude

### Recipe Type Filters
- `type`: Filter by meal type (main course, appetizer, dessert, etc.)
- `cuisine`: Filter by cuisine type (Italian, Asian, Mediterranean, etc.)
- `excludeCuisine`: Exclude specific cuisines

### Recipe Complexity
- `maxReadyTime`: Maximum preparation time in minutes
- `minServings`/`maxServings`: Serving size requirements
- `equipment`: Required kitchen equipment

### Nutritional Filters
Numerous nutritional filters are available, including:
- `minProtein`/`maxProtein`: Protein content per serving
- `minCalories`/`maxCalories`: Calorie range
- `minFat`/`maxFat`: Fat content
- Various vitamin and mineral filters

### Result Control
- `sort`: Results sorting method (calories, price, time, etc.)
- `sortDirection`: Sort ascending or descending
- `number`: Number of results to return

### Advanced Options
- `instructionsRequired`: Only return recipes with instructions
- `fillIngredients`: Add details about ingredients used/missing
- `addRecipeInformation`: Include detailed recipe information
- `addRecipeNutrition`: Include nutritional information

---

## Response Codes

| Code | Meaning |
|-----|---------|
| 200  | Success |
| 400  | Bad request format |
| 401  | Authentication missing or invalid (future secured endpoints) |
| 500  | Internal server error or external service failure |

---

## Related Docs

- [[README]]
- [[SYSTEM_OVERVIEW]]
- [[DECISIONS]]
- [[USER_REQUIREMENTS]]
