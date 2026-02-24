#!/usr/bin/env python3
"""
main.py — Focus Group Room Terminal Entry Point

Room commands during a session:
    !add @[name]     — add a persona to the active room
    !kick @[name]    — remove a persona from the room
    !observe         — let personas discuss amongst themselves (you watch)
    !focus @[name]   — speak only to one persona; others observe
    !focus           — clear focus, all active personas respond again
    !reset           — clear session history for all personas in room
    !exit            — end session and save a Markdown summary

Persona selection menu:
    1 / 2            — default personas (Lena, Marcus)
    G                — generate a new random persona
    3, 4, …          — a saved custom persona (opens manage menu)
    1 2              — multiple keys to start with both in the room
"""
import sys
import json
import os
import re
from typing import Dict

from dotenv import load_dotenv
load_dotenv()

from core.room import (
    RoomState, PersonaContext,
    make_log_entry, add_persona_to_room, kick_persona_from_room,
    set_focus, clear_focus, append_log,
)
from core.nodes import generate_response_for_persona
from core.persona_router import detect_command
from core.summary import save_chat_summary
from core.prompt_builder import build_system_prompt
from core.topic_context import fetch_topic_context, DEFAULT_TOPIC
from core.persona_generator import (
    generate_random_persona, refine_with_description,
    edit_traits_interactive, display_persona_traits,
)
from core.persona_store import (
    load_custom_registry, save_custom_persona,
    delete_custom_persona, update_custom_persona,
    get_full_registry, get_full_mention_map,
)
from db.chroma_client import get_persona
from db.redis_client import load_history, reset_session
from config import PERSONA_REGISTRY

# ── ANSI colours ──────────────────────────────────────────────────────────────
_COLOUR_CYCLE = [
    "\033[96m",   # Bright Cyan
    "\033[93m",   # Bright Yellow
    "\033[95m",   # Bright Magenta
    "\033[92m",   # Bright Green
    "\033[94m",   # Bright Blue
    "\033[91m",   # Bright Red
    "\033[97m",   # Bright White
]
PERSONA_COLORS: Dict[str, str] = {
    str(i + 1): c for i, c in enumerate(_COLOUR_CYCLE)
}

THINK_COLOR  = "\033[90m"    # Dark Grey  – thoughts
SYSTEM_COLOR = "\033[2;37m"  # Dim White  – system messages
USER_BOLD    = "\033[1m"     # Bold
RESET        = "\033[0m"
BOLD         = "\033[1m"
DIM          = "\033[2m"

DIVIDER      = "─" * 60
DEFAULT_KEYS = {"1", "2"}


def cprint(color: str, text: str) -> None:
    print(f"{color}{text}{RESET}")


_HINTS = (
    '!observe ["topic"] [rounds]'
    "  ·  !focus @name  ·  !focus"
    "  ·  !add @name  ·  !kick @name"
    "  ·  !topic [text]  ·  !image <path>  ·  !images"
    "  ·  !clear  ·  !exit  ·  !help"
)

def print_hints() -> None:
    print(f"\n{THINK_COLOR}  {_HINTS}{RESET}")


def persona_color(key: str) -> str:
    # Assign colours by key position, cycling for keys > number of defined colours
    try:
        idx = (int(key) - 1) % len(_COLOUR_CYCLE)
        return _COLOUR_CYCLE[idx]
    except ValueError:
        return "\033[97m"


# ── Persona loading ───────────────────────────────────────────────────────────

def load_persona_context(persona_key: str) -> PersonaContext:
    reg = get_full_registry()[persona_key]
    persona_data = get_persona(reg["id"])
    system_prompt = build_system_prompt(
        persona_name=reg["name"],
        persona_document=persona_data["document"],
        metadata=persona_data["metadata"],
    )
    history = load_history(reg["redis_key"])
    return {
        "persona_key": persona_key,
        "name": reg["name"],
        "redis_key": reg["redis_key"],
        "system_prompt": system_prompt,
        "history": history,
    }


# ── Banner ────────────────────────────────────────────────────────────────────

def _print_help() -> None:
    lines = [
        DIVIDER,
        "  Room Commands",
        DIVIDER,
        "  !add @name           Add a persona to the room",
        "  !kick @name          Remove a persona from the room",
        '  !observe             Watch personas discuss (3 rounds by default)',
        '  !observe "topic"     Observe with a specific seed topic',
        "  !observe [n]         Observe for n rounds",
        "  !focus @name         Direct questions to one persona only",
        "  !focus               Clear focus — all personas respond again",
        "  !topic [text]        Change the discussion topic mid-session",
        "  !topic               Reset to the default topic",
        "  !image <path>         Share an ad image — all personas react in character",
        "  !images               List all images currently loaded in the room",
        "  !image clear          Remove all shared images from the room",
        "  !reset / !clear      Wipe conversation history for all personas",
        "  !exit                Close the room and save a Markdown summary",
        "  !help                Show this help",
        DIVIDER,
    ]
    for line in lines:
        cprint(SYSTEM_COLOR, line)


def print_banner() -> None:
    print("\n" + "=" * 60)
    print("  FOCUS GROUP SIMULATION  —  Room Mode")
    print("=" * 60)
    cprint(SYSTEM_COLOR, "  !add @name  !kick @name  !observe  !focus @name  !topic [text]  !clear  !exit  !help")
    print()


# ── Persona selection menu ────────────────────────────────────────────────────

def _print_persona_menu(full_registry: dict) -> None:
    cprint(SYSTEM_COLOR, "\n── Select personas ──────────────────────────────────────")
    cprint(BOLD, "  DEFAULT PERSONAS:")
    for key in sorted(DEFAULT_KEYS):
        if key in full_registry:
            reg = full_registry[key]
            brief = reg.get("brief", "")
            print(f"  {key}. {reg['name']}")
            if brief:
                cprint(DIM, f"     {brief}")

    custom = {k: v for k, v in full_registry.items() if k not in DEFAULT_KEYS}
    if custom:
        cprint(BOLD, "\n  YOUR PERSONAS:")
        for key in sorted(custom.keys(), key=int):
            reg = custom[key]
            brief = reg.get("brief", "")
            print(f"  {key}. {reg['name']}")
            if brief:
                cprint(DIM, f"     {brief}")

    print()
    cprint(SYSTEM_COLOR, "  G  — Generate a random persona")
    cprint(SYSTEM_COLOR, "  Q  — Quit")
    cprint(SYSTEM_COLOR, "\n  Enter numbers to start room (e.g. '1 2'),")
    cprint(SYSTEM_COLOR, "  a single custom number to manage it, or 'G':")


def choose_initial_personas() -> list:
    """
    Returns list of persona keys to put in the room.
    Returns empty list only when user quits.
    """
    while True:
        full_registry  = get_full_registry()
        mention_map    = get_full_mention_map()
        _print_persona_menu(full_registry)

        try:
            raw = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)

        if not raw:
            continue

        lower = raw.lower()

        if lower in ("q", "quit"):
            sys.exit(0)

        if lower == "g":
            key = _generate_persona_flow()
            if key:
                return [key]
            continue   # back from generate flow → re-show menu

        parts = [p.strip() for p in raw.split()]
        valid = [p for p in parts if p in full_registry]

        if not valid:
            cprint(SYSTEM_COLOR, "[No valid persona numbers. Try again.]")
            continue

        # Single custom persona → management menu
        if len(valid) == 1 and valid[0] not in DEFAULT_KEYS:
            result = _manage_custom_persona(valid[0])
            if result == "chat":
                return valid
            # 'back' or 'deleted' → loop
            continue

        return valid


# ── Generate-persona flow ─────────────────────────────────────────────────────

def _generate_persona_flow() -> str | None:
    """
    Guides the user through generating, editing, and saving a new persona.
    Returns the persona key to chat with, or None (go back).
    """
    persona = generate_random_persona()

    while True:
        print()
        display_persona_traits(persona)
        print()
        cprint(SYSTEM_COLOR, "  1. Chat with this persona")
        cprint(SYSTEM_COLOR, "  2. Edit by description")
        cprint(SYSTEM_COLOR, "  3. Edit traits individually")
        cprint(SYSTEM_COLOR, "  4. Regenerate entirely")
        cprint(SYSTEM_COLOR, "  5. Back")

        try:
            choice = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            return None

        if choice == "1":
            # Save and return key
            cprint(SYSTEM_COLOR, "\n[Saving persona...]")
            key = save_custom_persona(persona)
            cprint(persona_color(key), f"[{persona['name']} saved as persona #{key}]")
            return key

        elif choice == "2":
            try:
                desc = input("Describe changes (e.g. 'make them older and budget-conscious'):\n> ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if desc:
                persona = refine_with_description(persona, desc)

        elif choice == "3":
            updated = edit_traits_interactive(persona)
            if updated is not None:
                persona = updated

        elif choice == "4":
            persona = generate_random_persona()

        elif choice == "5":
            return None

        else:
            cprint(SYSTEM_COLOR, "[Enter 1–5]")


# ── Custom persona management menu ───────────────────────────────────────────

def _manage_custom_persona(key: str) -> str:
    """
    Show Chat / Edit / Delete / Back for a saved custom persona.
    Returns: 'chat', 'back', or 'deleted'.
    """
    while True:
        registry = load_custom_registry()
        if key not in registry:
            return "deleted"

        entry = registry[key]
        name  = entry["name"]

        cprint(SYSTEM_COLOR, f"\n{DIVIDER}")
        cprint(BOLD, f"  {name}")
        cprint(SYSTEM_COLOR, DIVIDER)
        cprint(SYSTEM_COLOR, "  1. Chat")
        cprint(SYSTEM_COLOR, "  2. Edit")
        cprint(SYSTEM_COLOR, "  3. Delete")
        cprint(SYSTEM_COLOR, "  4. Back")

        try:
            choice = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            return "back"

        if choice == "1":
            return "chat"

        elif choice == "2":
            result = _edit_custom_persona(key)
            if result == "saved":
                cprint(SYSTEM_COLOR, "[Saved. Returning to menu.]")
                # Loop back — registry name may have changed
            # 'back' → just loop back to this menu

        elif choice == "3":
            try:
                confirm = input(f"Delete {name}? This cannot be undone. (y/n): ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                continue
            if confirm == "y":
                delete_custom_persona(key)
                cprint(SYSTEM_COLOR, f"[{name} deleted.]")
                return "deleted"

        elif choice == "4":
            return "back"

        else:
            cprint(SYSTEM_COLOR, "[Enter 1–4]")


def _edit_custom_persona(key: str) -> str:
    """
    Load the persona file, run the interactive trait editor, save on 's'.
    Returns 'saved' or 'back'.
    """
    registry = load_custom_registry()
    entry    = registry[key]

    persona_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "personas", "custom", entry["file"]
    )
    try:
        with open(persona_path) as f:
            persona = json.load(f)
    except Exception as e:
        cprint(SYSTEM_COLOR, f"[Could not load persona file: {e}]")
        return "back"

    print()
    updated = edit_traits_interactive(persona)
    if updated is None:
        return "back"

    update_custom_persona(key, updated)
    return "saved"


# ── Observe mode ──────────────────────────────────────────────────────────────

_DEFAULT_OBSERVE_ROUNDS = 3


def run_observe(
    room_state: RoomState,
    observe_topic: str = "",
    observe_rounds: int = 0,
) -> RoomState:
    """
    Personas converse with each other while the moderator watches.

    observe_topic:  optional seed question/topic for the discussion
    observe_rounds: number of full rounds to run (default: _DEFAULT_OBSERVE_ROUNDS)
    Ctrl+C always stops early.
    """
    active = room_state["active_personas"]
    if len(active) < 2:
        cprint(SYSTEM_COLOR, "[Observe requires at least 2 personas in the room.]")
        return room_state

    rounds = observe_rounds if observe_rounds > 0 else _DEFAULT_OBSERVE_ROUNDS

    # Determine seed content
    seed = observe_topic
    if not seed:
        for entry in reversed(room_state["full_log"]):
            if entry["type"] == "user":
                seed = entry["content"]
                break
    if not seed:
        seed = f"Share your honest thoughts on {room_state['topic']}."

    round_label = f"{rounds} round{'s' if rounds != 1 else ''}"
    log_note = f"Observing ({round_label}){': ' + observe_topic if observe_topic else ''}."
    room_state = append_log(room_state, make_log_entry("system", log_note))

    cprint(SYSTEM_COLOR, f"\n{DIVIDER}")
    if observe_topic:
        cprint(SYSTEM_COLOR, f"  Topic: \"{observe_topic}\"")
    cprint(SYSTEM_COLOR, f"  [Observing for {round_label} — Ctrl+C to stop early]")
    cprint(SYSTEM_COLOR, f"{DIVIDER}\n")

    all_names = [
        room_state["personas"][k]["name"]
        for k in active if k in room_state["personas"]
    ]
    speaker_list = " and ".join(all_names)

    def _make_seed_prompt() -> str:
        return (
            f"[The moderator has stepped back. Only {speaker_list} are in this room — "
            f"speak only to each other. The moderator wants you to discuss: \"{seed}\". "
            f"If you disagree, don't just move on — negotiate, push back, and try to find "
            f"what's genuinely fair. Make any agreement feel earned, not polite.]"
        )

    current_prompt = _make_seed_prompt()
    round_count = 0

    try:
        while round_count < rounds:
            for pkey in active:
                ctx   = room_state["personas"][pkey]
                color = persona_color(pkey)

                print(f"{DIM}[{ctx['name']} is thinking... (round {round_count + 1}/{rounds})]{RESET}")

                thoughts, response, updated_history = generate_response_for_persona(
                    ctx, current_prompt, is_observe=True,
                    room_participants=all_names,
                    topic_context=room_state["topic_context"],
                    image_context=_build_image_context(room_state),
                )

                if thoughts:
                    cprint(THINK_COLOR, f"  \U0001f4ad {ctx['name']} thinks: {thoughts}")
                    print()

                print(f"{color}{BOLD}{ctx['name']}:{RESET} {response}")
                cprint(SYSTEM_COLOR, DIVIDER)

                updated_personas = dict(room_state["personas"])
                updated_personas[pkey] = {**ctx, "history": updated_history}
                room_state = {**room_state, "personas": updated_personas}

                room_state = append_log(room_state, make_log_entry(
                    "persona", response, pkey, ctx["name"], thoughts,
                ))

                other_names = [n for n in all_names if n != ctx["name"]]
                addressee   = " and ".join(other_names) if other_names else "the other participant"
                current_prompt = (
                    f"[{ctx['name']} just said to {addressee}]: \"{response}\"\n"
                    f"[You are {addressee}. Respond directly to {ctx['name']}. "
                    f"Only {speaker_list} are in this room. Keep the discussion on: \"{seed}\"]"
                )

            round_count += 1

    except KeyboardInterrupt:
        cprint(SYSTEM_COLOR, "\n[Observation stopped.]")

    return room_state


# ── Image helpers ──────────────────────────────────────────────────────────────

def _build_image_context(room_state: RoomState) -> str:
    """Build the formatted image context string from loaded images in room_state."""
    if not room_state.get("image_contexts"):
        return ""
    try:
        from services.image_analysis.service import get_loaded_images, format_for_personas
        images = get_loaded_images()
        return format_for_personas(images) if images else ""
    except Exception:
        return ""


def _load_image(source: str, room_state: RoomState) -> RoomState:
    """Read a local image file, analyze it, and add it to room state."""
    try:
        from services.image_analysis.service import analyze_image, ImageTooLargeError, UnsupportedFormatError, AnalysisError
    except ImportError as e:
        cprint(SYSTEM_COLOR, f"[Image analysis service not available: {e}]")
        return room_state

    path = os.path.expanduser(source)
    if not os.path.exists(path):
        cprint(SYSTEM_COLOR, f"[File not found: {path}]")
        return room_state

    display_name = os.path.basename(path)
    cprint(SYSTEM_COLOR, f"[Analyzing image: {display_name}...]")

    try:
        loaded, cached = analyze_image(path)
    except ImageTooLargeError as e:
        cprint(SYSTEM_COLOR, f"[{e}]")
        return room_state
    except UnsupportedFormatError as e:
        cprint(SYSTEM_COLOR, f"[{e}]")
        return room_state
    except AnalysisError as e:
        cprint(SYSTEM_COLOR, f"[Image analysis failed: {e}]")
        return room_state

    # Update room_state image list (avoid duplicates by hash)
    existing = room_state.get("image_contexts", [])
    if not any(img["hash"] == loaded.hash for img in existing):
        existing = existing + [{"filename": loaded.filename, "hash": loaded.hash}]

    updated = {**room_state, "image_contexts": existing}
    status = "cached" if cached else "analyzed"
    cprint(SYSTEM_COLOR, f"[Image {status} ({len(existing)} image{'s' if len(existing) != 1 else ''} in room) — all personas are now briefed on: {display_name}]")
    updated = append_log(updated, make_log_entry("system", f"Image loaded: {display_name}"))
    return updated


def _print_image_list(room_state: RoomState) -> None:
    """Print all images currently loaded in the room."""
    images = room_state.get("image_contexts", [])
    if not images:
        cprint(SYSTEM_COLOR, "[No images loaded. Use !image <path> to share one.]")
        return
    cprint(SYSTEM_COLOR, f"\n{DIVIDER}")
    cprint(SYSTEM_COLOR, f"  Images in room ({len(images)}):")
    for i, img in enumerate(images, start=1):
        cprint(SYSTEM_COLOR, f"  {i}. {img['filename']}  [{img['hash'][:8]}...]")
    cprint(SYSTEM_COLOR, DIVIDER)


# ── Main loop ─────────────────────────────────────────────────────────────────

def _prompt_topic() -> tuple[str, str]:
    """Ask the user for a discussion topic before entering the room."""
    cprint(SYSTEM_COLOR, f"\n{DIVIDER}")
    cprint(SYSTEM_COLOR, "  Discussion topic (press Enter for PlayStation 5):")
    cprint(SYSTEM_COLOR, "  Examples: Nike Air Max · Miele espresso machines · Stoic philosophy")
    try:
        raw = input(f"\n{DIM}Topic{RESET} > ").strip()
    except (KeyboardInterrupt, EOFError):
        raw = ""
    topic = raw if raw else DEFAULT_TOPIC
    topic_context = fetch_topic_context(topic)
    return topic, topic_context


def _ensure_ollama_key() -> None:
    """Prompt the user to paste their Ollama API key if it isn't set."""
    if os.getenv("OLLAMA_API_KEY"):
        return
    cprint(SYSTEM_COLOR, "\n  [!image requires an Ollama API key — none found]")
    cprint(SYSTEM_COLOR, "  Get one at: https://ollama.com/settings/keys")
    cprint(SYSTEM_COLOR, "  Paste your key below, or press Enter to skip (image commands will be unavailable):\n")
    key = input("  OLLAMA_API_KEY: ").strip()
    if key:
        os.environ["OLLAMA_API_KEY"] = key
        # Persist to .env so the next run picks it up automatically
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        try:
            with open(env_path, "a") as f:
                f.write(f"\nOLLAMA_API_KEY={key}\n")
            cprint(SYSTEM_COLOR, "  [Key saved to .env]\n")
        except OSError:
            cprint(SYSTEM_COLOR, "  [Key set for this session only — could not write to .env]\n")
    else:
        cprint(SYSTEM_COLOR, "  [Skipped — !image will not be available this session]\n")


def run() -> None:
    print_banner()
    _ensure_ollama_key()

    initial_keys = choose_initial_personas()
    topic, topic_context = _prompt_topic()

    personas: Dict[str, PersonaContext] = {}
    full_reg = get_full_registry()
    for key in initial_keys:
        cprint(SYSTEM_COLOR, f"[Loading {full_reg[key]['name']}...]")
        personas[key] = load_persona_context(key)

    room_state: RoomState = {
        "active_personas": initial_keys,
        "focus_persona": "",
        "mode": "chat",
        "personas": personas,
        "full_log": [],
        "topic": topic,
        "topic_context": topic_context,
        "image_contexts": [],
    }

    names = [personas[k]["name"] for k in initial_keys]
    cprint(SYSTEM_COLOR, f"\n{DIVIDER}")
    cprint(SYSTEM_COLOR, f"  Room: {', '.join(names)} ready")
    cprint(SYSTEM_COLOR, f"  Topic: {room_state['topic']}")
    cprint(SYSTEM_COLOR, f"{DIVIDER}\n")

    while True:
        active      = room_state["active_personas"]
        focus       = room_state["focus_persona"]
        mention_map = get_full_mention_map()   # refresh each turn for newly added personas

        if focus and focus in room_state["personas"]:
            focused_name = room_state["personas"][focus]["name"]
            label = f"{USER_BOLD}You \u2192 {focused_name}{RESET}"
        else:
            room_names = [
                room_state["personas"][k]["name"]
                for k in active if k in room_state["personas"]
            ]
            label = f"{USER_BOLD}You \u2192 [{', '.join(room_names)}]{RESET}"

        try:
            user_input = input(f"\n{label}: ").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "!exit"

        if not user_input:
            continue

        # ── Command dispatch ──────────────────────────────────────────────────
        cmd_result = detect_command(user_input, mention_map=mention_map)
        if cmd_result:
            cmd = cmd_result["cmd"]

            if cmd == "exit":
                persona_names = [
                    ctx["name"]
                    for pkey, ctx in room_state["personas"].items()
                    if pkey in active
                ]
                cprint(SYSTEM_COLOR, "\n[Closing room...]")
                if room_state["full_log"]:
                    cprint(SYSTEM_COLOR, "[Generating summary, please wait...]")
                    filepath = save_chat_summary(room_state["full_log"], persona_names)
                    cprint(SYSTEM_COLOR, f"[Summary saved to: {filepath}]")
                else:
                    cprint(SYSTEM_COLOR, "[No conversation to save.]")
                cprint(SYSTEM_COLOR, "[Room closed. Goodbye.]\n")
                sys.exit(0)

            elif cmd == "reset":
                for pkey in active:
                    ctx = room_state["personas"][pkey]
                    reset_session(ctx["redis_key"])
                    updated_personas = dict(room_state["personas"])
                    updated_personas[pkey] = {**ctx, "history": []}
                    room_state = {**room_state, "personas": updated_personas}
                cprint(SYSTEM_COLOR, "[Memory cleared — all personas reset to default.]")

            elif cmd == "observe":
                room_state = run_observe(
                    room_state,
                    observe_topic=cmd_result.get("observe_topic", ""),
                    observe_rounds=cmd_result.get("observe_rounds", 0),
                )
                print_hints()

            elif cmd == "focus":
                pkey  = cmd_result["persona_key"]
                pname = cmd_result["persona_name"]
                if pkey not in active:
                    cprint(SYSTEM_COLOR, f"[{pname.capitalize()} is not in the room. Use !add @{pname} first.]")
                else:
                    room_state = set_focus(room_state, pkey)
                    ctx = room_state["personas"][pkey]
                    others = [
                        room_state["personas"][k]["name"]
                        for k in active if k != pkey and k in room_state["personas"]
                    ]
                    obs = f" ({', '.join(others)} {'is' if len(others) == 1 else 'are'} observing)" if others else ""
                    cprint(SYSTEM_COLOR, f"[Focused on {ctx['name']}{obs}.]")

            elif cmd == "unfocus":
                room_state = clear_focus(room_state)
                cprint(SYSTEM_COLOR, "[Focus cleared — all active personas will respond.]")

            elif cmd == "add":
                pkey  = cmd_result["persona_key"]
                pname = cmd_result["persona_name"]
                full_reg = get_full_registry()
                if pkey in active:
                    cprint(SYSTEM_COLOR, f"[{pname.capitalize()} is already in the room.]")
                else:
                    cprint(SYSTEM_COLOR, f"[Loading {full_reg[pkey]['name']}...]")
                    if pkey not in room_state["personas"]:
                        room_state["personas"][pkey] = load_persona_context(pkey)
                    room_state = add_persona_to_room(room_state, pkey)
                    ctx = room_state["personas"][pkey]
                    cprint(persona_color(pkey), f"[{ctx['name']} has joined the room.]")
                    room_state = append_log(room_state, make_log_entry(
                        "system", f"{ctx['name']} joined the room.",
                    ))

            elif cmd == "kick":
                pkey  = cmd_result["persona_key"]
                pname = cmd_result["persona_name"]
                if pkey not in active:
                    cprint(SYSTEM_COLOR, f"[{pname.capitalize()} is not in the room.]")
                else:
                    ctx = room_state["personas"][pkey]
                    room_state = kick_persona_from_room(room_state, pkey)
                    cprint(persona_color(pkey), f"[{ctx['name']} has left the room.]")
                    room_state = append_log(room_state, make_log_entry(
                        "system", f"{ctx['name']} left the room.",
                    ))

            elif cmd == "topic_set":
                new_topic = cmd_result["topic"]
                cprint(SYSTEM_COLOR, f"[Switching topic to: {new_topic}]")
                new_ctx = fetch_topic_context(new_topic)
                room_state = {**room_state, "topic": new_topic, "topic_context": new_ctx}
                cprint(SYSTEM_COLOR, f"[Context loaded. Personas are now briefed on: {new_topic}]")
                room_state = append_log(room_state, make_log_entry(
                    "system", f"Topic changed to: {new_topic}",
                ))

            elif cmd == "topic_clear":
                from core.topic_context import DEFAULT_TOPIC, fetch_topic_context as _ftc
                room_state = {**room_state, "topic": DEFAULT_TOPIC, "topic_context": _ftc(DEFAULT_TOPIC)}
                cprint(SYSTEM_COLOR, f"[Topic reset to default: {DEFAULT_TOPIC}]")

            elif cmd == "image_load":
                source = cmd_result["source"]
                room_state = _load_image(source, room_state)

            elif cmd == "image_clear":
                from services.image_analysis.image_redis import clear_index
                clear_index()
                room_state = {**room_state, "image_contexts": []}
                cprint(SYSTEM_COLOR, "[All images removed from the room.]")
                room_state = append_log(room_state, make_log_entry("system", "Image context cleared."))

            elif cmd == "image_list":
                _print_image_list(room_state)

            elif cmd == "help":
                _print_help()

            elif cmd == "did_you_mean":
                suggestion = cmd_result["suggestion"]
                cprint(SYSTEM_COLOR, f"[Did you mean: {suggestion}]")

            elif cmd == "usage_hint":
                cprint(SYSTEM_COLOR, f"[{cmd_result['hint']}]")

            elif cmd in ("add_unknown", "kick_unknown", "focus_unknown"):
                pname = cmd_result["persona_name"]
                known = ", ".join(f"@{k[1:]}" for k in mention_map)
                cprint(SYSTEM_COLOR, f"[Unknown persona @{pname}. Known: {known}]")

            continue

        # ── Inline !image embedded in message ─────────────────────────────────
        # e.g. "what do you think? !image '/path/to/ad.png'"
        inline_img = re.search(r'!image\s+(.+)', user_input, re.IGNORECASE)
        if inline_img:
            raw_source = inline_img.group(1).strip()
            if len(raw_source) >= 2 and raw_source[0] == raw_source[-1] and raw_source[0] in ("'", '"'):
                raw_source = raw_source[1:-1]
            room_state = _load_image(raw_source, room_state)
            user_input = user_input[:inline_img.start()].strip()
            if not user_input:
                continue

        # ── Normal conversation ───────────────────────────────────────────────
        if not active:
            cprint(SYSTEM_COLOR, "[No personas in the room. Use !add @name.]")
            continue

        room_state = append_log(room_state, make_log_entry("user", user_input))

        responders = [focus] if (focus and focus in active) else list(active)
        all_room_names = [
            room_state["personas"][k]["name"]
            for k in active if k in room_state["personas"]
        ]

        for pkey in responders:
            ctx   = room_state["personas"][pkey]
            color = persona_color(pkey)

            print(f"\n{DIM}[{ctx['name']} is thinking...]{RESET}")
            thoughts, response, updated_history = generate_response_for_persona(
                ctx, user_input, is_observe=False,
                room_participants=all_room_names,
                topic_context=room_state["topic_context"],
                image_context=_build_image_context(room_state),
            )

            if thoughts:
                cprint(THINK_COLOR, f"  \U0001f4ad {thoughts}")
                print()

            print(f"{color}{BOLD}{ctx['name']}:{RESET} {response}")
            cprint(SYSTEM_COLOR, DIVIDER)

            updated_personas = dict(room_state["personas"])
            updated_personas[pkey] = {**ctx, "history": updated_history}
            room_state = {**room_state, "personas": updated_personas}

            room_state = append_log(room_state, make_log_entry(
                "persona", response, pkey, ctx["name"], thoughts,
            ))

        if focus:
            observers = [
                room_state["personas"][k]["name"]
                for k in active if k != focus and k in room_state["personas"]
            ]
            if observers:
                verb = "is" if len(observers) == 1 else "are"
                cprint(SYSTEM_COLOR, f"  [{', '.join(observers)} {verb} observing]")

        print_hints()


if __name__ == "__main__":
    run()
