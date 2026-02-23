# Focus Group Simulation
### v2 | Terminal-Based | Room Mode | PS5 Product Context

A terminal AI focus-group simulation. A human moderator (you) runs a room of synthetic personas who discuss the **PlayStation 5** in character. Personas can converse with each other, be added or removed mid-session, and their thinking process is visible. Every session can be exported as a Markdown summary.

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

### Seed the persona database

This only needs to be run once (or after adding new personas):

```bash
source .venv/bin/activate
python personas_loader.py
```

### Start Ollama and Redis

```bash
ollama serve           # in one terminal (or run as a background service)
redis-server           # in another terminal (or use a system service)
```

### Run

```bash
source .venv/bin/activate
python main.py
```

---

## Room Commands

Once the simulation is running, these commands are available at the prompt:

| Command | What it does |
|---|---|
| `!add @name` | Add a persona to the active room |
| `!kick @name` | Remove a persona from the room |
| `!observe` | Step back and watch the personas discuss with each other (3 rounds, Ctrl+C to stop early) |
| `!focus @name` | Speak directly to one persona — others stay silent and observe |
| `!focus` | Clear focus — all active personas respond again |
| `!reset` | Wipe Redis conversation history for all active personas |
| `!exit` | End the session and save a Markdown summary to `chat_summaries/` |

**Available persona names:** `@lena`, `@marcus`

### Example session

```
Who would you like to start with?
  1. Lena
  2. Marcus

Enter numbers separated by spaces (e.g. '1 2' for both): 1 2

[Loading Lena...]
[Loading Marcus...]

──────────────────────────────────────────────────────────
  Room: Lena, Marcus ready
──────────────────────────────────────────────────────────

You → [Lena, Marcus]: Would you buy a PS5?

[Lena is thinking...]
  💭 The closed ecosystem thing is always my first reaction...

Lena: Honestly, the hardware is impressive but the closed ecosystem
      puts me off. I can't mod, I can't customise, it feels like a
      walled garden I'm paying $499 to enter.
──────────────────────────────────────────────────────────

[Marcus is thinking...]
  💭 Design-wise it's polarising. I'd need to think about family utility...

Marcus: I've looked at it in stores. The design is very aggressive —
        it doesn't feel refined. But my kids keep asking, so I'm weighing
        the family angle.
──────────────────────────────────────────────────────────

You → [Lena, Marcus]: !observe

  [Observing — press Ctrl+C to stop]

[Lena is thinking...]
  💭 I wonder what Marcus actually thinks about the exclusives...

Lena: Marcus, do you think the PS5 exclusives justify the price for
      someone who isn't a core gamer?
──────────────────────────────────────────────────────────

[Marcus is thinking...]
  💭 Good question. Spider-Man and Gran Turismo are the obvious ones...

Marcus: Honestly, Gran Turismo is the one that got my attention.
        The craftsmanship in that game is something I respect. But
        for the price of the console alone? It's a stretch.
──────────────────────────────────────────────────────────

You → [Lena, Marcus]: !focus @lena

[Focused on Lena. (Marcus is observing).]

You → Lena: What would make you actually pull the trigger on buying one?

[Lena is thinking...]
  💭 Open ecosystem, or at least better mod/cross-platform support...

Lena: Probably if Sony opened up cross-platform play properly and
      gave me more control over my save data. Or if a killer exclusive
      dropped that I genuinely couldn't experience anywhere else.
──────────────────────────────────────────────────────────
  [Marcus is observing]

You → Lena: !exit

[Generating session summary... please wait]
[Summary saved to: chat_summaries/chat_20260223_141022.md]
[Session ended. Goodbye.]
```

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

Evaluates the PS5 through a **performance and content-creation lens**. Spec-driven, analytical, skeptical of closed ecosystems. Will compare against PC and Android. Her English has a slight German accent. Direct and opinionated.

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

Evaluates the PS5 through **family utility, design quality, and long-term value**. Deliberate, resistant to hype. Assesses products like design objects — does it feel crafted, does it last. Uses gaming as a medium to share his interests in cars and anime with his kids.

---

## Adding a New Persona

1. Copy `personas/persona_template.json` and fill it in.
2. Add an entry to `PERSONA_REGISTRY` in `config.py`:
   ```python
   "3": {
       "name": "Yuki",
       "id": "persona_yuki_id",
       "file": "yuki.json",
       "redis_key": "session:yuki:messages"
   }
   ```
3. Add the `@mention` mapping to `PERSONA_MENTION_MAP` in `config.py`:
   ```python
   "@yuki": "3"
   ```
4. Re-run `python personas_loader.py` to seed ChromaDB.
5. Yuki is now available as `!add @yuki`.

---

## Chat Summaries

When you type `!exit`, the simulation:

1. Calls the LLM to write an **executive summary** of the session
2. Saves a Markdown file to `chat_summaries/chat_YYYYMMDD_HHMMSS.md`

The file structure is:

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

## Architecture

### Stack

| Layer | Technology | Purpose |
|---|---|---|
| LLM Inference | Ollama + Llama 3.1 8B | Local, cost-free inference |
| Persona Storage | ChromaDB | Persona documents and metadata |
| Session Memory | Redis | Conversation history per persona |
| Orchestration | LangGraph | Legacy graph (context assembly + response) |
| Interface | Terminal (CLI) | Human moderator input/output |

### Key modules

```
FocusGroup/
│
├── main.py                  ← Entry point — room loop, all commands, colours
│
├── core/
│   ├── room.py              ← RoomState / PersonaContext types + room management fns
│   ├── nodes.py             ← LLM call, thinking extraction, room-constraint injection
│   ├── persona_router.py    ← Command parsing (!add, !kick, !focus, !observe, !exit…)
│   ├── summary.py           ← Chat summary generation + Markdown file writer
│   ├── prompt_builder.py    ← System prompt assembly (persona identity + PS5 context)
│   └── graph.py             ← LangGraph definition (used for single-persona legacy flow)
│
├── db/
│   ├── chroma_client.py     ← ChromaDB init, upsert, retrieve
│   └── redis_client.py      ← Redis session read / write / reset helpers
│
├── context/
│   └── ps5_context.py       ← Static PS5 product context block injected into every prompt
│
├── personas/
│   ├── female_23.json       ← Lena's persona definition
│   ├── male_38.json         ← Marcus's persona definition
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

### How the room constraint works

Each persona's system prompt has four layers assembled at load time:

```
[1] Persona identity      — who they are, their history, values
[2] Behavioural anchors   — hesitation triggers, motivations, decision style
[3] PS5 product context   — what the PS5 is, comparison points
[4] Rules of engagement   — stay in character, be candid, 2–4 paragraphs max
```

On every LLM call, two more blocks are appended at runtime:

```
[5] Room constraint       — "The ONLY people present are X and Y. Do not address anyone else."
[6] Thinking instruction  — "Wrap internal reasoning in <think>…</think> before responding."
```

Block 5 prevents the model from hallucinating participants who aren't in the room.

### Thinking display

If the model wraps its reasoning in `<think>…</think>` tags, it is:
- **Stripped from the visible response** (persona only says what they'd say out loud)
- **Shown in the terminal in dark grey** before the response
- **Logged and included** in the chat summary under each persona's entry

---

## Configuration

All settings are in `config.py` or via environment variables:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.1:8b` | Model name for Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `REDIS_SESSION_TTL` | `86400` (24h) | History TTL in seconds |
| `CHROMA_PERSIST_PATH` | `./.chromadb` | ChromaDB storage path |

---

## Running Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Tests cover room state management, command parsing, thinking extraction, and Markdown output — no live Ollama, Redis, or ChromaDB required.

---

*Last updated: February 2026*
