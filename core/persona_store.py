import json
import os
import re

from config import PERSONA_REGISTRY, PERSONA_MENTION_MAP, PERSONAS_DIR
from db.chroma_client import upsert_persona, get_collection
from db.redis_client import reset_session

CUSTOM_DIR = os.path.join(PERSONAS_DIR, "custom")
REGISTRY_PATH = os.path.join(CUSTOM_DIR, "registry.json")


def _slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = re.sub(r"_+", "_", slug)
    return slug.strip("_")


def load_custom_registry() -> dict:
    try:
        with open(REGISTRY_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_registry(registry: dict) -> None:
    os.makedirs(CUSTOM_DIR, exist_ok=True)
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def next_available_key(registry: dict) -> str:
    all_keys = {1, 2} | {int(k) for k in registry.keys()}
    return str(max(all_keys) + 1)


def custom_to_chroma_metadata(persona: dict) -> dict:
    return {
        "age": persona["age"],
        "gender": persona["gender"],
        "nationality": persona["nationality"],
        "location": persona["location"],
        "profession": persona["occupation"],
        "gaming_experience_level": persona["gaming_level"],
        "is_custom": True,
        "purchase_hesitation_triggers": persona["hesitation_triggers"],
        "motivations": persona["motivations"],
        "emotional_language_resonance": persona["emotional_resonance"],
        "psychographics_decision_style": persona["decision_style"],
    }


def save_custom_persona(persona: dict) -> str:
    os.makedirs(CUSTOM_DIR, exist_ok=True)
    registry = load_custom_registry()
    key = next_available_key(registry)

    name = persona["name"]
    slugified_name = _slugify(name)
    # Extract timestamp from persona id (last segment after final underscore)
    ts = persona["id"].rsplit("_", 1)[-1]

    registry_entry = {
        "name": name,
        "id": persona["id"],
        "file": f"{persona['id']}.json",
        "redis_key": f"session:custom_{slugified_name}_{ts}:messages",
        "mention": _slugify(name),   # slugified so @mention works in regex (\w+)
    }

    # Save persona JSON file
    persona_path = os.path.join(CUSTOM_DIR, registry_entry["file"])
    with open(persona_path, "w") as f:
        json.dump(persona, f, indent=2)

    # Upsert to ChromaDB
    chroma_metadata = custom_to_chroma_metadata(persona)
    upsert_persona(persona["id"], persona["document"], chroma_metadata)

    # Update registry
    registry[key] = registry_entry
    save_registry(registry)

    return key


def delete_custom_persona(key: str) -> None:
    registry = load_custom_registry()
    entry = registry.get(key)
    if entry is None:
        raise KeyError(f"Custom persona key '{key}' not found in registry")

    # Delete JSON file
    persona_path = os.path.join(CUSTOM_DIR, entry["file"])
    if os.path.exists(persona_path):
        os.remove(persona_path)

    # Remove from ChromaDB
    get_collection().delete(ids=[entry["id"]])

    # Clear Redis history
    reset_session(entry["redis_key"])

    # Update registry
    del registry[key]
    save_registry(registry)


def update_custom_persona(key: str, persona: dict) -> None:
    registry = load_custom_registry()
    entry = registry.get(key)
    if entry is None:
        raise KeyError(f"Custom persona key '{key}' not found in registry")

    # Overwrite persona JSON file
    persona_path = os.path.join(CUSTOM_DIR, entry["file"])
    with open(persona_path, "w") as f:
        json.dump(persona, f, indent=2)

    # Re-upsert to ChromaDB
    chroma_metadata = custom_to_chroma_metadata(persona)
    upsert_persona(entry["id"], persona["document"], chroma_metadata)

    # Update registry entry (name may have changed)
    entry["name"] = persona["name"]
    entry["mention"] = _slugify(persona["name"])
    registry[key] = entry
    save_registry(registry)


def get_full_registry() -> dict:
    merged = dict(PERSONA_REGISTRY)
    merged.update(load_custom_registry())
    return merged


def get_full_mention_map() -> dict:
    merged = dict(PERSONA_MENTION_MAP)
    custom_registry = load_custom_registry()
    for key, entry in custom_registry.items():
        merged[f"@{entry['mention']}"] = key
    return merged
