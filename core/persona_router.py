import re
from config import PERSONA_MENTION_MAP


def detect_switch(user_input: str, mention_map: dict = None):
    """
    Returns registry key if input is a bare @mention switch command.
    mention_map overrides the static PERSONA_MENTION_MAP when provided.
    """
    map_ = mention_map if mention_map is not None else PERSONA_MENTION_MAP
    stripped = user_input.strip().lower()
    return map_.get(stripped, None)


def detect_command(user_input: str, mention_map: dict = None):
    """
    Detect reserved commands. Returns a dict:
      {"cmd": "exit"|"reset"|"observe"|"add"|"kick"|"focus"|"unfocus", ...extra keys}
    Returns None if not a command.

    mention_map: pass the full dynamic mention map (static + custom) so that
    !add/@kick/@focus resolve custom personas too. Defaults to static map.
    """
    map_ = mention_map if mention_map is not None else PERSONA_MENTION_MAP
    stripped = user_input.strip()
    lower = stripped.lower()

    if lower == "!exit":
        return {"cmd": "exit"}
    if lower == "!reset":
        return {"cmd": "reset"}
    if lower == "!observe":
        return {"cmd": "observe"}
    if lower == "!focus":
        return {"cmd": "unfocus"}

    # !add @name
    add_match = re.match(r'^!add\s+@(\w+)$', stripped, re.IGNORECASE)
    if add_match:
        name = add_match.group(1).lower()
        key = map_.get(f"@{name}")
        if key:
            return {"cmd": "add", "persona_key": key, "persona_name": name}
        return {"cmd": "add_unknown", "persona_name": name}

    # !kick @name
    kick_match = re.match(r'^!kick\s+@(\w+)$', stripped, re.IGNORECASE)
    if kick_match:
        name = kick_match.group(1).lower()
        key = map_.get(f"@{name}")
        if key:
            return {"cmd": "kick", "persona_key": key, "persona_name": name}
        return {"cmd": "kick_unknown", "persona_name": name}

    # !focus @name
    focus_match = re.match(r'^!focus\s+@(\w+)$', stripped, re.IGNORECASE)
    if focus_match:
        name = focus_match.group(1).lower()
        key = map_.get(f"@{name}")
        if key:
            return {"cmd": "focus", "persona_key": key, "persona_name": name}
        return {"cmd": "focus_unknown", "persona_name": name}

    return None
