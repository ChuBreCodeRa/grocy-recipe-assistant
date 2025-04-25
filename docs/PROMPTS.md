
# Prompt Templates

This document captures the prompt engineering strategies used with GPT-4.1-Nano for the Grocy AI Recipe Assistant.

---

## 1. Ingredient Classification Prompt

**Purpose**: Classify recipe ingredients as Essential, Important, or Optional relative to a specific recipe and user's inventory.

**Prompt Template**:

```
You are a culinary assistant.

Given a recipe, classify each ingredient as:
- Essential: Defines the dish; cannot omit.
- Important: Strongly affects flavor or texture.
- Optional: Can be omitted with little impact.

Also mark whether the user has this ingredient.

Output strictly as JSON array:
[
  {
    "ingredient": "ingredient name",
    "category": "Essential | Important | Optional",
    "in_inventory": true | false,
    "confidence": 0.0 to 1.0
  },
  ...
]

Recipe: {recipe_name}
Instructions: {instructions}
Ingredients: {ingredients_list}
User Inventory: {user_inventory_list}
```

**Expected Output**: Well-structured JSON for backend ingestion.

---

## 2. Review Parsing Prompt

**Purpose**: Parse freeform user reviews to extract effort perception, flavor tags, and overall sentiment.

**Prompt Template**:

```
You are a meal review interpreter.

Task: Parse a user's natural language review of a meal to extract:
- Effort perception: "easy", "moderate", or "hard"
- Primary flavor tags: e.g., "spicy", "savory", "sweet", "bland"
- Overall sentiment: "positive", "neutral", or "negative"

Respond strictly in JSON format:
{
  "effort_tag": "...",
  "flavor_tags": ["...", "..."],
  "sentiment": "..."
}

Review: {review_text}
```

**Expected Output**: Structured JSON that feeds into the daily preference update logic.

---

## Versioning Strategy

- Prompts should be versioned in source control.
- Changes should be treated with caution as they impact feedback loops.
- Major updates to prompts must trigger a minor system version bump.

---

## Related Documents

- [[SYSTEM_OVERVIEW]]
- [[API_REFERENCE]]
- [[DB_SCHEMA]]
- [[USER_REQUIREMENTS]]
