import chromadb
import json
import os
from config import CHROMA_PERSIST_PATH, CHROMA_COLLECTION_NAME

_client = None
_collection = None

def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
        _collection = _client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection

def upsert_persona(persona_id: str, document: str, metadata: dict):
    col = get_collection()
    flat_meta = _flatten_metadata(metadata)
    col.upsert(
        ids=[persona_id],
        documents=[document],
        metadatas=[flat_meta]
    )

def get_persona(persona_id: str) -> dict:
    col = get_collection()
    result = col.get(ids=[persona_id], include=["documents", "metadatas"])
    if not result["ids"]:
        raise ValueError(f"Persona '{persona_id}' not found in ChromaDB")
    return {
        "id": result["ids"][0],
        "document": result["documents"][0],
        "metadata": result["metadatas"][0]
    }

def _flatten_metadata(meta: dict, prefix: str = "") -> dict:
    flat = {}
    for k, v in meta.items():
        key = f"{prefix}{k}" if not prefix else f"{prefix}_{k}"
        if isinstance(v, dict):
            flat.update(_flatten_metadata(v, prefix=key))
        elif isinstance(v, list):
            flat[key] = json.dumps(v)
        elif isinstance(v, (str, int, float, bool)):
            flat[key] = v
        else:
            flat[key] = str(v)
    return flat
