
# Background Jobs - Cron Setup

This document describes scheduled background processes that keep user profiles up-to-date and ensure the Grocy AI Recipe Assistant continuously adapts to user feedback.

---

## 1. Daily User Preference Update Job

**Purpose**:  
Analyze new user ratings and reviews, and update per-user preference profiles accordingly.

**Trigger**:  
- Scheduled daily at 3:00 AM local server time.

**Actions**:

- Fetch all `user_ratings` submitted in the last 24 hours.
- For each rating:
  - Parse and normalize flavor tags, effort tags, and sentiment.
  - Adjust user's `preferred_flavors` vector.
  - Adjust `effort_tolerance` based on perceived difficulty.
  - Promote/demote liked and disliked ingredients.
- Apply slight decay to old preferences.
- Update `user_preferences.last_updated` timestamp.

**Failure Handling**:
- Log failures into `cron_failures.log`.
- If Spoonacular or AI services fail temporarily, retry up to 3 times.

**Notes**:
- Critical to smooth preference learning and personalization.

---

## 2. AI Response Cache Expiry Job (Planned)

**Purpose**:  
Purge expired entries from the `cached_ai_responses` table to conserve Redis memory.

**Trigger**:  
- Scheduled weekly on Sundays at 4:00 AM.

**Actions**:
- Delete cached responses where `expires_at < now()`.

**Failure Handling**:
- Log into `cron_failures.log`.

**Notes**:
- Non-critical. Cache misses will naturally trigger re-calls if purge fails.

---

## Scheduling Method

Recommended:  
- Use `cron` + `docker exec` if Dockerized backend.
- Future option: Move to Celery periodic tasks or APScheduler for more granular control.

Example Crontab (host level):

```
0 3 * * * docker exec recipe_assistant_backend python manage_cron.py update_preferences
0 4 * * 0 docker exec recipe_assistant_backend python manage_cron.py purge_cache
```

---

## Related Documents

- [[README]]
- [[SYSTEM_OVERVIEW]]
- [[DB_SCHEMA]]
