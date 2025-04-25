
# Project Roadmap

This document outlines the planned future phases for the Grocy AI Recipe Assistant project.  
**Status: In Discovery and Planning Phase**

---

## Phase 0 - Discovery & Requirements Gathering (Current)

- Define user personas (Alyssa, Brendan)
- Clarify core goals: reduce decision fatigue, build trust, enhance enjoyment
- Document all architecture decisions
- Gather API capabilities (Grocy, Spoonacular, OpenAI)
- Design scoring engine architecture
- Design user feedback and learning loop
- Create full production-ready documentation scaffold

---

## Phase 1 - Core System Architecture (Upcoming)

- Build FastAPI backend service
- Connect to Grocy to retrieve real-time inventory
- Connect to Spoonacular ComplexSearch for recipe discovery
- Integrate GPT-4.1-Nano for:
  - Ingredient classification
  - Review parsing
- Implement Redis cache layer for API efficiency
- Implement PostgreSQL DB for user preferences and feedback

---

## Phase 2 - Core Feature Development (Planned)

- Build `/ai/suggest-recipes` endpoint
- Build `/feedback/submit` endpoint
- Implement user feedback collection (rating + review)
- Implement daily cron job for profile updates
- Start basic Home Assistant webhook integration for trigger/response

---

## Phase 3 - Core Testing and First Release

- Unit test scoring engine
- Integration test API interactions
- Validate AI output parsing accuracy
- Prepare MVP deployment on local Docker environment

---

## Phase 4 - Expansion and Personalization Enhancements

- Add Spoonacular Meal Planner integration
- Multi-day meal planning based on inventory
- Ingredient expiry prioritization
- Multi-user profile support

---

## Phase 5 - Operational Maturity

- Implement monitoring and basic logging
- Backup preference data
- Improve retry logic on external API failures

---

## Stretch Goals

- Offline recipe fallback with local database
- Fine-tune lightweight LLM for faster local inference
- Browser extension for live inventory-based recipe suggestion

---

## Related Documents

- [[README]]
- [[SYSTEM_OVERVIEW]]
- [[DECISIONS]]
- [[USER_REQUIREMENTS]]
- [[PROJECT_SUMMARY]]
