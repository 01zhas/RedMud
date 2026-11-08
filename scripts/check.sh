#!/usr/bin/env bash
# Run from the repository root; builds and reinstalls the exact release extension.
set -euo pipefail
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
python -m ruff check --select E9,F63,F7,F82 python tests examples benchmarks
python -m compileall -q python
cargo test --workspace --locked
redmud_check_python="$(python -c 'import sys; print(sys.executable)')"
redmud_check_tag="$(python -c 'import sys; print(sys.implementation.cache_tag)')"
redmud_check_wheels="target/check-wheels/$redmud_check_tag"
maturin build --release --locked --interpreter "$redmud_check_python" --out "$redmud_check_wheels"
python -m pip install --force-reinstall --no-deps "$redmud_check_wheels"/*.whl
python -c 'import redmud, redmud._native; print(redmud.__file__); print(redmud._native.__file__)'
python -m unittest discover -s tests -v
