import sys
from datetime import datetime, timedelta
import json
import logging
from app.models import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TASTE_DIMENSIONS = ["sweetness", "saltiness", "sourness", "bitterness", "savoriness", "fattiness"]


def update_preferences():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT user_id FROM user_ratings")
        users = [row[0] for row in cur.fetchall()]
        logger.info(f"Found users with ratings: {users}")

        for user_id in users:
            logger.info(f"Updating preferences for user: {user_id}")
            # Get ratings from last 24h (or longer for initial seeding?)
            # Consider weighting recent ratings more?
            cur.execute(
                f"""
                SELECT effort_tag, {', '.join(TASTE_DIMENSIONS)}
                FROM user_ratings
                WHERE user_id = %s AND timestamp > %s AND sentiment = 'positive' -- Only learn from positive experiences?
            """,
                (user_id, datetime.now() - timedelta(days=1)),
            )
            rows = cur.fetchall()
            logger.info(f"Found {len(rows)} recent positive ratings for user {user_id}")

            if not rows:
                continue

            # Aggregate effort
            effort_counts = {"easy": 0, "moderate": 0, "hard": 0}
            # Aggregate taste scores
            taste_sums = {dim: 0 for dim in TASTE_DIMENSIONS}
            taste_counts = {dim: 0 for dim in TASTE_DIMENSIONS}

            for row_data in rows:
                effort_tag = row_data[0]
                if effort_tag in effort_counts:
                    effort_counts[effort_tag] += 1

                for i, dim in enumerate(TASTE_DIMENSIONS):
                    score = row_data[i + 1]
                    if score is not None:  # Only count non-null scores
                        taste_sums[dim] += score
                        taste_counts[dim] += 1

            # Calculate average taste profile
            avg_taste_profile = {}
            for dim in TASTE_DIMENSIONS:
                if taste_counts[dim] > 0:
                    avg_taste_profile[dim] = round(taste_sums[dim] / taste_counts[dim])
                else:
                    avg_taste_profile[dim] = 50  # Default to neutral if no data

            # Determine preferred effort
            effort_pref = (
                max(effort_counts, key=effort_counts.get)
                if any(effort_counts.values())
                else "moderate"
            )

            # Upsert into user_preferences
            cur.execute(
                """
                INSERT INTO user_preferences (user_id, taste_profile, effort_tolerance, last_updated)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    taste_profile = EXCLUDED.taste_profile,
                    effort_tolerance = EXCLUDED.effort_tolerance,
                    last_updated = EXCLUDED.last_updated
            """,
                (user_id, json.dumps(avg_taste_profile), effort_pref, datetime.now()),
            )
            logger.info(
                f"Updated preferences for {user_id}: Effort={effort_pref}, Taste={avg_taste_profile}"
            )

        conn.commit()
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "update_preferences":
        update_preferences()
        print("User preferences updated.")
    else:
        print("Usage: python manage_cron.py update_preferences")
