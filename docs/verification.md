# Verification — 2026-11-07

Linux x86_64, Python 3.12.14, Rust stable 1.99.1.

Executed from project root:

- `cargo test`: 3 Rust tests pass.
- `cargo fmt --all --check`: passes after installing rustfmt.
- `python -m pip install .`: built and installed native release extension.
- `python -m unittest discover -s tests -v`: 41 tests pass.
- `python examples/native_cart.py`: cart total 3500.
- `python examples/cart.py`: runs; original dataclass cart total 357000.
- `python examples/cpu_profiling.py`: runs and emits bounded profile.
- `python examples/source_sink_agnostic.py`: results 20, 40, 60, 80.
- `python benchmarks/benchmark.py`: measured results in benchmark-results.txt.
- `maturin build --release`: CPython 3.12 manylinux_2_34 x86_64 wheel built.
- `maturin sdist`: source distribution built.
- Release wheel reinstalled and Python test suite rerun successfully.

Optional Polars example was retained but not executed (optional dependency).
macOS, Windows, other Python versions, RSS measurement, fuzz testing and
parallel execution have not been verified. This initial release does not meet
every aspirational performance/observability requirement; see architecture.md.
