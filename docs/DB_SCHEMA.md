
# Database Schema

This document outlines the database tables, fields, and relationships for the Grocy AI Recipe Assistant.

---

## Tables

### 1. `users`

| Field     | Type    | Description                         |
|-----------|---------|-------------------------------------|
| `id`      | TEXT (PK) | Unique identifier (e.g., "alyssa") |
| `created_at` | TIMESTAMP | When the user was first added   |

---

### 2. `user_preferences`

| Field                  | Type        | Description                                    |
|-------------------------|-------------|------------------------------------------------|
| `user_id`               | TEXT (FK)   | References `users.id`                         |
| `liked_ingredients`     | JSON        | List of liked ingredients                     |
| `disliked_ingredients`  | JSON        | List of disliked ingredients                  |
| `preferred_flavors`     | JSON        | Flavor preference vector (savory, sweet, etc.)|
| `effort_tolerance`      | TEXT        | "low", "medium", or "high" effort preference  |
| `preferred_dish_types`  | JSON        | Dish types like "soup", "stir fry", etc.       |
| `last_updated`          | TIMESTAMP   | Last time preferences were updated            |

---

### 3. `user_ratings`

| Field            | Type      | Description                                 |
|------------------|-----------|---------------------------------------------|
| `id`             | INTEGER (PK) | Unique auto-incrementing rating id         |
| `user_id`        | TEXT (FK) | References `users.id`                       |
| `recipe_id`      | TEXT      | Spoonacular or internal recipe ID           |
| `rating`         | INTEGER   | Star rating (1–5)                           |
| `review_text`    | TEXT      | User's freeform mini-review                 |
| `effort_tag`     | TEXT      | Parsed by AI (easy, moderate, hard)          |
| `flavor_tags`    | JSON      | Parsed flavor tags (e.g., ["spicy", "savory"]) |
| `sentiment`      | TEXT      | Parsed overall sentiment ("positive", etc.) |
| `timestamp`      | TIMESTAMP | When feedback was submitted                 |

---

### 4. `cached_ai_responses`

| Field            | Type    | Description                          |
|------------------|---------|--------------------------------------|
| `key`            | TEXT (PK) | Composite cache key (e.g., inventory+recipe) |
| `response_json`  | JSON    | Cached GPT response                  |
| `expires_at`     | TIMESTAMP | Expiration time for cache invalidation |

---

## Relationships

- `user_preferences.user_id` → `users.id`
- `user_ratings.user_id` → `users.id`
- `user_ratings.recipe_id` → internal or Spoonacular recipes
- `cached_ai_responses` is standalone, used to improve API speed and reduce cost.

---

## Related Documents

- [[SYSTEM_OVERVIEW]]
- [[API_REFERENCE]]
- [[USER_REQUIREMENTS]]
