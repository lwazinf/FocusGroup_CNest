#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup.sh — FocusGroup one-command installer
#
# What this script does:
#   1. Checks Python version (3.11+ required)
#   2. Checks Ollama and Redis are installed
#   3. Creates and activates a Python virtual environment (.venv)
#   4. Installs all Python dependencies from requirements.txt
#   5. Pulls the Ollama model (llama3.1:8b) if not already downloaded
#   6. Creates a .env file from .env.example if one doesn't exist
#   7. Seeds the persona database (ChromaDB) on first run
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# Safe to re-run — all steps are idempotent.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

step()    { echo -e "\n${BOLD}${BLUE}▶  $1${NC}"; }
ok()      { echo -e "   ${GREEN}✓${NC}  $1"; }
warn()    { echo -e "   ${YELLOW}⚠${NC}   $1"; }
err()     { echo -e "   ${RED}✗${NC}  $1"; }
detail()  { echo -e "   ${DIM}$1${NC}"; }

OLLAMA_MISSING=0
REDIS_MISSING=0

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}FocusGroup — Setup${NC}"
echo -e "${DIM}Terminal AI focus-group simulation${NC}"
echo ""

# ── 1. Python ─────────────────────────────────────────────────────────────────
step "Python"
PYTHON=""
for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

if [[ -z "$PYTHON" ]]; then
    err "Python 3.11+ not found."
    detail "Install from https://python.org or via your package manager."
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [[ "$PY_MINOR" -lt 11 ]]; then
    err "Python $PY_VERSION found — 3.11 or newer required."
    exit 1
fi
ok "Python $PY_VERSION  ($PYTHON)"

# ── 2. Ollama ─────────────────────────────────────────────────────────────────
step "Ollama"
if command -v ollama &>/dev/null; then
    OLLAMA_VER=$(ollama --version 2>/dev/null | head -1 || echo "installed")
    ok "$OLLAMA_VER"
else
    err "Ollama not found — required for persona conversations."
    detail "Install: https://ollama.com/download"
    OLLAMA_MISSING=1
fi

# ── 3. Redis ──────────────────────────────────────────────────────────────────
step "Redis"
if command -v redis-server &>/dev/null; then
    REDIS_VER=$(redis-server --version 2>/dev/null | awk '{print $3}' | cut -d= -f2 || echo "installed")
    ok "redis-server $REDIS_VER"
else
    err "Redis not found — required for session history."
    OS=$(uname -s)
    if [[ "$OS" == "Darwin" ]]; then
        detail "Install: brew install redis"
    else
        detail "Install: sudo apt install redis-server"
    fi
    REDIS_MISSING=1
fi

# ── 4. Virtual environment ────────────────────────────────────────────────────
step "Virtual environment"
if [[ -d ".venv" ]]; then
    ok ".venv already exists — skipping creation"
else
    $PYTHON -m venv .venv
    ok "Created .venv"
fi

# Activate inside this script's shell
# shellcheck disable=SC1091
source .venv/bin/activate
ok "Activated  ($(python --version))"

# ── 5. Python dependencies ────────────────────────────────────────────────────
step "Python packages"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
ok "All packages installed"

# ── 6. Ollama model ───────────────────────────────────────────────────────────
if [[ "$OLLAMA_MISSING" -eq 0 ]]; then
    step "Ollama model (llama3.1:8b)"
    if ollama list 2>/dev/null | grep -q "llama3.1:8b"; then
        ok "llama3.1:8b already downloaded"
    else
        echo ""
        echo -e "   Pulling llama3.1:8b — this may take a few minutes..."
        if ollama pull llama3.1:8b; then
            ok "llama3.1:8b downloaded"
        else
            warn "Could not pull llama3.1:8b automatically."
            detail "Once Ollama is running: ollama pull llama3.1:8b"
        fi
    fi
fi

# ── 7. Environment file ───────────────────────────────────────────────────────
step "Environment file (.env)"
if [[ -f ".env" ]]; then
    ok ".env already exists — skipping"
else
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        ok ".env created from .env.example"
        warn "Open .env and add your OLLAMA_API_KEY to enable image analysis (!image)"
        detail "Get a key at: https://ollama.com/settings/keys"
    else
        warn ".env.example not found — create .env manually (see README)"
    fi
fi

# ── 8. Seed persona database ──────────────────────────────────────────────────
step "Seeding persona database (ChromaDB)"
if python personas_loader.py; then
    ok "Personas seeded (Lena + Marcus)"
else
    err "personas_loader.py failed — check the output above."
    exit 1
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────────────────────────────────────────────"
echo -e "${BOLD}Setup complete.${NC}"
echo "─────────────────────────────────────────────────────────────────────────────"
echo ""

if [[ "$OLLAMA_MISSING" -eq 1 ]] || [[ "$REDIS_MISSING" -eq 1 ]]; then
    echo -e "${YELLOW}One or more services are missing. Install them before running:${NC}"
    echo ""
    if [[ "$OLLAMA_MISSING" -eq 1 ]]; then
        echo -e "  ${BOLD}Ollama${NC}   https://ollama.com/download"
        echo "           Then: ollama pull llama3.1:8b"
    fi
    if [[ "$REDIS_MISSING" -eq 1 ]]; then
        OS=$(uname -s)
        if [[ "$OS" == "Darwin" ]]; then
            echo -e "  ${BOLD}Redis${NC}    brew install redis && brew services start redis"
        else
            echo -e "  ${BOLD}Redis${NC}    sudo apt install redis-server && sudo systemctl start redis"
        fi
    fi
    echo ""
fi

echo -e "  ${BOLD}Activate the environment:${NC}"
echo ""
echo "    # bash / zsh"
echo "    source .venv/bin/activate"
echo ""
echo "    # fish"
echo "    source .venv/bin/activate.fish"
echo ""
echo -e "  ${BOLD}Start services, then run:${NC}"
echo ""
echo "    ollama serve        # terminal 1"
echo "    redis-server        # terminal 2"
echo "    python main.py      # terminal 3"
echo ""
