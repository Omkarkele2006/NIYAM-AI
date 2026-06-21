#!/usr/bin/env bash
REPO="/mnt/c/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original"
cd "$REPO"

echo "=== Checking for existing venv ==="
if [ -d ".venv" ]; then
    echo "Found .venv directory"
    ls .venv/bin/ 2>/dev/null || ls .venv/Scripts/ 2>/dev/null || echo "No bin/Scripts"
elif [ -d "venv" ]; then
    echo "Found venv directory"
    ls venv/bin/ 2>/dev/null | head -5
else
    echo "No venv found"
fi

echo ""
echo "=== Checking pip3 ==="
pip3 --version 2>&1 | head -2
which pip3

echo ""
echo "=== System Python packages ==="
pip3 list 2>/dev/null | grep -E "pydantic|jsonschema|streamlit" || echo "None of target packages installed"

echo ""
echo "=== Python site-packages ==="
python3 -c "import site; print(site.getsitepackages())"
