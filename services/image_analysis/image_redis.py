import json
from db.redis_client import get_redis
from services.image_analysis.config import IMAGE_ANALYSIS_TTL, IMAGE_FILENAME_TTL

# Key schema
# room:images:{hash}:analysis  — JSON-serialised AnalysisResult
# room:images:{hash}:filename  — original filename string
# room:images:index            — Redis list of hashes in upload order (session-scoped)


def _analysis_key(md5_hex: str) -> str:
    return f"room:images:{md5_hex}:analysis"


def _filename_key(md5_hex: str) -> str:
    return f"room:images:{md5_hex}:filename"


INDEX_KEY = "room:images:index"


def get_analysis(md5_hex: str) -> dict | None:
    try:
        raw = get_redis().get(_analysis_key(md5_hex))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def set_analysis(md5_hex: str, filename: str, analysis: dict) -> None:
    try:
        r = get_redis()
        r.set(_analysis_key(md5_hex), json.dumps(analysis), ex=IMAGE_ANALYSIS_TTL)
        r.set(_filename_key(md5_hex), filename, ex=IMAGE_FILENAME_TTL)
        # Only add to index if not already present
        index = r.lrange(INDEX_KEY, 0, -1)
        if md5_hex not in index:
            r.rpush(INDEX_KEY, md5_hex)
    except Exception:
        pass


def get_filename(md5_hex: str) -> str | None:
    try:
        return get_redis().get(_filename_key(md5_hex))
    except Exception:
        return None


def get_index() -> list[str]:
    """Return ordered list of hashes currently in the session."""
    try:
        return get_redis().lrange(INDEX_KEY, 0, -1)
    except Exception:
        return []


def clear_index() -> None:
    """Remove the session image index (does not delete individual analyses)."""
    try:
        get_redis().delete(INDEX_KEY)
    except Exception:
        pass
