import os
import redis
import json

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

def get_cache(key):
    value = r.get(key)
    if value:
        try:
            return json.loads(value)
        except Exception:
            return value
    return None

def set_cache(key, value, ex=3600):
    r.set(key, json.dumps(value), ex=ex)
