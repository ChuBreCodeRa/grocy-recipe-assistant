
# Project Summary

## Project Title
Grocy AI Recipe Assistant

## Purpose

The Grocy AI Recipe Assistant reduces meal decision fatigue by suggesting meals based on real-time kitchen inventory, learned personal preferences, and minimal user friction. 
It combines Spoonacular’s recipe database, Grocy’s inventory tracking, and GPT-4.1-Nano for intelligent classification and learning.

## Value Proposition

- Personalized, AI-driven meal suggestions.
- Seamless voice-first interaction through Home Assistant.
- Learns and evolves with user feedback automatically.
- Trust-building through transparency and control.

## Tech Stack

- Backend: FastAPI, Redis, PostgreSQL
- Inventory Source: Grocy API
- Recipe Source: Spoonacular API (ComplexSearch, Meal Planner)
- AI Layer: OpenAI API (GPT-4.1-Nano)
- Containerization: Docker Compose setup
- User Interaction: Home Assistant webhook triggers

## Core Features

- Real-time inventory checking.
- Personalized recipe suggestions using inventory, preferences, and flavor profiles.
- User feedback collection via natural language reviews.
- Daily user profile updating and learning loop.
- Cached AI responses for performance.

## Challenges Addressed

- Reducing decision fatigue at mealtimes.
- Building trust through clear and relevant suggestions.
- Evolving preferences without burdensome manual input.

## Status

- Core architecture and system design finalized.
- Documentation fully scaffolded and filled.
- Development phase beginning: preference engine and feedback flow.

## Related Documents

- [[README]]
- [[SYSTEM_OVERVIEW]]
- [[DECISIONS]]
- [[USER_REQUIREMENTS]]
