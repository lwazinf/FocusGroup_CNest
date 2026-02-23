import json
import redis
from config import REDIS_URL, REDIS_SESSION_TTL

_redis = None

def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis

def load_history(redis_key: str) -> list:
    r = get_redis()
    raw = r.get(redis_key)
    if raw:
        return json.loads(raw)
    return []

def save_history(redis_key: str, messages: list):
    r = get_redis()
    r.set(redis_key, json.dumps(messages), ex=REDIS_SESSION_TTL)

def append_exchange(redis_key: str, user_msg: str, assistant_msg: str):
    history = load_history(redis_key)
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": assistant_msg})
    save_history(redis_key, history)

def reset_session(redis_key: str):
    r = get_redis()
    r.delete(redis_key)
