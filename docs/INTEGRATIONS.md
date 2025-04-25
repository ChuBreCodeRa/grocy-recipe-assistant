
# Integrations Overview

This document outlines how the Grocy AI Recipe Assistant integrates with external systems including Grocy, Spoonacular, OpenAI, and Home Assistant.

**Status**: Integration design complete. Implementation pending.

---

## 1. Grocy API

**Purpose**: Provide real-time inventory information.

**Endpoints Used**:
- `GET /stock`: Returns all current products in stock

**Notes**:
- Requires `GROCY-API-KEY` in headers
- Data is normalized into a flat list of available ingredients

---

## 2. Spoonacular API

**Purpose**: Source recipes based on inventory and manage meal history.

**Endpoints Used**:
- `GET /recipes/complexSearch`: Returns recipes based on available ingredients
- `GET /recipes/{id}/information`: Retrieves full instructions, tags, etc.
- `GET /recipes/{id}/tasteWidget.json`: Gets structured flavor profiles
- `POST /mealplanner/{username}/items` (planned): Add recipe to user's meal planner

**Authentication**:
- Requires API key in `apiKey` query parameter

**Notes**:
- Will eventually serve as persistent meal history source

---

## 3. OpenAI (GPT-4.1-Nano)

**Purpose**:
- Classify ingredient importance
- Parse user reviews into effort, flavor, and sentiment

**Endpoint**:
- `POST /v1/responses` via `client.responses.create()`

**Prompt Templates**:
- See [[PROMPTS]]

**Security**:
- API key stored in `.env`, not committed

---

## 4. Home Assistant

**Purpose**: Provide user interface for triggering recipe suggestions and submitting feedback.

**Interactions**:
- User says: “Hey Google, I don’t know what to eat.”
- Home Assistant sends webhook to backend
- Backend returns top 1–2 suggestions
- (Planned) Home Assistant prompts for feedback post-meal

**Security**:
- Local network only; optional HTTPS via NGINX proxy in future

---

## Future Considerations

- Optional integration with Home Assistant calendar for scheduled meal prompts
- Optional integration with Grocy product expiry dates for inventory prioritization

---

## Related Documents

- [[SYSTEM_OVERVIEW]]
- [[API_REFERENCE]]
- [[PROMPTS]]
- [[SECURITY]]
