#!/usr/bin/env bash
REPO="/mnt/c/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original"
cd "$REPO"

echo "=== Installing minimum required packages ==="
pip3 install pydantic 2>&1 | tail -3
pip3 install jsonschema 2>&1 | tail -2

echo ""
echo "=== Verifying core imports ==="
python3 -c "import pydantic; print('pydantic', pydantic.__version__)"
python3 -c "import jsonschema; print('jsonschema OK')"
python3 -c "import sqlite3; print('sqlite3 OK')"
python3 -c "import hashlib; print('hashlib OK')"
python3 -c "import uuid; print('uuid OK')"
python3 -c "import json; print('json OK')"
python3 -c "import subprocess; print('subprocess OK')"
python3 -c "import re; print('re OK')"
echo "=== Core imports verified ==="
