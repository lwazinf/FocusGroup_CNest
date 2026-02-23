import os

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_SESSION_TTL = int(os.getenv("REDIS_SESSION_TTL", 86400))  # 24h default
CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "./.chromadb")
CHROMA_COLLECTION_NAME = "personas"
PERSONAS_DIR = os.path.join(os.path.dirname(__file__), "personas")

PERSONA_REGISTRY = {
    "1": {
        "name": "Lena",
        "id": "persona_german_transfer_student_23",
        "file": "female_23.json",
        "redis_key": "session:lena:messages"
    },
    "2": {
        "name": "Marcus",
        "id": "persona_designer_dad_38_refined",
        "file": "male_38.json",
        "redis_key": "session:marcus:messages"
    }
}

PERSONA_MENTION_MAP = {
    "@lena": "1",
    "@marcus": "2"
}
