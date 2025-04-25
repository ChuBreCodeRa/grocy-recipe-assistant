
# API Reference

This document outlines the main endpoints exposed by the Grocy AI Recipe Assistant backend.

## Base URL

- Local Development: `http://localhost:8000/`
- (Future) Deployment: To be configured

---

## Endpoints

### 1. POST `/ai/suggest-recipes`

**Description**:  
Generates recipe suggestions based on real-time inventory, user preferences, and Spoonacular recipe discovery.

**Request Body**:
```json
{
  "inventory_override": ["chicken", "garlic", "rice"] // Optional. Use to manually override Grocy inventory.
}
```

**Response**:
```json
[
  {
    "recipe_name": "Garlic Tuna Pasta",
    "score": 0.92,
    "labels": ["You Can Make This"],
    "missing_ingredients": ["olive oil"],
    "classified_ingredients": [
      {"ingredient": "pasta", "category": "Essential", "confidence": 0.95}
    ]
  }
]
```

**Notes**:
- Defaults to fetching real Grocy inventory if `inventory_override` is not provided.
- Returns top 1–2 ranked recipes by score.

---

### 2. POST `/feedback/submit` (Planned)

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
  "message": "Feedback received and processing started."
}
```

**Notes**:
- Triggers AI parsing to extract effort, flavor, and sentiment from freeform reviews.
- Parsed data stored into user preference update queue.

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
