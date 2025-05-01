# Onboarding Guide

This guide outlines how a new user (such as Alyssa) would interact with the Grocy AI Recipe Assistant for the first time, and what setup or understanding is required.

**Status**: Drafted for post-launch implementation.

---

## 1. Setup (Handled by Technical Owner)

- Grocy is configured and running with accurate kitchen inventory.
- Spoonacular API key is obtained and stored in `.env`.
- OpenAI API key is stored in `.env`.
- Home Assistant is configured to send a webhook to the backend.
- User profiles (`alyssa`, `brendan`) are added manually to the system.
- Redis is now required for caching AI and API responses. It is included in Docker Compose and requires no manual setup for local development.
- Ensure your `.env` file includes any custom Redis settings if you are not using the default Docker Compose setup.

---

## 2. First Interaction

User says:
> “Hey Google, I don’t know what to eat.”

System will:

1. Query Grocy for inventory.
2. Send ingredient list to Spoonacular.
3. Score 5–10 candidate recipes using AI and personal profile.
4. Reply with top 1–2 suggestions via Home Assistant.

Response Example:
> “How about Cheesy Tuna Pasta? You’ve got everything you need, and it matches your preferences.”

---

## 3. Giving Feedback

After dinner, the system (or user manually) triggers feedback flow:

> “How was dinner?”

User replies with:
- Star rating (1–5)
- Mini-review (e.g. “Tasty but a little too spicy and time consuming”)

The AI parses this feedback and updates the user’s preferences overnight.

---

## 4. Viewing Your Preferences (Planned)

Users may eventually be able to:
- View their current flavor profile
- See most-liked and least-liked ingredients
- Review feedback history

---

## 5. Tips

- Try interacting with different phrasing to find your preferred way of asking.
- Don't worry about tagging ingredients or effort—just speak normally. The AI handles it.
- If no suggestions are given, ensure Grocy inventory isn’t empty or expired.

---

## Related Documents

- [[USER_REQUIREMENTS]]
- [[PROMPTS]]
- [[SYSTEM_OVERVIEW]]
