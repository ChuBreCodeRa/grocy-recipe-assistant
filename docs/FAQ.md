
# Frequently Asked Questions

This FAQ covers common concerns and potential questions from end users and developers working with the Grocy AI Recipe Assistant.

---

## User Questions

### What if I don’t like the suggestions?
The system only shows 1–2 suggestions to reduce decision fatigue, but you can ask again or override inventory to try different results. Over time, the system will learn your preferences.

### How does it know what I like?
After each meal, you can rate the recipe and leave a short review. The system uses AI to analyze that review and update your flavor, effort, and ingredient preferences.

### Do I have to choose tags when I give feedback?
No. You just write a short sentence about your experience. The AI handles classification.

### Can I see my profile or preferences?
This is not available in the first release, but it may be added later as a local dashboard or Home Assistant card.

### What if I don’t have everything for the recipe?
Recipes are scored based on your inventory. If you’re only missing optional ingredients, you’ll still get the suggestion. If something essential is missing, it’ll either be flagged or excluded.

---

## Developer Questions

### Can I run this entirely offline?
Not initially. It relies on:
- OpenAI API for classification
- Spoonacular API for recipes
Grocy and Home Assistant can run locally. Future versions may support local AI.

### How do I add new users?
Create a new entry in the `users` and `user_preferences` tables. You'll need to trigger a feedback cycle to initialize meaningful data.

### How does scoring work?
Scoring blends inventory match, user preferences, flavor alignment, effort level, and recency. The exact weights are documented in [[DECISIONS]] and applied in the backend.

### What’s the upgrade plan?
Future plans include a lightweight local model, multi-user calendar sync, and richer feedback visualization.

---

## Related Documents

- [[USER_REQUIREMENTS]]
- [[PROJECT_SUMMARY]]
- [[PROMPTS]]
- [[DECISIONS]]
