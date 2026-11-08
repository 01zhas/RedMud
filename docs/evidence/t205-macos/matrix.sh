#!/usr/bin/env bash
# Execute available local macOS matrix sequentially; retain each failed run.
set -uo pipefail
cd "$(dirname "$0")/../../.."
source docs/evidence/t205-macos/env.sh
recorder="$PWD/docs/evidence/t205-macos/run.py"
base_python="$PWD/target/t205-tools/python/bin/python"
"$base_python" "$recorder" package-311 "$base_python" scripts/package_check.py --output target/t205-macos-package
for version in 3.12 3.13; do
  tag="${version/./}"
  interpreter="$(uv python find "$version")" || continue
  venv="$PWD/target/t205-tools/python-$tag"
  "$base_python" "$recorder" "venv-$tag" "$interpreter" -m venv "$venv" || continue
  "$base_python" "$recorder" "tools-$tag" "$venv/bin/python" -m pip install -r requirements-dev.txt || continue
  export PATH="$venv/bin:$PWD/target/t205-tools/python/bin:$CARGO_HOME/bin:$PATH"
  "$base_python" "$recorder" "versions-$tag" bash -c 'python -VV; python -m pip list; rustc -Vv'
  "$base_python" "$recorder" "check-$tag" bash scripts/check.sh
  "$base_python" "$recorder" "package-$tag" "$venv/bin/python" scripts/package_check.py --output target/t205-macos-package
 done
