"""Lightweight, bounded data-quality checks and descriptive field profiles."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from math import isfinite
from numbers import Real
from typing import Any, Literal

Severity = Literal["reject", "warn"]
_MISSING = object()
_TYPE_LABELS = {t: t.__name__ for t in (bool, int, float, str, list, tuple, dict, Decimal)}


@dataclass(frozen=True, slots=True)
class Rule:
    """A pure predicate: True means a record passes this check."""

    name: str
    check: Callable[[Any], bool]
    severity: Severity = "reject"
    message: str = "Data quality check failed"

    def __post_init__(self) -> None:
        if not self.name or not self.name.isascii() or not self.name.replace("_", "").isalnum():
            raise ValueError("Rule name must be alphanumeric or underscores")
        if not callable(self.check):
            raise ValueError("Rule check must be callable")
        if self.severity not in ("reject", "warn"):
            raise ValueError("severity must be 'reject' or 'warn'")


@dataclass(frozen=True, slots=True)
class Issue:
    stage: Literal["input", "output"]
    rule: str
    severity: Severity
    message: str


def get_path(obj: Any, path: str) -> Any:
    """Read an explicitly configured dotted path, returning a sentinel if missing.

    Only map keys and ordinary object attributes are supported, not list indexes.
    """
    current = obj
    for part in path.split("."):
        if isinstance(current, Mapping):
            if part not in current:
                return _MISSING
            current = current[part]
        else:
            try:
                current = getattr(current, part)
            except AttributeError:
                return _MISSING
    return current


@dataclass(slots=True)
class FieldProfile:
    path: str
    observed: int = 0
    missing: int = 0
    nulls: int = 0
    numeric_count: int = 0
    mean: float = 0.0
    _m2: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    types: Counter[str] = field(default_factory=Counter)

    def observe(self, value: Any) -> None:
        self.observed += 1
        if value is _MISSING:
            self.missing += 1
            return
        if value is None:
            self.nulls += 1
            return
        self.types[_TYPE_LABELS.get(type(value), "other")] += 1
        if isinstance(value, (Real, Decimal)) and not isinstance(value, bool):
            number = float(value)
            if not isfinite(number):
                return
            self.numeric_count += 1
            self.minimum = number if self.minimum is None else min(self.minimum, number)
            self.maximum = number if self.maximum is None else max(self.maximum, number)
            delta = number - self.mean
            self.mean += delta / self.numeric_count
            self._m2 += delta * (number - self.mean)

    def snapshot(self) -> dict[str, Any]:
        return {
            "observed": self.observed,
            "missing": self.missing,
            "nulls": self.nulls,
            "types": dict(self.types),
            "numeric_count": self.numeric_count,
            "mean": self.mean if self.numeric_count else None,
            "stddev_population": (self._m2 / self.numeric_count) ** 0.5
            if self.numeric_count else None,
            "min": self.minimum,
            "max": self.maximum,
        }


class OutputProfiler:
    """O(number_of_configured_fields) memory. Never stores raw record values."""

    def __init__(self, paths: tuple[str, ...]):
        if any(not path or ".." in path for path in paths):
            raise ValueError("Invalid field path")
        if len(set(paths)) != len(paths):
            raise ValueError("Duplicate field paths")
        self._fields = {name: FieldProfile(name) for name in paths}
        self.errors = 0

    def observe(self, obj: Any) -> None:
        for name, profile in self._fields.items():
            try:
                profile.observe(get_path(obj, name))
            except Exception:
                # Observability must never break the transform hot path.
                self.errors += 1

    def snapshot(self) -> dict[str, Any]:
        return {"fields": {k: v.snapshot() for k, v in self._fields.items()},
                "profiling_errors": self.errors}


@dataclass(frozen=True, slots=True)
class Error:
    code: str
    path: str
    stage: str
    message: str
