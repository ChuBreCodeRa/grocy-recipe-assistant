# System Overview

## High-Level Architecture

Grocy Recipe Assistant is a backend-first service that integrates multiple systems to provide recipe recommendations based on available inventory:

- **Grocy**: Source of truth for inventory data
- **Spoonacular**: Primary source for recipe data and some matching logic
- **OpenAI GPT-4.1-Nano**: Provides ingredient classification, preference parsing, and recipe generation
- **Flask/FastAPI**: REST API backend
- **Redis**: Caching layer for API responses
- **PostgreSQL**: Database for user preferences and history
- **Home Assistant**: Optional frontend integration point

---

## Components

### 1. Inventory Service
- Integrates with Grocy API to fetch current inventory.
- Syncs data to local database for filtering, performance, and reliability.
- Uses AI to identify food ingredients from general inventory items.

### 2. Recipe Service
- Fetches recipe candidates from Spoonacular based on available ingredients.
- Preserves original ingredient names from inventory for accurate matching of meal kits and prepared foods.
- Uses culinary-informed grouping to create logical ingredient combinations.
- Falls back to AI-generated recipes when Spoonacular doesn't provide good matches.
- Classifies ingredients into Essential/Important/Optional and marks availability.

### 3. Scoring Engine
- Ranks recipes based on multi-dimensional fit to user's profile.
- Incorporates preference vectors for taste profile, effort tolerance, and ingredient preferences.
- Considers inventory match, dietary restrictions, and personalization factors.

### 4. Feedback Processor
- Extracts structured data from natural language reviews.
- Uses lightweight AI to parse effort level, flavor tags, and sentiment.
- Maintains user preference profiles that evolve over time.

### 5. User Profile Service
- Stores individual preference data.
- Handles dietary restrictions, taste preferences, effort tolerance.
- Updates daily via cron-based preference learning cycle.

### 6. Redis
- Cache layer for AI responses and API lookups.
- Minimizes external API calls for speed and cost efficiency.

### 7. PostgreSQL
- Stores user profiles, preferences, rating history, and review outputs.

---

## Key Data Flow

1. **Inventory Processing**:
   - Inventory data retrieved from Grocy → Filtered to food ingredients → Stored in local DB
   - Ingredient combinations created using culinary knowledge or AI guidance

2. **Recipe Suggestion**:
   - Inventory ingredients → Spoonacular Complex Search → Return candidate recipes
   - If no good matches, AI generates custom recipes from available ingredients
   - Recipes classified and scored → Returned to user

3. **Feedback Loop**:
   - User rates and writes mini-review → AI parses effort/flavor/sentiment
   - User profile updated daily → Influences next recommendations

---

## AI-Assisted Elements [[PROMPTS]]

1. **Ingredient Filtering**: Identifies food items in inventory without generalizing them.

2. **Ingredient Classification**: Labels recipe ingredients as Essential, Important, or Optional.

3. **Ingredient Matching**: Marks which recipe ingredients are present in inventory with exact and fuzzy matching.

4. **Recipe Generation**: Creates full recipes with instructions when Spoonacular doesn't return good matches.

5. **Review Parsing**: Extracts effort level, flavor descriptors, and sentiment from natural language reviews.

6. **Preference Inference**: Updates user preference vectors based on review history.

---

## Performance Optimizations [[PERFORMANCE]]

1. **Redis Caching**: All API responses and AI responses are cached.

2. **Local DB Sync**: Grocy inventory stored locally to minimize API calls.

3. **Batched API Processing**: Recipe calls are batched to minimize Spoonacular API quota usage.

4. **Structured Prompting**: All AI calls use structured prompts to minimize token usage.

5. **JSON Response Handling**: Multiple fallback strategies for parsing potentially malformed AI-generated JSON.

---

## Recent Enhancements

### 1. Original Ingredient Preservation

We've updated the system to preserve exact ingredient names throughout the processing pipeline:

- Modified AI filtering prompt to explicitly keep original names rather than generalizing them
- Enhanced inventory ingredient handling to maintain specificity for meal kits and prepared foods
- Updated matching algorithms to handle original names while still finding relevant recipes

### 2. Culinary-Aware Ingredient Combinations

Improved ingredient grouping with real culinary knowledge:

- Added understanding of classic meal structures (protein + starch + vegetable)
- Implemented special handling for prepared foods and meal kits
- Created more logical ingredient groupings based on cooking principles
- Enhanced AI prompts to respect original names and create sensible combinations

### 3. AI Recipe Generation Fallback

Added AI-based recipe creation when Spoonacular can't find good matches:

- Automatically generates custom recipes using available ingredients when:
  - Spoonacular returns no matches for the ingredients
  - The best recipe match has a fit score of 10% or lower
- Format matches Spoonacular's structure for consistent handling
- Enhanced error handling with multiple JSON parsing fallbacks
- Recipes respect dietary restrictions and time constraints

---

## Related Docs

- [[API_REFERENCE]]
- [[DECISIONS]]
- [[DB_SCHEMA]]
- [[PROMPTS]]
- [[INGREDIENT_HANDLING]]
- [[AI_RECIPE_GENERATION]]
