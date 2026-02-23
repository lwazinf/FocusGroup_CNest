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
from core.nodes import SessionState, assemble_context
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

        # Normal conversation turn — run the graph
        state = graph.invoke({**state, "user_input": user_input})

        print(f"\n{state['persona_name']}: {state['response']}\n")
        print(DIVIDER)

if __name__ == "__main__":
    run()
