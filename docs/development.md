# Local verification

Install Rust stable with rustfmt/clippy (`rustup component add rustfmt clippy`)
and `python -m pip install -r requirements-dev.txt`. From the repository root,
with Cargo on PATH, run `bash scripts/check.sh`. The script runs format/lint,
compileall, Rust tests, release-wheel build/reinstall, records import paths and
runs all Python tests against that extension. Use an activated venv for isolated
installation. No optional Polars/Pydantic dependency is required.

M1 tool baseline: Rust 1.99.1, rustfmt 1.10.0-stable, clippy 0.1.99; Python
3.12.14; maturin 1.16.0; Ruff 0.17.4. Ruff declares MIT, verified from installed
metadata/license file; CLI focused selectors tested. Rust tools ship with the
installed Rust toolchain. These are recorded baseline versions, not a claim that
all other versions/platforms have been tested. Advisory verification is now T-206 in M1 (A-01); platform CI remains M2.


## Security verification (T-206)

Selection/license evidence: docs/evidence/m1/scanner-selection.json.
Install `cargo-audit 0.22.2` separately using
`cargo install cargo-audit --version 0.22.2 --locked`; its license is
Apache-2.0 OR MIT. Install pip-audit 2.10.1 (Apache-2.0) into a separate venv
using requirements-security.txt. Neither tool is a runtime/build dependency.

```sh
REDMUD_CARGO_AUDIT=/path/to/cargo-audit \
REDMUD_PIP_AUDIT_PYTHON=/path/to/scanner-venv/bin/python \
bash scripts/security.sh
```

The script requires network access for advisory data and fails on unavailable
feeds, vulnerabilities, Rust advisory warnings or skipped Python packages. It
makes no fixes and uses no ignores. JSON reports default to target/security;
REDMUD_SECURITY_OUTPUT can select an evidence directory. Python requirements
are exact pinned build/dev packages, with no dependency resolution during scan:
maturin/ruff have no mandatory Python dependencies for supported CPython 3.11+.
RedMud wheel metadata is separately checked for empty Requires-Dist. Scanner
self-dependencies and the Rust/CPython toolchain are not the RedMud runtime graph.

THIRD_PARTY_NOTICES.md retains original license texts for all 22 locked external
Rust packages, including target-specific/build-only crates conservatively. The
inventory records source license file hashes and SPDX expressions. Unicode-3.0
and the target-lexicon LLVM exception texts are included, not flattened to MIT.
The notices are included in both wheel and sdist. Regenerate/review them whenever
Cargo.lock changes; retaining notices is separate from checking advisories.


After dependency updates, run `python scripts/update_notices.py --inventory
path/to/inventory.json`, inspect all changed license expressions/texts, and rerun
`python scripts/update_notices.py --check --inventory path/to/inventory.json`.
This copies cached upstream notices, not a custom legal-policy scanner. Full
Rust/Python gate plus security gate are both required; the latter checks notices
against the exact lockfile before fetching advisories.

T-206 remediation resolves PyO3 to 0.29.3 (patched 0.29 family), replacing the
vulnerable 0.23.5 line. Rust binding uses Python.detach and explicitly requires
the GIL for module import. Wheel/ABI support beyond the tested local platform
remains unverified; this dependency fix is not a new public API or release.


## Packaging and CI (T-205)

Run `python scripts/package_check.py --python /absolute/path/to/python` with a
supported Python containing venv/ensurepip; the current interpreter supplies
pinned maturin. The runner builds a wheel for the selected interpreter and an
sdist, installs each in its own temporary venv (sdist uses maturin 1.16.0 without
build isolation), asserts installed package/extension paths, and executes the
full suite plus native/cart examples outside the repository. Results and build
artifacts stay under target/package-check/<OS>-<arch>-<version>.

scripts/check.sh now passes its active Python explicitly to maturin and isolates
wheel output by CPython cache tag, preventing stale cross-version wheel installs.

CI workflow .github/workflows/ci.yml uses Ubuntu 24.04 x86_64/macOS 15 arm64 and
CPython 3.11–3.13. It asserts architecture, runs Rust/static/regression/package
gates, stores logs/artifacts and has a separate Linux advisory/license job.
Official actions are pinned to commits whose metadata/license/action inputs
were retrieved in docs/evidence/m2/ci-action-pins.json. Current GitHub runner
labels/architectures were checked against the hosted-runner reference, not guessed.
No workflow has been pushed or executed: the workspace has no Git remote, and
connected GitHub searches for RedMud/TCore returned no matching accessible repo.
Provide the target repository to run the hosted matrix; until then T-205 remains
BLOCKED and macOS/hosted CI are NOT RUN. Local YAML validation is not a hosted run.
