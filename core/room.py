from typing import TypedDict, List, Dict
from datetime import datetime


class PersonaContext(TypedDict):
    persona_key: str      # e.g. '1', '2'
    name: str
    redis_key: str
    system_prompt: str
    history: List[dict]   # [{role: "user"|"assistant", content: str}]


class RoomState(TypedDict):
    active_personas: List[str]          # ordered list of persona keys in room
    focus_persona: str                  # '' means all active, else a specific persona_key
    mode: str                           # 'chat' or 'observe'
    personas: Dict[str, PersonaContext] # persona_key -> PersonaContext
    full_log: List[dict]                # complete log with thoughts
    topic: str                          # current discussion topic (default: "PlayStation 5")
    topic_context: str                  # fetched context block for topic
    image_contexts: List[dict]          # list of {filename, hash} for images loaded this session
    # Each log entry: {timestamp, type, persona_key, persona_name, thoughts, content}


def make_log_entry(entry_type: str, content: str, persona_key: str = "", persona_name: str = "", thoughts: str = "") -> dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "type": entry_type,      # "user", "persona", "system"
        "persona_key": persona_key,
        "persona_name": persona_name,
        "thoughts": thoughts,
        "content": content
    }


def add_persona_to_room(state: RoomState, persona_key: str) -> RoomState:
    """Add a persona key to active_personas if not already present."""
    if persona_key not in state["active_personas"]:
        new_active = state["active_personas"] + [persona_key]
        return {**state, "active_personas": new_active}
    return state


def kick_persona_from_room(state: RoomState, persona_key: str) -> RoomState:
    """Remove a persona key from active_personas. Also clear focus if it was on that persona."""
    new_active = [k for k in state["active_personas"] if k != persona_key]
    new_focus = "" if state["focus_persona"] == persona_key else state["focus_persona"]
    return {**state, "active_personas": new_active, "focus_persona": new_focus}


def set_focus(state: RoomState, persona_key: str) -> RoomState:
    return {**state, "focus_persona": persona_key}


def clear_focus(state: RoomState) -> RoomState:
    return {**state, "focus_persona": ""}


def append_log(state: RoomState, entry: dict) -> RoomState:
    new_log = state["full_log"] + [entry]
    return {**state, "full_log": new_log}
