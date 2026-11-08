#!/usr/bin/env bash
# Run from the repository root. Keep scanners separate from the product environment.
set -euo pipefail
redmud_audit_tool="${REDMUD_CARGO_AUDIT:-cargo-audit}"
redmud_audit_python="${REDMUD_PIP_AUDIT_PYTHON:-python}"
redmud_security_output="${REDMUD_SECURITY_OUTPUT:-target/security}"
mkdir -p "$redmud_security_output"
date -u +%FT%TZ
python scripts/update_notices.py --check
"$redmud_audit_tool" audit --version
"$redmud_audit_python" -m pip_audit --version
# Fetch the database normally: no --stale, --no-fetch, ignores or automatic fixes.
"$redmud_audit_tool" audit --json > "$redmud_security_output/rust-advisories.json"
"$redmud_audit_python" -m pip_audit --disable-pip --no-deps -r requirements-dev.txt \
    --format json --output "$redmud_security_output/python-advisories.json"
python - "$redmud_security_output" <<'PY'
import json
import sys
from pathlib import Path
folder = Path(sys.argv[1])
rust = json.loads((folder / 'rust-advisories.json').read_text())
python = json.loads((folder / 'python-advisories.json').read_text())
assert not rust['vulnerabilities']['found'], 'Rust vulnerability findings'
assert not any(rust.get('warnings', {}).values()), 'Review Rust advisory warnings'
assert not any(d.get('skip_reason') for d in python['dependencies']), 'Python packages skipped'
assert not any(d['vulns'] for d in python['dependencies']), 'Python vulnerability findings'
print('PASS: audited Cargo.lock and pinned Python build/dev tools; no findings or skipped packages.')
print('Scope: dated advisory databases; not a proof of absence of unknown vulnerabilities.')
PY
