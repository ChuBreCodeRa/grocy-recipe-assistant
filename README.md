# Grocy AI Recipe Assistant

## Overview

The Grocy AI Recipe Assistant intelligently suggests meals you can prepare based on your real-time kitchen inventory.
It combines Grocy's inventory management, Spoonacular's recipe database, and GPT-4.1-Nano personalization to help reduce decision fatigue, build trust, and improve meal enjoyment.

Users interact naturally—primarily through voice ("Hey Google, what should I make?")—and the system learns their preferences over time through star ratings and short natural language reviews.

## Core Goals

- Reduce daily mealtime decision fatigue.
- Build personalized meal suggestions based on real inventory, tastes, and effort tolerance.
- Create a trust-building system that improves over time with minimal user effort.
- Keep all AI interactions structured, transparent, and adaptable.

## Features

- **Real-time Inventory Fetching**: Pulls inventory from Grocy automatically.
- **Spoonacular ComplexSearch Integration**: Finds recipes based on current kitchen inventory.
- **AI-Powered Classification**: GPT-4.1-Nano classifies ingredient importance, effort level, and flavor profile.
- **Custom Scoring Engine**: Recipes ranked by flavor match, effort match, ingredient availability, and user preference.
- **Natural Feedback Loop**: Users provide star ratings + freeform mini-reviews; AI extracts effort, flavor, and sentiment tags.
- **User Profiles**: Per-user preferences for flavor, effort, ingredient likes/dislikes, and dietary restrictions are continuously updated.
- **Dietary Restrictions Support**: Filter recipes by diet type (vegetarian, vegan, etc.) and food intolerances.
- **Daily Preference Updates**: Cron job refreshes user profiles based on recent reviews.
- **Voice Assistant Integration**: Trigger suggestions via Home Assistant.
- **User Management**: Create and manage user profiles with customizable preferences.
- **Manual Inventory Sync**: Trigger a sync from Grocy with `POST /inventory/sync`.
- **Inventory API**: Fetch current inventory from the local database with `GET /inventory`.
- **Redis Caching**: Caches AI and API responses for performance and cost efficiency. Redis is now required and runs as a service in Docker Compose.

## Tech Stack

- Backend: FastAPI + Redis + PostgreSQL
- AI Integration: OpenAI API (GPT-4.1-Nano model)
- Recipe Source: Spoonacular API
- Inventory Management: Grocy API
- Voice Assistant: Home Assistant webhook integration
- Dockerized: Full container-based deployment

## Setup Instructions

1. Clone this repository.
2. Copy `.env.example` to `.env` and fill in:
    - OpenAI API Key
    - Spoonacular API Key
    - Grocy URL + API Key
3. Install Docker and Docker Compose.
4. Run:

    docker-compose up --build

5. Access backend API at `http://localhost:8000`.

## User Management

The system supports multiple users with individual preferences:

1. Create a new user: `POST /users/create` with a unique user_id
2. Update preferences: `POST /users/{user_id}/preferences`
3. Get preferences: `GET /users/{user_id}/preferences`
4. List all users: `GET /users`

## Dietary Restrictions

Users can specify dietary preferences that filter recipe suggestions:

- **Diet Types**: vegetarian, vegan, pescetarian, gluten-free, ketogenic, paleo
- **Intolerances**: dairy, egg, gluten, grain, peanut, seafood, sesame, shellfish, soy, sulfite, tree nut, wheat

Example preference update:
```json
{
  "dietary_restrictions": {
    "diet": "vegetarian",
    "intolerances": ["shellfish", "dairy"]
  }
}
```

## Project Status

- Core architectural design complete.
- Documentation scaffolded and filled.
- Prompting and feedback pipeline defined.
- User management and dietary restrictions implemented.
- Development phase initiated.

## Related Documents

- [[SYSTEM_OVERVIEW]]
- [[DECISIONS]]
- [[USER_REQUIREMENTS]]
- [[API_REFERENCE]]

### Environment Variables

- `REDIS_HOST` (default: `redis`)
- `REDIS_PORT` (default: `6379`)
- `REDIS_DB` (default: `0`)
