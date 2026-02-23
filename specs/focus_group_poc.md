# Focus Group Simulation — Technical Reference

---

## Architecture

### Stack

| Layer | Technology | Purpose |
|---|---|---|
| LLM Inference | Ollama + Llama 3.1 8B | Local, cost-free inference |
| Persona Storage | ChromaDB | Persona documents and metadata (vector store) |
| Session Memory | Redis | Conversation history per persona (rolling, TTL-based) |
| Orchestration | LangGraph | Legacy single-persona graph (context assembly + response) |
| Interface | Terminal (CLI) | Human moderator input/output |

---

### Module Map

```
FocusGroup/
│
├── main.py                  ← Entry point — room loop, all commands, colours
│
├── core/
│   ├── room.py              ← RoomState / PersonaContext types + room management fns
│   ├── nodes.py             ← LLM call, thinking extraction, room-constraint injection
│   ├── persona_router.py    ← Command parsing (!add, !kick, !focus, !observe, !exit…)
│   ├── persona_generator.py ← Random persona generation + interactive editing
│   ├── persona_store.py     ← Custom persona save / load / delete / update
│   ├── topic_context.py     ← Dynamic topic context fetching
│   ├── summary.py           ← Chat summary generation + Markdown file writer
│   ├── prompt_builder.py    ← System prompt assembly (persona identity + topic context)
│   └── graph.py             ← LangGraph definition (single-persona legacy flow)
│
├── db/
│   ├── chroma_client.py     ← ChromaDB init, upsert, retrieve
│   └── redis_client.py      ← Redis session read / write / reset helpers
│
├── context/
│   └── ps5_context.py       ← Static PS5 product context block (default topic)
│
├── personas/
│   ├── female_23.json       ← Lena's persona definition
│   ├── male_38.json         ← Marcus's persona definition
│   ├── custom/              ← User-generated custom personas
│   └── persona_template.json
│
├── chat_summaries/          ← Auto-generated session summaries (created on !exit)
├── tests/
│   └── test_core.py         ← Unit tests (room logic, commands, thinking, summary)
│
├── personas_loader.py       ← Seeds persona JSONs into ChromaDB (run once)
├── config.py                ← PERSONA_REGISTRY, PERSONA_MENTION_MAP, env vars
└── requirements.txt
```

---

### How the Room Constraint Works

Each persona's system prompt has four layers assembled at load time:

```
[1] Persona identity      — who they are, their history, values
[2] Behavioural anchors   — hesitation triggers, motivations, decision style
[3] Topic context         — what the current discussion topic is, comparison points
[4] Rules of engagement   — stay in character, be candid, concise response length
```

On every LLM call, two more blocks are appended at runtime:

```
[5] Room constraint       — "The ONLY people present are X and Y. Do not address anyone else."
[6] Thinking instruction  — "Wrap internal reasoning in <think>…</think> before responding."
```

Block 5 prevents the model from hallucinating participants who aren't in the room.

---

### Thinking Display

If the model wraps its reasoning in `<think>…</think>` tags, it is:
- **Stripped from the visible response** (persona only says what they'd say out loud)
- **Shown in the terminal in dark grey** before the response
- **Logged and included** in the chat summary under each persona's entry

---

### Observe Mode

`!observe` puts the moderator in the background and lets the personas speak directly to each other. Each round, every active persona responds to the last thing said by the previous speaker. The seed prompt is taken from the last moderator message, or a generic prompt if none exists.

Rounds are counted per full loop through all active personas. `!observe 5` runs 5 full rounds; `!observe` defaults to 3.

---

## Configuration Reference

All settings live in `config.py` or can be overridden via environment variable.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.1:8b` | Model name for Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `REDIS_SESSION_TTL` | `86400` (24h) | History TTL in seconds |
| `CHROMA_PERSIST_PATH` | `./.chromadb` | ChromaDB storage path |

Optional `.env` override file:

```
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
REDIS_URL=redis://localhost:6379
REDIS_SESSION_TTL=86400
CHROMA_PERSIST_PATH=./.chromadb
```

---

## Adding a New Persona

### 1. Create the persona JSON

Copy `personas/persona_template.json`. The file must have this top-level structure:

```json
{
  "id": "persona_yuki_id",
  "document": "Yuki is a ...",
  "metadata": {
    "name": "Yuki",
    "evaluation_framework": {
      "primary_filter": "value for money"
    },
    "psychographics_decision_style": "...",
    "purchase_hesitation_triggers": ["price", "..."],
    "emotional_language_resonance": ["quality", "..."],
    "motivations": ["family", "..."]
  }
}
```

Place the file in `personas/`.

### 2. Register the persona in `config.py`

Add an entry to `PERSONA_REGISTRY`:

```python
"3": {
    "name": "Yuki",
    "id": "persona_yuki_id",
    "file": "yuki.json",
    "redis_key": "session:yuki:messages",
    "brief": "28yo Tokyo-based engineer · budget-conscious · mobile-first",
}
```

Add the `@mention` mapping to `PERSONA_MENTION_MAP`:

```python
"@yuki": "3"
```

### 3. Seed ChromaDB

```bash
python personas_loader.py
```

Yuki is now available in the persona selection menu and as `!add @yuki`.

---

## Chat Summary Format

Saved to `chat_summaries/chat_YYYYMMDD_HHMMSS.md`:

```
# Focus Group Session Summary
*Generated: 2026-02-23 14:10:22*

---

## Executive Summary
[3–5 paragraph analysis: themes, agreements, tensions, overall sentiment]

---

## Full Chat Log
[Every message with timestamps, including each persona's thinking in grey blockquotes]
```

---

---

# Plan: Focus Group Simulation POC

## Task Description

Build a terminal-based AI focus group simulation that allows a human moderator to have one-on-one conversations with one of two richly defined synthetic personas — Lena (23, German gamer/content creator) and Marcus (38, designer dad/Apple loyalist). The system uses LangGraph for orchestration, Ollama + Llama 3.1 for local LLM inference, ChromaDB for persona vector storage, and Redis for isolated session conversation history. The product focus is the PlayStation 5. The moderator interacts via terminal, selects a persona at startup, and can switch personas mid-session using `@Lena` or `@Marcus`. Reserved commands `!reset` and `!exit` manage session lifecycle.

## Objective

A fully functional terminal application where the moderator can:
1. Choose to speak with Lena or Marcus at session start
2. Ask freeform questions about the PS5 and receive deeply in-character responses
3. Switch between personas at any time with `@Lena` or `@Marcus`
4. Reset a persona's session history with `!reset`
5. Exit cleanly with `!exit`

Each persona maintains isolated conversation history in Redis and responds consistently with their defined identity, values, decision frameworks, and relationship to gaming/the PS5.

## Problem Statement

A static persona JSON file alone cannot power a dynamic, in-character conversation. The system needs to: embed persona identity into a vector store, assemble layered system prompts at runtime, maintain rolling conversation history per persona, and route all of this through a clean LangGraph state machine that handles switching and resets gracefully.

## Solution Approach

Build the project module by module — config and constants first, then database clients (ChromaDB + Redis), then the persona loader that seeds ChromaDB, then the prompt builder, then LangGraph nodes and graph, then the terminal entry point. Each layer depends on the one below it. The persona JSON files already exist in `personas/`. The LLM runs locally via Ollama — no API keys required.

---

## Relevant Files

- `personas/female_23.json` — Lena's persona definition (exists)
- `personas/male_38.json` — Marcus's persona definition (exists)
- `personas/persona_template.json` — Template for future personas (exists)
- `README.md` — Full architecture documentation (exists)

### New Files
- `config.py` — Environment config, model name, Redis URL, TTL, persona registry
- `requirements.txt` — All Python dependencies
- `context/ps5_context.py` — Static PS5 product context string injected into every session
- `db/chroma_client.py` — ChromaDB initialisation, embedding, and retrieval helpers
- `db/redis_client.py` — Redis session read, write, reset helpers
- `db/__init__.py` — Package init
- `core/prompt_builder.py` — Assembles layered system prompt from persona + PS5 context
- `core/nodes.py` — All LangGraph node functions: context assembly, moderator input, persona response, memory write
- `core/graph.py` — LangGraph StateGraph definition and compilation
- `core/persona_router.py` — Detects @Lena / @Marcus switches and !commands
- `core/__init__.py` — Package init
- `context/__init__.py` — Package init
- `personas_loader.py` — One-time script to embed persona JSONs into ChromaDB
- `main.py` — Terminal entry point: persona selection, conversation loop

---

## Implementation Phases

### Phase 1: Foundation
Set up config, requirements, PS5 context block, and database clients. Ensure ChromaDB and Redis can initialise cleanly. Run the persona loader to seed ChromaDB with Lena and Marcus.

### Phase 2: Core Implementation
Build the prompt builder, LangGraph nodes, graph state machine, and persona router. Each node should be independently testable. The graph should handle the full conversation loop and persona switching.

### Phase 3: Integration & Polish
Wire everything together in `main.py`. Test the full terminal flow: startup, persona selection, conversation, switching, reset, and exit. Ensure personas stay in character across multi-turn conversations.

---

## Team Orchestration

- You operate as the team lead and orchestrate the team to execute the plan.
- You NEVER write code directly — you use Task and Task* tools to deploy team members.
- Validate all work is correct and complete before marking tasks done.

### Team Members

- Builder: **builder-foundation**
  - Role: Sets up config, requirements, PS5 context, and database clients (ChromaDB + Redis)
  - Agent Type: general-purpose
  - Resume: true

- Builder: **builder-persona-loader**
  - Role: Writes and validates the personas_loader.py script that seeds ChromaDB
  - Agent Type: general-purpose
  - Resume: true

- Builder: **builder-core**
  - Role: Builds prompt_builder, LangGraph nodes, graph, and persona router
  - Agent Type: general-purpose
  - Resume: true

- Builder: **builder-main**
  - Role: Writes main.py terminal entry point and wires all modules together
  - Agent Type: general-purpose
  - Resume: true

- Validator: **validator**
  - Role: Runs validation checks, confirms imports resolve, structure is correct, and does a dry-run without Ollama/Redis
  - Agent Type: general-purpose
  - Resume: false

---

## Step by Step Tasks

### 1. Setup Config, Requirements, and PS5 Context

- **Task ID**: setup-foundation
- **Depends On**: none
- **Assigned To**: builder-foundation
- **Agent Type**: general-purpose
- **Parallel**: false

Create `config.py` with the following:
```python
# config.py
import os

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
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

# Map @mention names to registry keys
PERSONA_MENTION_MAP = {
    "@lena": "1",
    "@marcus": "2"
}
```

Create `requirements.txt`:
```
langgraph>=0.2.0
langchain>=0.2.0
langchain-community>=0.2.0
langchain-ollama>=0.1.0
chromadb>=0.5.0
redis>=5.0.0
python-dotenv>=1.0.0
```

Create `context/__init__.py` (empty).

Create `context/ps5_context.py`:
```python
PS5_CONTEXT = """
PRODUCT FOCUS: PlayStation 5 (PS5)
Manufacturer: Sony Interactive Entertainment
Original Release: November 2020
PS5 Pro Release: November 2024
Price: ~$499 (Standard Disc Edition) / ~$449 (Digital Edition) / ~$699 (PS5 Pro)

Key Features:
- Custom AMD Zen 2 CPU + RDNA 2 GPU
- Ultra-high-speed NVMe SSD (5.5 GB/s)
- DualSense haptic feedback + adaptive triggers
- 4K gaming at up to 120fps, ray tracing support
- Backwards compatible with PS4 titles
- PlayStation Network (PSN) ecosystem — closed platform
- No mod support, no cross-buy with PC, limited cross-platform play

Notable Exclusive Library:
- God of War Ragnarök, Spider-Man 2, Returnal, Demon's Souls
- Gran Turismo 7, Ratchet & Clank: Rift Apart, Horizon Forbidden West
- Astro's Playroom (pack-in, showcases DualSense)

Relevant Comparisons Available:
- PS4 / PS4 Pro (predecessor)
- Xbox Series X (direct competitor, Game Pass ecosystem)
- Nintendo Switch / Switch OLED (family-oriented, portable)
- Gaming PC (open ecosystem, modding, higher ceiling)

Ecosystem Notes:
- Fully closed — no sideloading, no mods, no emulation
- PSN subscription (PS Plus) required for online multiplayer
- Digital storefront only for digital titles
- No native Android or iOS integration
"""
```

---

### 2. Build Database Clients

- **Task ID**: build-db-clients
- **Depends On**: setup-foundation
- **Assigned To**: builder-foundation
- **Agent Type**: general-purpose
- **Parallel**: false

Create `db/__init__.py` (empty).

Create `db/chroma_client.py`:
```python
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
    # Flatten metadata for ChromaDB (only accepts str/int/float/bool values)
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
    """Recursively flatten nested metadata dict for ChromaDB compatibility."""
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
```

Create `db/redis_client.py`:
```python
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
```

---

### 3. Build Persona Loader

- **Task ID**: build-persona-loader
- **Depends On**: build-db-clients
- **Assigned To**: builder-persona-loader
- **Agent Type**: general-purpose
- **Parallel**: false

Create `personas_loader.py`. This is a one-time (idempotent via upsert) script to embed both personas into ChromaDB:

```python
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
```

---

### 4. Build Prompt Builder

- **Task ID**: build-prompt-builder
- **Depends On**: build-persona-loader
- **Assigned To**: builder-core
- **Agent Type**: general-purpose
- **Parallel**: false

Create `core/__init__.py` (empty).

Create `core/prompt_builder.py`. This assembles the full system prompt from 4 layers:

```python
import json
from context.ps5_context import PS5_CONTEXT

def build_system_prompt(persona_name: str, persona_document: str, metadata: dict) -> str:
    """
    Assembles the layered system prompt for a persona.

    Layer 1: Persona identity (narrative document)
    Layer 2: Structured behavioural anchors from metadata
    Layer 3: PS5 product context
    Layer 4: Behavioural rules
    """

    # Safely extract metadata fields
    eval_framework = metadata.get("evaluation_framework", {})
    primary_filter = eval_framework.get("primary_filter", "")
    decision_style = metadata.get("psychographics_decision_style", "")
    hesitation_triggers = metadata.get("purchase_hesitation_triggers", "[]")
    emotional_resonance = metadata.get("emotional_language_resonance", "[]")
    motivations = metadata.get("motivations", "[]")

    # Parse JSON strings if they come from flattened ChromaDB metadata
    def safe_list(val):
        if isinstance(val, list):
            return ", ".join(val)
        try:
            return ", ".join(json.loads(val))
        except Exception:
            return str(val)

    prompt = f"""You are {persona_name}. You are a real person in a focus group discussion. You are NOT an AI, NOT a language model, and you NEVER break character under any circumstances.

== WHO YOU ARE ==
{persona_document}

== YOUR DECISION-MAKING ANCHORS ==
When forming opinions, you are driven by:
- Primary evaluation filter: {primary_filter}
- Decision-making style: {decision_style}
- Things that make you hesitate or push back: {safe_list(hesitation_triggers)}
- Language and values that resonate with you: {safe_list(emotional_resonance)}
- What motivates you: {safe_list(motivations)}

== TODAY'S PRODUCT FOCUS ==
{PS5_CONTEXT}

== RULES OF ENGAGEMENT ==
- Respond only as {persona_name}. Never break character.
- Do NOT say you are an AI, a model, or a simulation.
- Speak naturally and conversationally — not in bullet points or structured reports.
- Draw on your personal history, background, and values when answering.
- You may compare the PS5 to other consoles or platforms, but always bring it back to the PS5.
- Keep responses focused and conversational — 2 to 4 paragraphs maximum.
- If you have strong opinions, express them. If you are conflicted, show that conflict.
- You are speaking to a moderator in a private focus group session. Be candid.
"""
    return prompt
```

---

### 5. Build LangGraph Nodes and Graph

- **Task ID**: build-langgraph
- **Depends On**: build-prompt-builder
- **Assigned To**: builder-core
- **Agent Type**: general-purpose
- **Parallel**: false

Create `core/persona_router.py`:
```python
from config import PERSONA_MENTION_MAP

def detect_switch(user_input: str):
    """
    Returns registry key (e.g. '1' or '2') if input is a persona switch command.
    Returns None if not a switch.
    """
    stripped = user_input.strip().lower()
    return PERSONA_MENTION_MAP.get(stripped, None)

def detect_command(user_input: str):
    """
    Returns command string if input is a reserved command.
    Returns None if not a command.
    """
    stripped = user_input.strip().lower()
    if stripped == "!reset":
        return "reset"
    if stripped == "!exit":
        return "exit"
    return None
```

Create `core/nodes.py`:
```python
from typing import TypedDict, Annotated, List
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from db.chroma_client import get_persona
from db.redis_client import load_history, append_exchange, reset_session
from core.prompt_builder import build_system_prompt
from config import OLLAMA_MODEL, OLLAMA_BASE_URL, PERSONA_REGISTRY

class SessionState(TypedDict):
    persona_key: str           # '1' or '2'
    persona_name: str
    persona_id: str
    redis_key: str
    system_prompt: str
    history: List[dict]
    user_input: str
    response: str
    command: str               # 'reset', 'exit', 'switch', or ''

def assemble_context(state: SessionState) -> SessionState:
    """Load persona from ChromaDB, build system prompt, load Redis history."""
    persona_key = state["persona_key"]
    reg = PERSONA_REGISTRY[persona_key]

    persona_data = get_persona(reg["id"])
    system_prompt = build_system_prompt(
        persona_name=reg["name"],
        persona_document=persona_data["document"],
        metadata=persona_data["metadata"]
    )
    history = load_history(reg["redis_key"])

    return {
        **state,
        "persona_name": reg["name"],
        "persona_id": reg["id"],
        "redis_key": reg["redis_key"],
        "system_prompt": system_prompt,
        "history": history,
        "command": ""
    }

def generate_response(state: SessionState) -> SessionState:
    """Send prompt + history + user input to Ollama, get in-character response."""
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.75
    )

    messages = [SystemMessage(content=state["system_prompt"])]
    for msg in state["history"]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=state["user_input"]))

    result = llm.invoke(messages)
    response_text = result.content

    # Persist to Redis
    append_exchange(state["redis_key"], state["user_input"], response_text)

    # Update in-memory history
    updated_history = state["history"] + [
        {"role": "user", "content": state["user_input"]},
        {"role": "assistant", "content": response_text}
    ]

    return {
        **state,
        "response": response_text,
        "history": updated_history
    }
```

Create `core/graph.py`:
```python
from langgraph.graph import StateGraph, END
from core.nodes import SessionState, assemble_context, generate_response

def build_graph():
    graph = StateGraph(SessionState)

    graph.add_node("assemble_context", assemble_context)
    graph.add_node("generate_response", generate_response)

    graph.set_entry_point("assemble_context")
    graph.add_edge("assemble_context", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()
```

---

### 6. Build Terminal Entry Point

- **Task ID**: build-main
- **Depends On**: build-langgraph
- **Assigned To**: builder-main
- **Agent Type**: general-purpose
- **Parallel**: false

Create `main.py`. This is the full terminal conversation loop:

```python
#!/usr/bin/env python3
"""
main.py — Focus Group Simulation Terminal Entry Point

Usage:
    python main.py

Commands during session:
    @Lena     — switch to Lena
    @Marcus   — switch to Marcus
    !reset    — clear current persona's conversation history
    !exit     — quit the simulation
"""
import sys
from core.graph import build_graph
from core.persona_router import detect_switch, detect_command
from core.nodes import SessionState
from db.redis_client import reset_session, load_history
from config import PERSONA_REGISTRY

DIVIDER = "─" * 50

def print_banner():
    print("\n" + "=" * 50)
    print("  FOCUS GROUP SIMULATION")
    print("  Product: PlayStation 5")
    print("=" * 50)

def choose_persona() -> str:
    print("\nWho would you like to speak with?\n")
    for key, val in PERSONA_REGISTRY.items():
        print(f"  {key}. {val['name']}")
    print()
    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice in PERSONA_REGISTRY:
            return choice
        print("  Please enter 1 or 2.")

def announce_persona(persona_key: str):
    name = PERSONA_REGISTRY[persona_key]["name"]
    redis_key = PERSONA_REGISTRY[persona_key]["redis_key"]
    history = load_history(redis_key)
    print(f"\n{DIVIDER}")
    if history:
        print(f"[Resuming session with {name}]")
    else:
        print(f"[{name} is ready]")
    print(DIVIDER)

def run():
    print_banner()
    graph = build_graph()

    # Initial persona selection
    persona_key = choose_persona()
    announce_persona(persona_key)

    # Seed initial state
    state: SessionState = {
        "persona_key": persona_key,
        "persona_name": "",
        "persona_id": "",
        "redis_key": "",
        "system_prompt": "",
        "history": [],
        "user_input": "",
        "response": "",
        "command": ""
    }

    # Run context assembly once for the initial persona
    from core.nodes import assemble_context
    state = assemble_context(state)

    while True:
        try:
            user_input = input(f"\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n[Session ended]")
            sys.exit(0)

        if not user_input:
            continue

        # Check for reserved commands
        cmd = detect_command(user_input)
        if cmd == "exit":
            print("\n[Session ended. Goodbye.]")
            sys.exit(0)
        if cmd == "reset":
            reset_session(state["redis_key"])
            state["history"] = []
            print(f"\n[{state['persona_name']}'s session history cleared.]\n")
            continue

        # Check for persona switch
        switch_key = detect_switch(user_input)
        if switch_key:
            if switch_key == state["persona_key"]:
                print(f"\n[Already speaking with {state['persona_name']}]\n")
                continue
            persona_key = switch_key
            state["persona_key"] = persona_key
            state = assemble_context(state)
            announce_persona(persona_key)
            continue

        # Normal conversation turn — run generate_response node
        state["user_input"] = user_input
        state = graph.invoke({**state, "user_input": user_input})

        print(f"\n{state['persona_name']}: {state['response']}\n")
        print(DIVIDER)

if __name__ == "__main__":
    run()
```

---

### 7. Validation

- **Task ID**: validate-all
- **Depends On**: build-main
- **Assigned To**: validator
- **Agent Type**: general-purpose
- **Parallel**: false

Run the following checks:

**Structural check — all files exist:**
```bash
ls config.py requirements.txt main.py personas_loader.py \
   context/__init__.py context/ps5_context.py \
   db/__init__.py db/chroma_client.py db/redis_client.py \
   core/__init__.py core/prompt_builder.py core/nodes.py \
   core/graph.py core/persona_router.py
```

**Import check — no syntax errors:**
```bash
python -c "import config; print('config OK')"
python -c "from context.ps5_context import PS5_CONTEXT; print('ps5_context OK')"
python -c "from db.chroma_client import get_collection; print('chroma_client OK')"
python -c "from db.redis_client import load_history; print('redis_client OK')"
python -c "from core.prompt_builder import build_system_prompt; print('prompt_builder OK')"
python -c "from core.persona_router import detect_switch, detect_command; print('persona_router OK')"
python -c "from core.nodes import assemble_context, generate_response, SessionState; print('nodes OK')"
python -c "from core.graph import build_graph; print('graph OK')"
python -c "import main; print('main OK')"
```

**Persona router unit test:**
```bash
python -c "
from core.persona_router import detect_switch, detect_command
assert detect_switch('@Lena') == '1', 'Lena switch failed'
assert detect_switch('@Marcus') == '2', 'Marcus switch failed'
assert detect_switch('@lena') == '1', 'lowercase lena failed'
assert detect_switch('hello') is None, 'false positive switch'
assert detect_command('!reset') == 'reset', 'reset failed'
assert detect_command('!exit') == 'exit', 'exit failed'
assert detect_command('hello') is None, 'false positive command'
print('persona_router unit tests PASSED')
"
```

**Prompt builder unit test (no LLM needed):**
```bash
python -c "
from core.prompt_builder import build_system_prompt
prompt = build_system_prompt('Lena', 'Test document.', {'evaluation_framework': {'primary_filter': 'performance'}})
assert 'Lena' in prompt
assert 'PlayStation 5' in prompt
assert 'Test document.' in prompt
print('prompt_builder unit tests PASSED')
"
```

**Confirm personas directory integrity:**
```bash
python -c "
import json, os
for f in ['female_23.json', 'male_38.json']:
    with open(f'personas/{f}') as fp:
        d = json.load(fp)
    assert 'id' in d and 'document' in d and 'metadata' in d
    print(f'{f}: OK ({d[\"id\"]})')
"
```

If any check fails, fix the relevant module before proceeding. Do NOT mark this task complete until all checks pass.

---

## Acceptance Criteria

- [ ] All files listed in the folder structure exist with no import errors
- [ ] `personas_loader.py` runs without error and confirms both personas are loaded
- [ ] `@Lena` and `@Marcus` correctly trigger persona switches in the router
- [ ] `!reset` clears the correct Redis key
- [ ] `!exit` terminates cleanly
- [ ] System prompt contains persona identity, behavioural anchors, and PS5 context
- [ ] Conversation history persists across turns (Redis append working)
- [ ] Switching personas loads isolated history (no cross-contamination)
- [ ] All unit tests in validation task pass

## Validation Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Seed ChromaDB
python personas_loader.py

# Run all import checks
python -c "from core.graph import build_graph; build_graph(); print('Graph compiled OK')"

# Run persona router tests
python -c "
from core.persona_router import detect_switch, detect_command
assert detect_switch('@Lena') == '1'
assert detect_switch('@Marcus') == '2'
assert detect_command('!reset') == 'reset'
assert detect_command('!exit') == 'exit'
print('All router tests passed')
"

# Start the simulation (requires Ollama running with llama3.1 and Redis running)
python main.py
```

## Notes

**Prerequisites before running:**
- Ollama installed and running: `ollama serve`
- Llama 3.1 pulled: `ollama pull llama3.1`
- Redis running: `redis-server` or Docker: `docker run -p 6379:6379 redis`

**First-time setup order:**
1. `pip install -r requirements.txt`
2. `python personas_loader.py` (seeds ChromaDB — run once, safe to re-run)
3. `python main.py`

**Model size note:**
Llama 3.1 8B is the default. If persona consistency feels shallow, switch to 70B by setting `OLLAMA_MODEL=llama3.1:70b` in your environment. The 8B model requires ~8GB RAM; 70B requires ~40GB+.

**Environment overrides (optional `.env` file):**
```
OLLAMA_MODEL=llama3.1:8B
OLLAMA_BASE_URL=http://localhost:11434
REDIS_URL=redis://localhost:6379
REDIS_SESSION_TTL=86400
CHROMA_PERSIST_PATH=./.chromadb
```

**V2 features (not in scope for this POC):**
- Persona-to-persona Jubilee-style conversation (both in the same "room")
- Dynamic persona loading at runtime
- Product context switching mid-session
- Session transcript export (JSON/PDF)
- Web UI