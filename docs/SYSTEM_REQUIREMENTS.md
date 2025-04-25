
# System Requirements Specification (SRS)

## 1. Purpose

To provide intelligent, inventory-aware recipe suggestions for households, reducing decision fatigue and increasing mealtime satisfaction through AI-driven personalization and integration with Grocy and Spoonacular.

## 2. Scope

This system interfaces with Grocy for real-time inventory, Spoonacular for recipe sourcing and meal planning, and GPT-4.1-Nano for AI personalization. It scores and ranks recipes based on user preferences and feedback, learning continuously from star ratings and natural language reviews.

## 3. Functional Requirements

- F1: Fetch current inventory from Grocy
- F2: Query Spoonacular's complexSearch with available ingredients
- F3: Retrieve full recipe metadata and taste profile
- F4: Use AI to classify ingredient importance
- F5: Score recipes based on flavor, effort, preferences, and inventory match
- F6: Return 1–2 top-ranked personalized suggestions
- F7: Accept user feedback (rating + review)
- F8: Use AI to extract structured data from reviews
- F9: Update user preference profiles daily
- F10: Store user preferences and rating history per person

## 4. Non-Functional Requirements

- N1: Responses must complete in under 3 seconds for typical inventory
- N2: AI classifications must be structured and cacheable
- N3: Privacy-respecting design; no sensitive data leaves the local system
- N4: System must be voice- and mobile-accessible via Home Assistant
- N5: System must handle Spoonacular API rate limits gracefully

## 5. Constraints

- Grocy is used for inventory only—not recipes
- User must have Spoonacular and OpenAI API keys
- Runs in a local environment using Docker and FastAPI

## 6. Assumptions and Dependencies

- Home Assistant is installed and supports webhook integration
- Users are willing to provide natural language feedback post-meal
