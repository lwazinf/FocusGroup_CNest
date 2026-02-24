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
      {"cmd": "exit"|"reset"|"observe"|"add"|"kick"|"focus"|"unfocus"|"help"
              |"did_you_mean"|"usage_hint", ...extra keys}
    Returns None if not a command.

    mention_map: pass the full dynamic mention map (static + custom) so that
    !add/!kick/!focus resolve custom personas too. Defaults to static map.
    """
    map_ = mention_map if mention_map is not None else PERSONA_MENTION_MAP
    stripped = user_input.strip()
    lower = stripped.lower()

    # Exit — match !exit or !quit (with or without trailing garbage)
    if re.match(r'^!exit', lower):
        return {"cmd": "exit"}
    if re.match(r'^!quit', lower):
        return {"cmd": "exit"}

    # Fuzzy catch: user typed exit/quit without the !
    if lower in ("exit", "quit"):
        return {"cmd": "did_you_mean", "suggestion": "!exit"}

    if lower in ("!reset", "!clear"):
        return {"cmd": "reset"}

    if lower in ("!help", "!commands", "!?"):
        return {"cmd": "help"}

    # !observe with optional "topic" and/or number of rounds
    # Accepted forms:
    #   !observe
    #   !observe "What was the best PS generation?"
    #   !observe 5
    #   !observe "Some question" 5
    if re.match(r'^!observe', stripped, re.IGNORECASE):
        rest = stripped[len("!observe"):].strip()
        obs_topic = None
        obs_rounds = None

        # Extract quoted topic string
        quote_match = re.search(r'"([^"]+)"', rest)
        if quote_match:
            obs_topic = quote_match.group(1).strip()
            rest = (rest[:quote_match.start()] + rest[quote_match.end():]).strip()

        # Extract trailing integer (rounds, minimum 1)
        num_match = re.search(r'\b(\d+)\b', rest)
        if num_match:
            obs_rounds = max(1, int(num_match.group(1)))

        result: dict = {"cmd": "observe"}
        if obs_topic:
            result["observe_topic"] = obs_topic
        if obs_rounds:
            result["observe_rounds"] = obs_rounds
        return result

    if lower == "!focus":
        return {"cmd": "unfocus"}

    # !topic [text] — set or clear discussion topic
    if lower == "!topic":
        return {"cmd": "topic_clear"}
    topic_match = re.match(r'^!topic\s+(.+)$', stripped, re.IGNORECASE)
    if topic_match:
        return {"cmd": "topic_set", "topic": topic_match.group(1).strip()}

    # !add @name
    add_match = re.match(r'^!add\s+@(\w+)$', stripped, re.IGNORECASE)
    if add_match:
        name = add_match.group(1).lower()
        key = map_.get(f"@{name}")
        if key:
            return {"cmd": "add", "persona_key": key, "persona_name": name}
        return {"cmd": "add_unknown", "persona_name": name}

    # !add name (missing @) — suggest correct form
    add_no_at = re.match(r'^!add\s+(\w+)$', stripped, re.IGNORECASE)
    if add_no_at:
        name = add_no_at.group(1).lower()
        return {"cmd": "did_you_mean", "suggestion": f"!add @{name}"}

    # bare !add — show usage
    if lower == "!add":
        return {"cmd": "usage_hint", "hint": "Usage: !add @name"}

    # !kick @name
    kick_match = re.match(r'^!kick\s+@(\w+)$', stripped, re.IGNORECASE)
    if kick_match:
        name = kick_match.group(1).lower()
        key = map_.get(f"@{name}")
        if key:
            return {"cmd": "kick", "persona_key": key, "persona_name": name}
        return {"cmd": "kick_unknown", "persona_name": name}

    # !kick name (missing @) — suggest correct form
    kick_no_at = re.match(r'^!kick\s+(\w+)$', stripped, re.IGNORECASE)
    if kick_no_at:
        name = kick_no_at.group(1).lower()
        return {"cmd": "did_you_mean", "suggestion": f"!kick @{name}"}

    # bare !kick — show usage
    if lower == "!kick":
        return {"cmd": "usage_hint", "hint": "Usage: !kick @name"}

    # !focus @name
    focus_match = re.match(r'^!focus\s+@(\w+)$', stripped, re.IGNORECASE)
    if focus_match:
        name = focus_match.group(1).lower()
        key = map_.get(f"@{name}")
        if key:
            return {"cmd": "focus", "persona_key": key, "persona_name": name}
        return {"cmd": "focus_unknown", "persona_name": name}

    # !focus name (missing @) — suggest correct form
    focus_no_at = re.match(r'^!focus\s+(\w+)$', stripped, re.IGNORECASE)
    if focus_no_at:
        name = focus_no_at.group(1).lower()
        return {"cmd": "did_you_mean", "suggestion": f"!focus @{name}"}

    # !image <filepath> — load and analyze an image
    # !image clear      — remove all images from the room
    image_match = re.match(r'^!image\s+(.+)$', stripped, re.IGNORECASE)
    if image_match:
        source = image_match.group(1).strip()
        # Strip surrounding single or double quotes (paths with spaces are often quoted)
        if len(source) >= 2 and source[0] == source[-1] and source[0] in ("'", '"'):
            source = source[1:-1]
        if source.lower() == "clear":
            return {"cmd": "image_clear"}
        return {"cmd": "image_load", "source": source}

    # bare !image — usage hint
    if lower == "!image":
        return {"cmd": "usage_hint", "hint": "Usage: !image <filepath>  or  !image clear"}

    # !images — list all loaded images
    if lower == "!images":
        return {"cmd": "image_list"}

    return None
