#!/usr/bin/env bash
set -e

REPO="/mnt/c/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original"
cd "$REPO"

echo "=== STEP 0: Environment Check ==="
ezkl --version
python3 --version

echo ""
echo "=== STEP 1: Python Dependencies ==="
python3 -c "import pydantic; print('pydantic:', pydantic.__version__)"
python3 -c "import jsonschema; print('jsonschema: OK')"
python3 -c "import sqlite3; print('sqlite3: OK')"
python3 -c "import hashlib; print('hashlib: OK')"

echo ""
echo "=== STEP 2: VK Hash Verification ==="
python3 -c "
import hashlib
with open('vk.key', 'rb') as f:
    h = hashlib.sha256(f.read()).hexdigest()
TRUSTED = 'f519d8bddcf2801c194fb65e7d1ef628497462443e0891081e52c47bd99956e1'
print('Actual  :', h)
print('Trusted :', TRUSTED)
print('MATCH   :', h == TRUSTED)
"

echo ""
echo "=== STEP 3: validate_proof_environment() ==="
python3 -c "
import sys
sys.path.insert(0, '.')
from schema.proof_lifecycle import validate_proof_environment
report = validate_proof_environment()
print('valid            :', report['valid'])
print('ezkl_available   :', report['ezkl_available'])
print('missing_files    :', report['missing_files'])
print('vk_tampered      :', report['vk_tampered'])
print('errors           :', report['errors'])
"

echo ""
echo "=== DONE: Preflight Check ==="
