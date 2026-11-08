"""Dependency-free counters and sampled stage timings."""

from __future__ import annotations

from collections import Counter
import re
from dataclasses import dataclass
from time import monotonic_ns
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .runtime import RecordResult


@dataclass(slots=True)
class Timing:
    count: int = 0
    total_ns: int = 0
    max_ns: int = 0

    def observe(self, duration_ns: int) -> None:
        self.count += 1
        self.total_ns += duration_ns
        self.max_ns = max(self.max_ns, duration_ns)

    def snapshot(self) -> dict[str, float | int]:
        return {
            "samples": self.count,
            "mean_ms": self.total_ns / self.count / 1e6 if self.count else 0.0,
            "max_ms": self.max_ns / 1e6,
            "total_seconds": self.total_ns / 1e9,
        }


class Metrics:
    def __init__(self) -> None:
        self.processed = 0
        self.error_counts: Counter[str] = Counter()
        self.batch_sizes: Counter[str] = Counter()
        self.batch_count = 0
        self.batch_size_total = 0
        self.batch_size_min: int | None = None
        self.batch_size_max: int | None = None
        self.statuses: Counter[str] = Counter()
        self.rule_failures: Counter[tuple[str, str, str]] = Counter()
        self.timings: dict[str, Timing] = {}
        self.batch_fallbacks = 0
        self._start_ns: int | None = None

    def start(self) -> None:
        if self._start_ns is None:
            self._start_ns = monotonic_ns()

    def observe(self, result: RecordResult[Any]) -> None:
        self.start()
        self.processed += 1
        self.statuses[result.status] += 1
        for error in result.errors:
            self.error_counts[error.code] += 1
        for issue in result.issues:
            self.rule_failures[(issue.stage, issue.rule, issue.severity)] += 1

    def timing(self, stage: str, duration_ns: int) -> None:
        self.timings.setdefault(stage, Timing()).observe(duration_ns)

    def batch(self, size: int, duration_ns: int) -> None:
        """Fixed-cardinality histogram plus exact scalar summary for completed calls."""
        if size == 0: bucket = '0'
        elif size == 1: bucket = '1'
        elif size < 64: bucket = '2-63'
        elif size < 256: bucket = '64-255'
        elif size < 1000: bucket = '256-999'
        else: bucket = '1000+'
        self.batch_sizes[bucket] += 1
        self.batch_count += 1
        self.batch_size_total += size
        self.batch_size_min = size if self.batch_size_min is None else min(self.batch_size_min, size)
        self.batch_size_max = size if self.batch_size_max is None else max(self.batch_size_max, size)
        self.timing('batch', duration_ns)

    def snapshot(self) -> dict[str, Any]:
        elapsed = ((monotonic_ns() - self._start_ns) / 1e9
                   if self._start_ns is not None else 0.0)
        return {
            "processed": self.processed,
            "errors_by_code": dict(self.error_counts),
            "batch_sizes": dict(self.batch_sizes),
            "batch_size_summary": {"count": self.batch_count, "sum": self.batch_size_total,
                                   "min": self.batch_size_min, "max": self.batch_size_max},
            "statuses": dict(self.statuses),
            "batch_fallbacks": self.batch_fallbacks,
            "elapsed_seconds": elapsed,
            "throughput_per_second": self.processed / elapsed if elapsed > 0 else 0.0,
            "stages": {name: timing.snapshot() for name, timing in self.timings.items()},
            "rule_failures": [
                {"stage": stage, "rule": rule, "severity": severity, "count": count}
                for (stage, rule, severity), count in sorted(self.rule_failures.items())
            ],
        }

    def prometheus_text(self, prefix: str = "redmud") -> str:
        """Export bounded-cardinality text metrics; no web server dependency."""
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", prefix):
            raise ValueError("Invalid Prometheus metric prefix")
        lines = [f"# TYPE {prefix}_records_total counter"]
        for status in ("ok", "rejected", "error"):
            lines.append(f'{prefix}_records_total{{status="{status}"}} '
                         f'{self.statuses[status]}')
        lines.extend([
            f"# TYPE {prefix}_batch_fallbacks_total counter",
            f"{prefix}_batch_fallbacks_total {self.batch_fallbacks}",
            f"# TYPE {prefix}_stage_duration_seconds summary",
        ])
        for stage, duration in sorted(self.timings.items()):
            lines.extend([
                f'{prefix}_stage_duration_seconds_sum{{stage="{stage}"}} '
                f'{duration.total_ns / 1e9}',
                f'{prefix}_stage_duration_seconds_count{{stage="{stage}"}} '
                f'{duration.count}',
            ])
        lines.append(f"# TYPE {prefix}_quality_failures_total counter")
        for (stage, rule, severity), count in sorted(self.rule_failures.items()):
            lines.append(f'{prefix}_quality_failures_total{{stage="{stage}",'
                         f'rule="{rule}",severity="{severity}"}} {count}')
        return "\n".join(lines) + "\n"
