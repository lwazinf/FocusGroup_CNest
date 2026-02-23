#!/usr/bin/env python3
"""
personas_loader.py
Run once (or any time persona files are updated) to seed ChromaDB.
Usage: python personas_loader.py
"""
import json
import os
from config import PERSONAS_DIR, PERSONA_REGISTRY
from db.chroma_client import upsert_persona

def load_all_personas():
    print("Loading personas into ChromaDB...")
    for key, meta in PERSONA_REGISTRY.items():
        filepath = os.path.join(PERSONAS_DIR, meta["file"])
        with open(filepath, "r") as f:
            data = json.load(f)
        persona_id = data["id"]
        document = data["document"]
        metadata = data["metadata"]
        upsert_persona(persona_id, document, metadata)
        print(f"  ✓ Loaded: {meta['name']} ({persona_id})")
    print("Done. ChromaDB is ready.")

if __name__ == "__main__":
    load_all_personas()
