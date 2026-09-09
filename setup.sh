#!/usr/bin/env bash
# Classical Candles setup: creates a virtualenv and installs everything needed.
set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

echo -e "${BOLD}🕯️  Classical Candles — setup${RESET}"
echo

PYTHON_BIN=""
for candidate in python3 python py; do
    if command -v "$candidate" >/dev/null 2>&1; then
        # `command -v` only checks that something with this name exists on
        # PATH -- on Windows that's sometimes a Microsoft Store alias stub
        # that "exists" but refuses to run. Confirm it actually reports a
        # version before trusting it.
        version_output="$("$candidate" --version 2>&1)" || true
        if [[ "$version_output" =~ ^Python\ 3\.[0-9] ]]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}✗ Python 3.10+ not found.${RESET} Install it from https://python.org and re-run this script."
    exit 1
fi
echo -e "${GREEN}✓${RESET} Found $($PYTHON_BIN --version) ($(command -v "$PYTHON_BIN"))"

if command -v ffmpeg >/dev/null 2>&1; then
    echo -e "${GREEN}✓${RESET} Found $(ffmpeg -version | head -n 1 | cut -d' ' -f1-3)"
else
    echo -e "${YELLOW}!${RESET} FFmpeg not found on PATH."
    echo "  macOS:   brew install ffmpeg"
    echo "  Ubuntu:  sudo apt install ffmpeg"
    echo "  Windows: winget install ffmpeg"
    echo "  Classical Candles needs it to pull audio and (optionally) export video."
fi

echo
echo "Creating virtual environment in .venv ..."
"$PYTHON_BIN" -m venv .venv

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    source .venv/Scripts/activate
fi

echo "Installing dependencies ..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo
echo -e "${GREEN}${BOLD}Listed and ready.${RESET}"
echo "Start the exchange with:"
echo
echo -e "  ${BOLD}source .venv/bin/activate   # or .venv\\\\Scripts\\\\activate on Windows${RESET}"
echo -e "  ${BOLD}python webapp/server.py${RESET}"
echo
echo "Then open http://127.0.0.1:5000 and paste a link."
