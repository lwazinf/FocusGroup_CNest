# Focus Group Simulation

A terminal-based AI focus group. You're the moderator — invite synthetic personas into a room, ask questions about any product or topic, and watch them respond in character. Sessions are saved as Markdown summaries.

---

## Quick Start

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | 3.12 recommended |
| [Ollama](https://ollama.com) | Local LLM inference |
| Redis | Session history storage |
| `llama3.1:8b` pulled | `ollama pull llama3.1:8b` |

### Install

```bash
git clone <repo-url>
cd FocusGroup

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Seed personas (first time only)

```bash
python personas_loader.py
```

### Start services

```bash
ollama serve      # in one terminal
redis-server      # in another terminal
```

### Run

```bash
source .venv/bin/activate
python main.py
```

---

## How It Works

1. At startup, choose one or more personas to invite into the room.
2. Set a discussion topic (default: PlayStation 5) or press Enter for the default.
3. Ask questions — all active personas respond in character.
4. Use room commands to control who speaks and what they discuss.
5. Type `!exit` to close the room and save a Markdown summary.

---

## Room Commands

Type `!help` at any time while the app is running to see all commands.

| Command | Description |
|---|---|
| `!add @name` | Add a persona to the room |
| `!kick @name` | Remove a persona from the room |
| `!observe` | Watch personas discuss with each other (3 rounds) |
| `!observe "topic"` | Observe with a specific seed topic |
| `!observe [n]` | Observe for n rounds |
| `!focus @name` | Direct all questions to one persona only |
| `!focus` | Clear focus — all active personas respond |
| `!topic [text]` | Change the discussion topic mid-session |
| `!topic` | Reset to the default topic |
| `!reset` / `!clear` | Wipe conversation history for all active personas |
| `!exit` | Close the room and save a Markdown summary |
| `!help` | Show all commands in-app |

**Available personas:** `@lena`, `@marcus`

---

## Personas

### Lena — `@lena`

| Attribute | Value |
|---|---|
| Age | 23 |
| Gender | Female |
| Nationality | German |
| Location | Cape Town, South Africa |
| Role | Transfer student + YouTube content creator |
| Ecosystem | Android |
| Gaming | Deeply immersed, competitive |

Evaluates products through a **performance and content-creation lens**. Spec-driven, analytical, skeptical of closed ecosystems. Direct and opinionated.

---

### Marcus — `@marcus`

| Attribute | Value |
|---|---|
| Age | 38 |
| Gender | Male |
| Marital status | Married, children under 12 |
| Profession | Digital Product Designer |
| Ecosystem | Apple |
| Gaming | Cultural observer, not a core gamer |

Evaluates products through **family utility, design quality, and long-term value**. Deliberate, resistant to hype. Assesses products like design objects.

---

## Example Session

```
Who would you like to start with?
  1. Lena
  2. Marcus

Enter numbers separated by spaces (e.g. '1 2' for both): 1 2

[Loading Lena...]
[Loading Marcus...]

──────────────────────────────────────────────────────────
  Room: Lena, Marcus ready
  Topic: PlayStation 5
──────────────────────────────────────────────────────────

You → [Lena, Marcus]: Would you buy a PS5?

[Lena is thinking... (round 1/1)]
  💭 The closed ecosystem thing is always my first reaction...

Lena: Honestly, the hardware is impressive but the closed ecosystem
      puts me off. I can't mod, I can't customise, it feels like a
      walled garden I'm paying $499 to enter.
──────────────────────────────────────────────────────────

You → [Lena, Marcus]: !observe

  [Observing for 3 rounds — Ctrl+C to stop early]

[Lena is thinking... (round 1/3)]
  💭 I wonder what Marcus actually thinks about the exclusives...

Lena: Marcus, do you think the PS5 exclusives justify the price for
      someone who isn't a core gamer?
──────────────────────────────────────────────────────────

You → [Lena, Marcus]: !focus @lena

[Focused on Lena. (Marcus is observing).]

You → Lena: What would make you actually pull the trigger on buying one?

[Lena is thinking...]

Lena: Probably if Sony opened up cross-platform play properly and
      gave me more control over my save data.
──────────────────────────────────────────────────────────
  [Marcus is observing]

You → Lena: !exit

[Closing room...]
[Generating summary, please wait...]
[Summary saved to: chat_summaries/chat_20260223_141022.md]
[Room closed. Goodbye.]
```

---

## Chat Summaries

When you type `!exit`, the app:

1. Generates an executive summary of the full session via the LLM
2. Saves a Markdown file to `chat_summaries/chat_YYYYMMDD_HHMMSS.md`

The file includes a 3–5 paragraph executive summary and the full timestamped chat log with each persona's visible thinking.

---

## Adding a New Persona

1. Copy `personas/persona_template.json` and fill it in.
2. Add an entry to `PERSONA_REGISTRY` in `config.py`.
3. Add the `@mention` mapping to `PERSONA_MENTION_MAP` in `config.py`.
4. Re-run `python personas_loader.py`.

See [specs/focus_group_poc.md](specs/focus_group_poc.md) for the full persona schema and step-by-step instructions.

---

## Configuration

Settings live in `config.py` or can be overridden via environment variables. See [specs/focus_group_poc.md](specs/focus_group_poc.md) for the full reference.

---

## Running Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Tests cover room state management, command parsing, thinking extraction, and Markdown output — no live Ollama, Redis, or ChromaDB required.

---

*Last updated: February 2026*
