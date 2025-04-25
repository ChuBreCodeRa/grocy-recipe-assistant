
# System Overview

## High-Level Architecture

Voice Trigger (Home Assistant) → Backend (FastAPI App) → Inventory/Recipe APIs → AI Layer → Personalized Suggestions → Home Assistant Output

---

## Components

### 1. Home Assistant [[README]]
- Primary user interaction surface.
- Sends webhook request to backend when user asks for meal suggestions.

### 2. Backend - FastAPI [[README]]
- Central API server.
- Fetches inventory from Grocy.
- Queries Spoonacular for recipe discovery.
- Sends recipes and user profiles to AI classification pipeline.
- Applies custom scoring logic to rank recipes.

### 3. Grocy API
- Source of real-time kitchen inventory.
- Only used for stock/ingredient management, not recipes.

### 4. Spoonacular API
- ComplexSearch used to discover recipes based on available ingredients.
- Meal Planner used to log and reference meals historically.
- Taste Widget used to retrieve structured flavor profiles.
- Similarity searches for unwanted recipes

### 5. OpenAI API (GPT-4.1-Nano)
- Ingredient classification: Essential / Important / Optional.
- Review analysis: Extract effort, flavor, and sentiment from mini-reviews.
- Outputs structured JSON for system consumption.

### 6. Redis
- Cache layer for AI responses and API lookups.
- Minimizes external API calls for speed and cost efficiency.

### 7. PostgreSQL
- Stores user profiles, preferences, rating history, and review outputs.

---

## Key Data Flow

1. Home Assistant triggers suggestion flow via webhook.
2. Backend fetches latest inventory from Grocy.
3. Inventory list sent to Spoonacular complexSearch endpoint.
4. 5–10 recipe candidates returned.
5. GPT-4.1-Nano classifies ingredients and tags recipes.
6. Backend applies custom weighted scoring model.
7. Top 1–2 recipes are returned to Home Assistant for user interaction.

---

## AI-Assisted Elements [[PROMPTS]]
- Ingredient classification at recipe time.
- Review parsing after meals.
- Optional future flavor matching using historical data.

---

## Related Docs

- [[README]]
- [[DECISIONS]]
- [[USER_REQUIREMENTS]]
