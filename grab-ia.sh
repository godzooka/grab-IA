#!/bin/bash
# grab-IA CLI Wrapper
# Automatically sets up environment and runs CLI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
    
    echo "📦 Installing dependencies..."
    "$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
    echo "✓ Dependencies installed"
fi

# Run CLI with all arguments passed through
exec "$PYTHON_BIN" "$SCRIPT_DIR/grabia_cli.py" "$@"
