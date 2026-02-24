# FocusGroup

A terminal-based AI focus group. You're the moderator — invite synthetic personas into a room, ask them about any product or topic, and watch them respond in character. Load an ad image and they'll react to it through their own lens. Sessions are saved as Markdown summaries.

---

## Quick Start

### 1. Clone the repo

```bash
git clone <repo-url>
cd FocusGroup
```

### 2. Install everything

```bash
chmod +x setup.sh
./setup.sh
```

`setup.sh` will:
- Check Python 3.11+, Ollama, and Redis are available
- Create a `.venv` virtual environment and install all Python packages
- Pull the `llama3.1:8b` Ollama model if not already downloaded
- Create a `.env` file from `.env.example`
- Seed the persona database (ChromaDB)

> **First time?** After setup, open `.env` and add your `OLLAMA_API_KEY` if you want to use the `!image` command. [Get a key here.](https://ollama.com/settings/keys)

### 3. Start services

```bash
ollama serve      # terminal 1
redis-server      # terminal 2
```

### 4. Run

```bash
# bash / zsh
source .venv/bin/activate

# fish
source .venv/bin/activate.fish

python main.py
```

---

## Requirements

| Dependency | Why it's needed | Install |
|---|---|---|
| Python 3.11+ | Runs the app | [python.org](https://python.org) |
| [Ollama](https://ollama.com) | Local LLM inference for personas | [ollama.com/download](https://ollama.com/download) |
| `llama3.1:8b` | The model personas use | `ollama pull llama3.1:8b` |
| Redis | Session history and image cache | `brew install redis` / `apt install redis-server` |
| Ollama API key | Image analysis via `!image` (optional) | [ollama.com/settings/keys](https://ollama.com/settings/keys) |

---

## Manual Setup

If you prefer step-by-step over the install script:

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate      # or: source .venv/bin/activate.fish

# Install dependencies
pip install -r requirements.txt

# Copy environment template and fill in your values
cp .env.example .env

# Pull the Ollama model
ollama pull llama3.1:8b

# Seed personas into ChromaDB (first time only)
python personas_loader.py
```

---

## How It Works

1. At startup, choose which personas to invite into the room.
2. Set a discussion topic (default: PlayStation 5) or press Enter to skip.
3. Type your question — all active personas respond in character.
4. Use room commands to control who speaks, what they discuss, and what they see.
5. Type `!exit` to close the room and save a Markdown summary.

---

## Room Commands

Type `!help` at any time while the app is running to see all commands.

| Command | Description |
|---|---|
| `!add @name` | Add a persona to the room |
| `!kick @name` | Remove a persona from the room |
| `!observe` | Watch personas discuss with each other (3 rounds) |
| `!observe "topic"` | Observe with a seeded question |
| `!observe [n]` | Observe for n rounds |
| `!focus @name` | Direct all questions to one persona only |
| `!focus` | Clear focus — all active personas respond again |
| `!topic [text]` | Change the discussion topic mid-session |
| `!topic` | Reset to the default topic |
| `!image <path>` | Load an ad image — personas will react to it in character |
| `!image clear` | Remove all images from the room |
| `!images` | List all images currently loaded |
| `!reset` / `!clear` | Wipe conversation history for all active personas |
| `!exit` | Close the room and save a Markdown summary |
| `!help` | Show all commands in-app |

**Available personas:** `@lena`, `@marcus`

> **Tip:** You can combine a message and an image in one line:
> `Tell me what you think about this ad !image '/path/to/ad.png'`

---

## Personas

### Lena — `@lena`

| | |
|---|---|
| Age | 23 |
| Background | German transfer student, Cape Town |
| Role | YouTube content creator |
| Ecosystem | Android |
| Gaming | Competitive, deeply immersed |

Evaluates products through a **performance and content-creation lens**. Spec-driven, analytical, and skeptical of closed ecosystems. Direct and holds her ground.

---

### Marcus — `@marcus`

| | |
|---|---|
| Age | 38 |
| Background | Digital Product Designer, married with kids |
| Ecosystem | Apple |
| Gaming | Cultural observer, casual |

Evaluates products through **family utility, design quality, and long-term value**. Deliberate and resistant to hype — he weighs things like a design object.

---

## Example Session

```
Who would you like to start with?
  1. Lena     — 23yo transfer student, streamer, Android
  2. Marcus   — 38yo designer dad, Apple, casual gamer

Enter numbers (e.g. '1 2' for both): 1 2

[Loading Lena...]
[Loading Marcus...]

──────────────────────────────────────────────────────────
  Room: Lena, Marcus ready
  Topic: PlayStation 5
──────────────────────────────────────────────────────────

You → [Lena, Marcus]: Would you buy a PS5?

[Lena is thinking...]
  💭 The closed ecosystem thing is always my first reaction...

Lena: The hardware is impressive but the closed ecosystem puts me off.
      I can't mod, I can't customise — it feels like a walled garden
      I'm paying $499 to enter.
──────────────────────────────────────────────────────────

You → [Lena, Marcus]: !observe

  [Observing for 3 rounds — Ctrl+C to stop early]

[Marcus is thinking...]

Marcus: Lena, I hear you on the ecosystem point, but for me the
        question is whether the exclusives justify it for my kids.
──────────────────────────────────────────────────────────

You → [Lena, Marcus]: !exit

[Closing room...]
[Generating summary, please wait...]
[Summary saved to: chat_summaries/chat_20260224_141022.md]
[Room closed. Goodbye.]
```

---

## Image Analysis

Load any advertisement into the room and the personas will react to it in character.

```
You → [Lena, Marcus]: !image /path/to/ps5_ad.jpg

[Analyzing ps5_ad.jpg...]
[Image analyzed (1 image in room) — all personas are now briefed on: ps5_ad.jpg]

You → [Lena, Marcus]: What's your first reaction to this ad?
```

**How it works:**

1. `!image <path>` reads the file and sends it to Ollama Cloud (Qwen3-VL 235B) for analysis.
2. The model produces a detailed structured brief: copy, typography, colour scheme, deal details, composition, brand presence, and more.
3. This brief is injected into every persona's context — they can "see" the ad.
4. Each persona reacts based on their own values and taste, not a shared script.
5. The same image loaded again uses the cached analysis — no extra API call.

**Setup:** Add to your `.env`:

```
OLLAMA_API_KEY=your_key_here
OLLAMA_HOST=https://ollama.com
```

**Supported formats:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` (max 20 MB)

---

## Chat Summaries

When you type `!exit`, the app generates an executive summary of the full session and saves it to:

```
chat_summaries/chat_YYYYMMDD_HHMMSS.md
```

The file includes a 3–5 paragraph executive summary followed by the full timestamped chat log with each persona's visible thinking.

---

## Configuration

All settings can be overridden in `.env`. The defaults work out of the box for a standard local setup.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.1:8b` | Local model for persona responses |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama server |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `CHROMA_PERSIST_PATH` | `./.chromadb` | ChromaDB local storage path |
| `OLLAMA_API_KEY` | _(empty)_ | Ollama Cloud key — required for `!image` |
| `OLLAMA_HOST` | `https://ollama.com` | Ollama Cloud endpoint |
| `OLLAMA_VISION_MODEL` | `qwen3-vl:235b-cloud` | Vision model for image analysis |

---

## Running Tests

Tests cover room state, command parsing, thinking extraction, and Markdown output. No live services required.

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

---

## Adding a New Persona

1. Copy `personas/persona_template.json` and fill it in.
2. Add an entry to `PERSONA_REGISTRY` in `config.py`.
3. Add the `@mention` mapping to `PERSONA_MENTION_MAP` in `config.py`.
4. Run `python personas_loader.py` to seed it into ChromaDB.

See [`specs/focus_group_poc.md`](specs/focus_group_poc.md) for the full persona schema and step-by-step guide.

---

*Last updated: February 2026*
