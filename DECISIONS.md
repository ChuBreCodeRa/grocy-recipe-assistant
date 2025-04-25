
# Architecture Decision Records [[SYSTEM_OVERVIEW]]

This document logs the key technical and strategic choices made during the design and early implementation of the Grocy AI Recipe Assistant.

## 1. AI Usage Strategy

**Decision**: Use GPT-4.1-Nano with strict, verbose prompting.

**Reason**: To maximize reliability and structured outputs from a lightweight, affordable model.

**Tradeoff**: Heavier prompting templates, but extremely consistent results.

---

## 2. Recipe Sourcing

**Decision**: Use Spoonacular's ComplexSearch and Meal Planner APIs for recipe discovery and storage.

**Reason**: Spoonacular provides mature ingredient matching, taste profiling, and persistent recipe management, while Grocy’s recipe system was deemed too inflexible.

**Tradeoff**: Reliance on an external service for recipes. Must respect rate limits and API availability.

---

## 3. Inventory Source

**Decision**: Use Grocy strictly for inventory, not for meal or recipe storage.

**Reason**: Grocy offers real-time stock data but lacks a scalable or flexible meal planner.

---

## 4. Scoring Logic Strategy

**Decision**: Manual weighted scoring logic with AI-assist.

**Reason**: Maintain transparency, control, and future extensibility while leveraging AI to classify but not score.

---

## 5. User Feedback Strategy

**Decision**: Only require star rating + natural language mini-reviews. No manual tag selection.

**Reason**: Minimize friction, build trust, maintain user simplicity.

---

## 6. Learning Strategy

**Decision**: Update user preferences daily via a cron job.

**Reason**: Smooth preference changes, avoid overfitting to one-off experiences.

---

## 7. Storage Model for Preferences

**Decision**: Maintain local user profile (liked ingredients, flavor profile, effort tolerance) separate from Spoonacular meal planner.

**Reason**: Full portability, control, and transparent AI-driven learning.

---

## Related Docs

- [[README]]
- [[SYSTEM_OVERVIEW]]
- [[USER_REQUIREMENTS]]
