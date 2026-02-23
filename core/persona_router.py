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
