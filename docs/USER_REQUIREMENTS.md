
# User Requirements Document

## 1. User Personas

**Alyssa** – Primary user. A busy mom who wants meal suggestions that are quick, enjoyable, and easy to decide on. Prefers voice-based interactions with minimal friction.

**Brendan** – Builder and secondary user. Technical, focused on system operation, efficiency, and user satisfaction. Also interacts via voice and dashboard triggers.

## 2. Goals and Motivations

- **Primary Goal**: Reduce decision fatigue surrounding daily meal planning.
- Build trust by offering genuinely useful, customized suggestions.
- Continuously improve the system through lightweight, natural user feedback.
- Surface recipes that match available inventory, effort tolerance, and flavor preferences.

## 3. Functional Requirements

- Fetch real-time inventory from Grocy.
- Query Spoonacular recipes based on available ingredients.
- Score recipes by flavor match, inventory match, effort suitability, and personal history.
- Classify ingredient importance via AI.
- Accept post-meal user ratings and freeform reviews.
- Use AI to parse reviews into structured preference updates.
- Update user preference profiles daily without manual intervention.
- Cache AI and API responses where possible for efficiency.

## 4. Interaction Flows

### Meal Suggestion Flow
- User triggers "What's for dinner?" via Home Assistant voice command.
- System retrieves inventory, queries Spoonacular, scores recipes.
- System returns 1–2 top suggestions, explained briefly.

### Feedback Flow
- After eating, user is prompted: "How was dinner?"
- User rates from 1–5 stars and optionally writes a short review.
- AI parses review automatically; preferences update overnight.

## 5. Trust-Building Requirements

- Explanations are provided for recipe suggestions.
- No assumptions or feedback guessing without explicit input.
- Suggestions prioritize ingredient availability and user flavor preference.
- System should not overrepeat recipes unless highly rated.

## 6. Feedback and Adaptation

- Feedback input is lightweight (rating + natural review).
- No mandatory tag selection by users.
- Flavor preferences, effort tolerance, and ingredient likes/dislikes adapt automatically.
- Historical influence decays slightly to avoid overfitting on old preferences.

## Related Documents

- [[README]]
- [[SYSTEM_OVERVIEW]]
- [[DECISIONS]]
- [[PROJECT_SUMMARY]]
