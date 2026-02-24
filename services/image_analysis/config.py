import os

OLLAMA_CLOUD_API_KEY  = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_CLOUD_BASE_URL = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_VISION_MODEL   = os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:235b-cloud")

IMAGE_ANALYSIS_TTL  = int(os.getenv("IMAGE_ANALYSIS_TTL", 604800))   # 7 days
IMAGE_FILENAME_TTL  = int(os.getenv("IMAGE_FILENAME_TTL", 604800))   # 7 days

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
