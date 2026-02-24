#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup.sh — FocusGroup installer for macOS and Linux
#
# This script will:
#   1.  Scan your system (OS, architecture, shell, package manager)
#   2.  Check Python 3.11+, Ollama, and Redis are available
#       and offer installation guidance for anything missing
#   3.  Create a Python virtual environment (.venv)
#   4.  Install all Python packages
#   5.  Pull the llama3.1:8b Ollama model
#   6.  Create your .env configuration file
#   7.  Ask for your Ollama API key (needed for image analysis)
#   8.  Seed the persona database (ChromaDB)
#
# Usage:
#   chmod +x setup.sh && ./setup.sh
#
# Safe to re-run — all steps check before acting.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

step()   { echo -e "\n${BOLD}${BLUE}▶  $1${NC}"; }
ok()     { echo -e "   ${GREEN}✓${NC}  $1"; }
warn()   { echo -e "   ${YELLOW}⚠${NC}   $1"; }
err()    { echo -e "   ${RED}✗${NC}  $1"; }
info()   { echo -e "   ${CYAN}→${NC}  $1"; }
detail() { echo -e "   ${DIM}$1${NC}"; }
blank()  { echo ""; }

OLLAMA_MISSING=0
REDIS_MISSING=0
PKG_MGR=""

# ── Banner ────────────────────────────────────────────────────────────────────
blank
echo -e "${BOLD}FocusGroup — Setup${NC}"
echo -e "${DIM}Terminal AI focus-group simulator${NC}"
blank

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0 — System scan
# ─────────────────────────────────────────────────────────────────────────────
step "System scan"

OS_RAW=$(uname -s)
ARCH=$(uname -m)

case "$OS_RAW" in
    Darwin)
        OS_TYPE="macos"
        OS_LABEL="macOS"
        ;;
    Linux)
        OS_TYPE="linux"
        OS_LABEL="Linux"
        # Try to read distro name
        if [[ -f /etc/os-release ]]; then
            # shellcheck disable=SC1091
            . /etc/os-release
            OS_LABEL="${PRETTY_NAME:-Linux}"
        fi
        ;;
    *)
        OS_TYPE="unknown"
        OS_LABEL="$OS_RAW"
        ;;
esac

# Detect shell
USER_SHELL=$(basename "${SHELL:-bash}")

# Detect package manager
if   command -v brew    &>/dev/null; then PKG_MGR="brew"
elif command -v apt-get &>/dev/null; then PKG_MGR="apt"
elif command -v dnf     &>/dev/null; then PKG_MGR="dnf"
elif command -v pacman  &>/dev/null; then PKG_MGR="pacman"
elif command -v zypper  &>/dev/null; then PKG_MGR="zypper"
fi

ok "OS:           $OS_LABEL ($ARCH)"
ok "Shell:        $USER_SHELL"
ok "Pkg manager:  ${PKG_MGR:-none detected}"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Python
# ─────────────────────────────────────────────────────────────────────────────
step "Python (3.11+ required)"

PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PY_VER_CHECK=$("$candidate" --version 2>&1 | awk '{print $2}')
        PY_MIN=$(echo "$PY_VER_CHECK" | cut -d. -f2)
        if [[ "$PY_MIN" -ge 11 ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    err "Python 3.11 or newer not found."
    blank
    case "$PKG_MGR" in
        brew)    info "Install: brew install python@3.12" ;;
        apt)     info "Install: sudo apt install python3.12 python3.12-venv" ;;
        dnf)     info "Install: sudo dnf install python3.12" ;;
        pacman)  info "Install: sudo pacman -S python" ;;
        *)       info "Download: https://python.org/downloads" ;;
    esac
    blank
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
ok "Found: Python $PY_VERSION  ($PYTHON)"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Ollama
# ─────────────────────────────────────────────────────────────────────────────
step "Ollama"

if command -v ollama &>/dev/null; then
    OLLAMA_VER=$(ollama --version 2>/dev/null | head -1 || echo "installed")
    ok "$OLLAMA_VER"
else
    err "Ollama not found."
    blank
    info "Download and install Ollama from: https://ollama.com/download"
    case "$OS_TYPE" in
        macos) detail "  macOS: download the .dmg installer from the link above" ;;
        linux) detail "  Linux: curl -fsSL https://ollama.com/install.sh | sh" ;;
    esac
    blank
    warn "You can continue setup now, but the app won't run until Ollama is installed."
    warn "After installing Ollama, run this script again to pull the model."
    OLLAMA_MISSING=1
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Redis
# ─────────────────────────────────────────────────────────────────────────────
step "Redis"

if command -v redis-server &>/dev/null; then
    REDIS_VER=$(redis-server --version 2>/dev/null | awk '{print $3}' | cut -d= -f2 || echo "installed")
    ok "redis-server $REDIS_VER"
else
    err "Redis not found."
    blank
    case "$PKG_MGR" in
        brew)
            info "Install with Homebrew:"
            detail "  brew install redis"
            detail "  brew services start redis   # auto-start on login"
            blank
            read -r -p "   Install Redis via Homebrew now? [y/N] " INSTALL_REDIS
            if [[ "${INSTALL_REDIS,,}" == "y" ]]; then
                brew install redis
                brew services start redis
                ok "Redis installed and started"
                REDIS_MISSING=0
            else
                REDIS_MISSING=1
            fi
            ;;
        apt)
            info "Install:"
            detail "  sudo apt update && sudo apt install redis-server"
            detail "  sudo systemctl enable --now redis-server"
            REDIS_MISSING=1
            ;;
        dnf)
            info "Install:"
            detail "  sudo dnf install redis"
            detail "  sudo systemctl enable --now redis"
            REDIS_MISSING=1
            ;;
        pacman)
            info "Install:"
            detail "  sudo pacman -S redis"
            detail "  sudo systemctl enable --now redis"
            REDIS_MISSING=1
            ;;
        zypper)
            info "Install:"
            detail "  sudo zypper install redis"
            detail "  sudo systemctl enable --now redis"
            REDIS_MISSING=1
            ;;
        *)
            info "Download Redis from: https://redis.io/download"
            REDIS_MISSING=1
            ;;
    esac
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Virtual environment
# ─────────────────────────────────────────────────────────────────────────────
step "Python virtual environment"

if [[ -d ".venv" ]]; then
    ok ".venv already exists — skipping creation"
else
    $PYTHON -m venv .venv
    ok "Created .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
ok "Activated ($(python --version))"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Python packages
# ─────────────────────────────────────────────────────────────────────────────
step "Python packages"

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
ok "All packages installed"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Ollama model
# ─────────────────────────────────────────────────────────────────────────────
if [[ "$OLLAMA_MISSING" -eq 0 ]]; then
    step "Ollama model (llama3.1:8b)"
    if ollama list 2>/dev/null | grep -q "llama3.1:8b"; then
        ok "llama3.1:8b already downloaded"
    else
        blank
        info "Pulling llama3.1:8b — this download is ~4.7 GB and may take several minutes..."
        blank
        if ollama pull llama3.1:8b; then
            ok "llama3.1:8b downloaded"
        else
            warn "Model pull failed. Make sure Ollama is running, then:"
            detail "  ollama pull llama3.1:8b"
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Environment file (.env)
# ─────────────────────────────────────────────────────────────────────────────
step "Environment configuration (.env)"

if [[ ! -f ".env" ]]; then
    cp .env.example .env
    ok ".env created"
else
    ok ".env already exists"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — Ollama API key
# ─────────────────────────────────────────────────────────────────────────────
step "Ollama API key (for image analysis)"

# Check if key is already set in .env (non-empty value after the = sign)
if grep -qE "^OLLAMA_API_KEY=.+" .env 2>/dev/null; then
    ok "OLLAMA_API_KEY is already set in .env"
else
    blank
    echo -e "   The ${BOLD}!image${NC} command lets personas react to advertisement images."
    echo -e "   It needs a free Ollama Cloud API key to analyse images."
    blank
    echo -e "   ${BOLD}Get your key here:${NC} ${CYAN}https://ollama.com/settings/keys${NC}"
    echo -e "   ${DIM}(log in or create a free account → click 'New key' → copy it)${NC}"
    blank
    echo -e "   Paste your key below and press Enter."
    echo -e "   ${DIM}Press Enter without typing anything to skip — you can add it to .env later.${NC}"
    blank
    read -r -p "   OLLAMA_API_KEY: " OLLAMA_KEY
    blank

    if [[ -n "$OLLAMA_KEY" ]]; then
        # Replace the OLLAMA_API_KEY= line in .env with the real value
        if [[ "$OS_TYPE" == "macos" ]]; then
            sed -i '' "s|^OLLAMA_API_KEY=.*|OLLAMA_API_KEY=${OLLAMA_KEY}|" .env
        else
            sed -i "s|^OLLAMA_API_KEY=.*|OLLAMA_API_KEY=${OLLAMA_KEY}|" .env
        fi
        ok "API key saved to .env"
    else
        warn "Skipped. To add it later, open .env and set:  OLLAMA_API_KEY=your_key_here"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — Seed persona database
# ─────────────────────────────────────────────────────────────────────────────
step "Seeding persona database"

if python personas_loader.py; then
    ok "Personas loaded (Lena + Marcus)"
else
    err "personas_loader.py failed — check the error above"
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────────────
blank
echo -e "────────────────────────────────────────────────────────────"
echo -e "${BOLD}${GREEN}  Setup complete!${NC}"
echo -e "────────────────────────────────────────────────────────────"
blank

# Show any blocking issues first
if [[ "$OLLAMA_MISSING" -eq 1 ]] || [[ "$REDIS_MISSING" -eq 1 ]]; then
    echo -e "${YELLOW}  Before running the app, install the missing services:${NC}"
    blank
    if [[ "$OLLAMA_MISSING" -eq 1 ]]; then
        echo -e "  ${BOLD}Ollama${NC}"
        case "$OS_TYPE" in
            macos) detail "  Download: https://ollama.com/download  (install the .dmg)" ;;
            linux) detail "  Run: curl -fsSL https://ollama.com/install.sh | sh" ;;
        esac
        detail "  Then: ollama pull llama3.1:8b"
        blank
    fi
    if [[ "$REDIS_MISSING" -eq 1 ]]; then
        echo -e "  ${BOLD}Redis${NC}"
        case "$PKG_MGR" in
            brew)   detail "  brew install redis && brew services start redis" ;;
            apt)    detail "  sudo apt install redis-server && sudo systemctl start redis-server" ;;
            dnf)    detail "  sudo dnf install redis && sudo systemctl start redis" ;;
            pacman) detail "  sudo pacman -S redis && sudo systemctl start redis" ;;
            *)      detail "  https://redis.io/download" ;;
        esac
        blank
    fi
fi

# Activation command, matched to the user's shell
case "$USER_SHELL" in
    fish)     ACTIVATE="source .venv/bin/activate.fish" ;;
    csh|tcsh) ACTIVATE="source .venv/bin/activate.csh" ;;
    *)        ACTIVATE="source .venv/bin/activate" ;;
esac

echo -e "  ${BOLD}To start the app:${NC}"
blank
echo -e "  ${DIM}# 1. activate the environment${NC}"
echo -e "  ${BOLD}$ACTIVATE${NC}"
blank
echo -e "  ${DIM}# 2. start Ollama (in a separate terminal window)${NC}"
echo -e "  ${BOLD}ollama serve${NC}"
blank
echo -e "  ${DIM}# 3. start Redis (in another terminal window)${NC}"
case "$PKG_MGR" in
    brew)
        echo -e "  ${BOLD}brew services start redis${NC}   ${DIM}# or: redis-server${NC}"
        ;;
    *)
        echo -e "  ${BOLD}redis-server${NC}"
        ;;
esac
blank
echo -e "  ${DIM}# 4. run the app${NC}"
echo -e "  ${BOLD}python main.py${NC}"
blank
