# ─────────────────────────────────────────────────────────────────────────────
# setup.ps1 — FocusGroup installer for Windows
#
# Run this in PowerShell (not Command Prompt).
# Right-click PowerShell → "Run as Administrator" is NOT required.
#
# If you see "running scripts is disabled", run this first:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#
# What this script does:
#   1.  Scans your system
#   2.  Checks Python 3.11+, Ollama, and Redis
#   3.  Creates a Python virtual environment (.venv)
#   4.  Installs all Python packages
#   5.  Pulls the llama3.1:8b Ollama model
#   6.  Creates your .env configuration file
#   7.  Asks for your Ollama API key (for image analysis)
#   8.  Seeds the persona database
# ─────────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Step  { param($m) Write-Host "`n  >> $m" -ForegroundColor Cyan }
function Write-Ok    { param($m) Write-Host "     [OK]  $m" -ForegroundColor Green }
function Write-Warn  { param($m) Write-Host "     [!]   $m" -ForegroundColor Yellow }
function Write-Err   { param($m) Write-Host "     [X]   $m" -ForegroundColor Red }
function Write-Info  { param($m) Write-Host "           $m" -ForegroundColor Gray }
function Write-Blank { Write-Host "" }

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Blank
Write-Host "  FocusGroup - Windows Setup" -ForegroundColor White
Write-Host "  Terminal AI focus-group simulator" -ForegroundColor DarkGray
Write-Blank

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0 — System scan
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "System scan"

$OS      = [System.Environment]::OSVersion.VersionString
$ARCH    = $env:PROCESSOR_ARCHITECTURE
$PSVER   = $PSVersionTable.PSVersion.ToString()

Write-Ok "OS:           $OS"
Write-Ok "Architecture: $ARCH"
Write-Ok "PowerShell:   $PSVER"

# Detect package managers
$HAS_WINGET = $null -ne (Get-Command winget -ErrorAction SilentlyContinue)
$HAS_CHOCO  = $null -ne (Get-Command choco  -ErrorAction SilentlyContinue)
$HAS_SCOOP  = $null -ne (Get-Command scoop  -ErrorAction SilentlyContinue)

$PKG_MGR = if ($HAS_WINGET) { "winget" } elseif ($HAS_CHOCO) { "chocolatey" } elseif ($HAS_SCOOP) { "scoop" } else { "none" }
Write-Ok "Pkg manager:  $PKG_MGR"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Python
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Python (3.11+ required)"

$PYTHON = $null
foreach ($candidate in @("python3.13", "python3.12", "python3.11", "python3", "python")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $verStr = & $candidate --version 2>&1
        if ($verStr -match "(\d+)\.(\d+)") {
            $minor = [int]$Matches[2]
            if ($minor -ge 11) {
                $PYTHON = $candidate
                break
            }
        }
    }
}

if (-not $PYTHON) {
    Write-Err "Python 3.11 or newer not found."
    Write-Blank
    Write-Info "Download from: https://python.org/downloads"
    Write-Info "During install, check 'Add Python to PATH'"
    Write-Blank
    if ($HAS_WINGET) { Write-Info "Or run: winget install Python.Python.3.12" }
    if ($HAS_CHOCO)  { Write-Info "Or run: choco install python312" }
    Write-Blank
    exit 1
}

$PY_VERSION = & $PYTHON --version 2>&1
Write-Ok "Found: $PY_VERSION  ($PYTHON)"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Ollama
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Ollama"
$OLLAMA_MISSING = $false

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    $ollamaVer = & ollama --version 2>&1 | Select-Object -First 1
    Write-Ok "$ollamaVer"
} else {
    Write-Err "Ollama not found."
    Write-Blank
    Write-Info "Download and install from: https://ollama.com/download"
    Write-Info "(Choose the Windows installer)"
    Write-Blank
    if ($HAS_WINGET) { Write-Info "Or run: winget install Ollama.Ollama" }
    Write-Blank
    Write-Warn "Continue setup, then install Ollama and run this script again to pull the model."
    $OLLAMA_MISSING = $true
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Redis
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Redis"
$REDIS_MISSING = $false

if (Get-Command redis-server -ErrorAction SilentlyContinue) {
    $redisVer = & redis-server --version 2>&1
    Write-Ok "$redisVer"
} else {
    Write-Err "Redis not found."
    Write-Blank
    Write-Info "Redis does not have an official Windows installer."
    Write-Info "The easiest options are:"
    Write-Blank
    Write-Info "  Option A — Memurai (Windows-native Redis fork, free for dev):"
    Write-Info "             https://www.memurai.com/get-memurai"
    Write-Blank
    Write-Info "  Option B — WSL2 (Windows Subsystem for Linux):"
    Write-Info "             1. Enable WSL2: wsl --install"
    Write-Info "             2. Open Ubuntu, then: sudo apt install redis-server"
    Write-Info "             3. Start it with:     sudo service redis-server start"
    Write-Blank
    if ($HAS_CHOCO) {
        Write-Info "  Option C — Chocolatey:"
        Write-Info "             choco install redis-64"
    }
    Write-Blank
    Write-Warn "Continue setup, then install Redis before running the app."
    $REDIS_MISSING = $true
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Virtual environment
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Python virtual environment"

if (Test-Path ".venv") {
    Write-Ok ".venv already exists - skipping creation"
} else {
    & $PYTHON -m venv .venv
    Write-Ok "Created .venv"
}

# Activate
& .\.venv\Scripts\Activate.ps1
Write-Ok "Activated ($(python --version))"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Python packages
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Python packages"

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Ok "All packages installed"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Ollama model
# ─────────────────────────────────────────────────────────────────────────────
if (-not $OLLAMA_MISSING) {
    Write-Step "Ollama model (llama3.1:8b)"
    $modelList = & ollama list 2>&1
    if ($modelList -match "llama3.1:8b") {
        Write-Ok "llama3.1:8b already downloaded"
    } else {
        Write-Blank
        Write-Info "Pulling llama3.1:8b - this is ~4.7 GB and may take several minutes..."
        Write-Blank
        if (& ollama pull llama3.1:8b) {
            Write-Ok "llama3.1:8b downloaded"
        } else {
            Write-Warn "Pull failed. Make sure Ollama is running, then run: ollama pull llama3.1:8b"
        }
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Environment file (.env)
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Environment configuration (.env)"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Ok ".env created from .env.example"
} else {
    Write-Ok ".env already exists"
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — Ollama API key
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Ollama API key (for image analysis)"

$envContent = Get-Content ".env" -Raw
$keyAlreadySet = $envContent -match "^OLLAMA_API_KEY=.+"

if ($keyAlreadySet) {
    Write-Ok "OLLAMA_API_KEY is already set in .env"
} else {
    Write-Blank
    Write-Host "     The !image command lets personas react to advertisement images." -ForegroundColor White
    Write-Host "     It needs a free Ollama Cloud API key." -ForegroundColor White
    Write-Blank
    Write-Host "     Get your key here: https://ollama.com/settings/keys" -ForegroundColor Cyan
    Write-Host "     (log in or create a free account, click 'New key', copy it)" -ForegroundColor DarkGray
    Write-Blank
    Write-Host "     Paste your key and press Enter." -ForegroundColor White
    Write-Host "     Press Enter without typing to skip (you can add it to .env later)." -ForegroundColor DarkGray
    Write-Blank
    $OLLAMA_KEY = Read-Host "     OLLAMA_API_KEY"
    Write-Blank

    if ($OLLAMA_KEY) {
        (Get-Content ".env") -replace "^OLLAMA_API_KEY=.*", "OLLAMA_API_KEY=$OLLAMA_KEY" |
            Set-Content ".env"
        Write-Ok "API key saved to .env"
    } else {
        Write-Warn "Skipped. To add later: open .env and set OLLAMA_API_KEY=your_key_here"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — Seed persona database
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Seeding persona database"

python personas_loader.py
Write-Ok "Personas loaded (Lena + Marcus)"

# ─────────────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────────────
Write-Blank
Write-Host "  ------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "  ------------------------------------------------------------" -ForegroundColor DarkGray
Write-Blank

if ($OLLAMA_MISSING -or $REDIS_MISSING) {
    Write-Host "  Before running, install the missing services above." -ForegroundColor Yellow
    Write-Blank
}

Write-Host "  To start the app:" -ForegroundColor White
Write-Blank
Write-Host "    # 1. Activate the environment (run this each time)" -ForegroundColor DarkGray
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Blank
Write-Host "    # 2. Start Ollama (leave this terminal open)" -ForegroundColor DarkGray
Write-Host "    ollama serve" -ForegroundColor White
Write-Blank
Write-Host "    # 3. Start Redis (in another terminal, or use Memurai's system tray icon)" -ForegroundColor DarkGray
Write-Host "    redis-server" -ForegroundColor White
Write-Blank
Write-Host "    # 4. Run the app" -ForegroundColor DarkGray
Write-Host "    python main.py" -ForegroundColor White
Write-Blank
