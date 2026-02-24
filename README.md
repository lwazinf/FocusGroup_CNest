# FocusGroup

You are the moderator. The AI personas are your focus group.

Ask them anything — about an ad, a product, a price point. Load an image and they'll react to it in character. Every session is saved as a summary you can read later.

---

## What you need to know before starting

This app runs in your computer's **terminal** (also called the command line or command prompt). You type commands and press Enter to run them. That's all you need to know.

> **Already familiar with terminals and Python?** Jump straight to [Installation](#installation).

---

## What you need to install first

The app uses three separate services. All are free.

| What | What it does | Download |
|---|---|---|
| **Python 3.11+** | Runs the app | [python.org/downloads](https://python.org/downloads) |
| **Ollama** | Powers the AI personas | [ollama.com/download](https://ollama.com/download) |
| **Redis** | Remembers the conversation | See instructions below |
| **Ollama API key** | Lets personas see and react to images | [ollama.com/settings/keys](https://ollama.com/settings/keys) — free account needed |

> **What is Redis?**
> It's a small background service that stores the conversation history while you're in a session. Think of it as the app's short-term memory.

---

## Installation

Find your operating system below and follow those steps only.

---

### 🍎 macOS

#### 1. Open Terminal

Press **Command + Space**, type `Terminal`, press Enter.

#### 2. Install Homebrew (if you don't have it)

Homebrew is a free tool that makes installing software on a Mac easier. If you're not sure whether you have it, paste this into Terminal and press Enter:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

If it says "command not found: brew" after — run the line above. If it's already installed, skip this.

#### 3. Install Ollama

Download the macOS installer from **[ollama.com/download](https://ollama.com/download)** and run it like any other app.

#### 4. Install Redis

In Terminal:

```
brew install redis
brew services start redis
```

The second command makes Redis start automatically whenever you log in.

#### 5. Get the project files

In Terminal, navigate to where you want the project folder to live, then:

```
git clone https://github.com/lwazinf/FocusGroup_CNest.git
cd FocusGroup_CNest
```

> Don't have git? Install it with `brew install git`.

#### 6. Run the setup script

```
chmod +x setup.sh
./setup.sh
```

The script will scan your system, install all Python packages, pull the AI model, and ask for your Ollama API key. **Follow the prompts on screen.**

> **Ollama API key:** The setup script will pause and ask you to paste your key. Get one free at [ollama.com/settings/keys](https://ollama.com/settings/keys) — log in, click **New key**, copy it.

---

### 🐧 Linux (Ubuntu / Debian / Fedora / Arch)

#### 1. Open your terminal

Use whatever terminal emulator you prefer.

#### 2. Install Ollama

```
curl -fsSL https://ollama.com/install.sh | sh
```

#### 3. Install Redis

**Ubuntu / Debian:**
```
sudo apt update && sudo apt install redis-server
sudo systemctl enable --now redis-server
```

**Fedora:**
```
sudo dnf install redis
sudo systemctl enable --now redis
```

**Arch Linux:**
```
sudo pacman -S redis
sudo systemctl enable --now redis
```

#### 4. Get the project files

```
git clone https://github.com/lwazinf/FocusGroup_CNest.git
cd FocusGroup_CNest
```

#### 5. Run the setup script

```
chmod +x setup.sh
./setup.sh
```

The script detects your distro and package manager, installs everything it can, and walks you through the rest. **Follow the prompts on screen.**

---

### 🪟 Windows

#### 1. Install Python

Download from [python.org/downloads](https://python.org/downloads).

During installation, **check the box that says "Add Python to PATH"** — this is important.

#### 2. Install Ollama

Download the Windows installer from [ollama.com/download](https://ollama.com/download) and run it.

#### 3. Install Redis

Redis doesn't have an official Windows installer. Pick whichever option suits you:

**Option A — Memurai** (easiest for Windows)
Download and install from [memurai.com/get-memurai](https://www.memurai.com/get-memurai). It runs as a system service in the background automatically.

**Option B — WSL2** (recommended if you're comfortable with it)
WSL2 lets you run Linux inside Windows, which makes Redis trivial to install.
1. Open PowerShell as Administrator and run: `wsl --install`
2. Restart your computer
3. Open the Ubuntu app that was installed, then run:
   ```
   sudo apt install redis-server
   sudo service redis-server start
   ```

#### 4. Get the project files

Open **PowerShell** (press Windows + X, then click "Windows PowerShell"), then:

```
git clone https://github.com/lwazinf/FocusGroup_CNest.git
cd FocusGroup_CNest
```

> Don't have git? Install it from [git-scm.com/download/win](https://git-scm.com/download/win).

#### 5. Run the setup script

If PowerShell says "running scripts is disabled", first run:
```
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then run the setup:
```
.\setup.ps1
```

The script installs all Python packages, pulls the AI model, and asks for your API key. **Follow the prompts on screen.**

---

## Manual setup (any OS)

If you'd rather do it step by step instead of using the install script:

```bash
# 1. Create a Python virtual environment
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate          # macOS / Linux (bash, zsh)
source .venv/bin/activate.fish     # macOS / Linux (fish)
.\.venv\Scripts\Activate.ps1       # Windows (PowerShell)

# 3. Install packages
pip install -r requirements.txt

# 4. Copy the config template
cp .env.example .env
# Open .env and add your OLLAMA_API_KEY

# 5. Pull the AI model (Ollama must be running)
ollama pull llama3.1:8b

# 6. Load the personas into the database (first time only)
python personas_loader.py
```

---

## Running the app

You need three things running at the same time — open three terminal windows (or tabs).

**Terminal 1 — Ollama**
```
ollama serve
```

**Terminal 2 — Redis**
```
redis-server
```

> On macOS with Homebrew: if you ran `brew services start redis` during setup, Redis is already running in the background. You can skip this terminal.
> On Windows with Memurai: Redis is running as a service automatically. Skip this too.

**Terminal 3 — The app**
```
# Activate your environment first (every time)
source .venv/bin/activate          # bash / zsh
source .venv/bin/activate.fish     # fish
.\.venv\Scripts\Activate.ps1       # Windows

python main.py
```

---

## How to use it

When the app starts, it will ask you which personas to invite into the room. Type the numbers you want (e.g. `1 2` for both), or press **G** to generate a brand-new custom persona on the spot.

Then type your topic (or press Enter for the default: PlayStation 5).

The terminal clears automatically when you enter the room so you start with a clean view.

Once you're in the room, just type your questions and press Enter.

### Room commands

| Command | What it does |
|---|---|
| `!add @name` | Add a persona to the room |
| `!kick @name` | Remove a persona from the room |
| `!observe` | Watch the personas talk to each other for 3 rounds |
| `!observe "question"` | Observe with a specific seed question |
| `!observe 5` | Observe for 5 rounds (combine: `!observe "question" 5`) |
| `!focus @name` | Talk to one persona only (others watch) |
| `!focus` | Go back to talking to everyone |
| `!topic your topic` | Change what you're discussing |
| `!image /path/to/image.jpg` | Load an ad image — personas will react to it |
| `!image clear` | Remove all images from the room |
| `!images` | See what images are loaded |
| `!clear` | Clear the conversation history (`!reset` also works) |
| `!exit` | Print a session brief, then save a full Markdown summary |
| `!help` | Show all commands inside the app |

**Built-in personas:** `@lena`, `@marcus`

**Custom personas:** Press **G** at the persona menu to generate one. Custom personas are addressed by `@firstname` (e.g. a generated "Rukmini Patel" is `@rukmini`).

> **Tip:** You can combine a message and an image in one go:
> `What do you think of this ad? !image '/Users/you/Desktop/ad.png'`
>
> On a Mac, you can drag a file from Finder into the terminal window to paste its path automatically.

---

## The personas

### Lena  (`@lena`)

23-year-old German transfer student living in Cape Town. YouTube content creator, competitive gamer, Android user. She evaluates everything through a **performance and specs lens**. Direct, opinionated, and not easily convinced.

### Marcus  (`@marcus`)

38-year-old digital product designer, married with two kids, Apple ecosystem. He looks at things like a designer — **quality, longevity, and family value** matter more than specs. Thoughtful and resistant to hype.

### Custom personas

Press **G** at the persona menu to generate a random persona. The app will suggest traits — age, background, gaming habits, personality — and let you edit them or regenerate before saving. Once saved, the persona appears in your menu and can be added to any future room.

Custom personas are addressed by first name: a generated "Rukmini Patel" becomes `@rukmini` in room commands.

---

## Loading ad images

The `!image` command sends the image to an AI vision model, which produces a detailed, neutral analysis — layout, colours, typography, copy, deals, brand prominence — and shares that brief with every persona. They each react in character.

**Requires:** `OLLAMA_API_KEY` in your `.env` file. Get one free at [ollama.com/settings/keys](https://ollama.com/settings/keys).

**Supported formats:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` (max 20 MB)

---

## Session summaries

When you type `!exit`, the app first prints a **session brief** — five bullet-point insights — directly to the terminal, then saves a full Markdown summary to:

```
chat_summaries/chat_YYYYMMDD_HHMMSS.md
```

The file includes an executive summary of the session and the full conversation log with each persona's internal thinking visible. The summary saves even if you Ctrl+C during the brief generation.

---

## Configuration

All settings live in your `.env` file. The defaults work out of the box for a standard local setup — you only need to change things if your setup is different.

| Setting | Default | What it controls |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.1:8b` | Which local model the personas use |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama server address |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection address |
| `CHROMA_PERSIST_PATH` | `./.chromadb` | Where persona data is stored on disk |
| `OLLAMA_API_KEY` | *(empty)* | Your Ollama Cloud key — needed for `!image` |
| `OLLAMA_HOST` | `https://ollama.com` | Ollama Cloud endpoint |

---

## Running tests

Tests cover the core logic and don't need Ollama or Redis running.

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

---

## Adding a new persona

**Easy way — in the app:** Press **G** at the persona menu. The app generates a full persona, lets you edit any trait, and saves it automatically. No files to edit.

**Manual way — via JSON:**

1. Copy `personas/persona_template.json` and fill it in.
2. Add an entry to `PERSONA_REGISTRY` in `config.py`.
3. Add the `@mention` to `PERSONA_MENTION_MAP` in `config.py`.
4. Run `python personas_loader.py` to register them.

See [`specs/focus_group_poc.md`](specs/focus_group_poc.md) for the full schema guide.

---

## Troubleshooting

**"Cannot connect to Redis" when starting the app**
→ Redis isn't running. Start it with `brew services start redis` (macOS) or `sudo systemctl start redis` (Linux), then try again.

**"Connection refused" from Ollama**
→ Ollama isn't running. Start it with `ollama serve` in a separate terminal.

**"!image" says no key found**
→ Open `.env` and add your key: `OLLAMA_API_KEY=your_key_here`

**Personas say they can't see an image**
→ The `!image` command must successfully analyse the image before you ask about it. Look for the `[Image analyzed...]` confirmation message. If it's missing, check your API key.

**"Permission denied: setup.sh"**
→ Run `chmod +x setup.sh` first, then `./setup.sh`.

**Windows: "running scripts is disabled"**
→ Open PowerShell and run: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

---

*Last updated: February 2026 — v1.1*
