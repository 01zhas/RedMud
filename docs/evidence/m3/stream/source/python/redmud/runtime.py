"""Source/sink-agnostic, bounded-memory transform runtime.

This module deliberately contains no network I/O, checkpoints, queues, or workers.
Processors MUST be pure; the runtime may replay a failed batch via scalar calls.
"""

from __future__ import annotations

import cProfile
import io
import json
import pstats
import tracemalloc
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, replace
from itertools import islice
from time import perf_counter_ns
from typing import Any, Generic, Literal, TypeVar

from .metrics import Metrics
from .quality import Issue, OutputProfiler, Rule, Error

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
Status = Literal["ok", "rejected", "error"]
Stage = Literal["validation", "parse", "input_quality", "transform", "transform_batch", "output_quality"]


class Processor(ABC, Generic[InputT, OutputT]):
    """Implement transform(); optionally override parse(), rules(), transform_batch()."""

    def parse(self, raw: Any) -> InputT:
        """JSON for bytes/str, identity for already decoded objects."""
        if isinstance(raw, (bytes, bytearray, str)):
            return json.loads(raw)  # type: ignore[return-value]
        return raw  # type: ignore[return-value]

    @abstractmethod
    def transform(self, item: InputT) -> OutputT:
        """Pure per-record business logic, without I/O or external side effects."""

    def transform_batch(self, items: Sequence[InputT]) -> Sequence[OutputT]:
        """Optional vectorized calculation. Must preserve order and output count."""
        return [self.transform(item) for item in items]

    def input_rules(self) -> Sequence[Rule]:
        return ()

    def output_rules(self) -> Sequence[Rule]:
        return ()


@dataclass(frozen=True, slots=True)
class Settings:
    batch_size: int = 256
    on_error: Literal["collect", "raise", "skip"] = "collect"
    fallback_to_scalar: bool = True
    timing_sample_every: int = 100  # 0 means no stage timing
    output_fields: tuple[str, ...] = ()  # dotted fields: 'totals.net'
    field_sample_every: int = 1
    expose_error_details: bool = False

    def __post_init__(self) -> None:
        if type(self.batch_size) is not int or self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.on_error not in ("collect", "raise", "skip"):
            raise ValueError("on_error must be collect or raise")
        if self.timing_sample_every < 0:
            raise ValueError("timing_sample_every must be >= 0")
        if self.field_sample_every <= 0:
            raise ValueError("field_sample_every must be positive")


@dataclass(frozen=True, slots=True)
class RecordResult(Generic[OutputT]):
    index: int
    status: Status
    value: OutputT | None = None
    issues: tuple[Issue, ...] = ()
    error_stage: Stage | None = None
    error_type: str | None = None
    error_message: str | None = None

    errors: tuple[Error, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == "ok"


class ProcessingError(RuntimeError):
    """Raised in fail-fast mode; the original exception is chained when possible."""

    def __init__(self, result: RecordResult[Any]):
        self.result = result
        super().__init__(f"Record {result.index}: {result.status} at "
                         f"{result.error_stage or 'quality_check'}")


class BatchSizeMismatch(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProfileReport:
    records: int
    elapsed_ms: float
    peak_traced_bytes: int | None
    top_functions: str


class Runtime(Generic[InputT, OutputT]):
    """Single-threaded per instance. Use separate instances for independent workers."""

    def __init__(
        self,
        processor: Processor[InputT, OutputT],
        settings: Settings | None = None,
        *,
        input_rules: Sequence[Rule] = (),
        output_rules: Sequence[Rule] = (),
    ):
        self.processor = processor
        self.settings = settings or Settings()
        self._input_rules = (*processor.input_rules(), *input_rules)
        self._output_rules = (*processor.output_rules(), *output_rules)
        self._check_duplicate_rules(self._input_rules, "input")
        self._check_duplicate_rules(self._output_rules, "output")
        self.metrics = Metrics()
        self.quality = OutputProfiler(self.settings.output_fields)
        self._index = 0
        self._ok_count = 0
        self._batch_count = 0
        self._custom_batch = type(processor).transform_batch is not Processor.transform_batch

    @staticmethod
    def _check_duplicate_rules(rules: Sequence[Rule], stage: str) -> None:
        names = [rule.name for rule in rules]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate {stage} rule names")

    def _measured(self, stage: Stage, fn: Callable[[], Any], sampled: bool) -> Any:
        if not sampled:
            return fn()
        begin = perf_counter_ns()
        try:
            return fn()
        finally:
            self.metrics.timing(stage, perf_counter_ns() - begin)

    def _sample(self, index: int) -> bool:
        n = self.settings.timing_sample_every
        return n > 0 and index % n == 0

    @staticmethod
    def _run_rules(rules: Sequence[Rule], value: Any, stage: Literal["input", "output"]
                   ) -> tuple[Issue, ...]:
        issues: list[Issue] = []
        for rule in rules:
            if not rule.check(value):
                issues.append(Issue(stage, rule.name, rule.severity, rule.message))
        return tuple(issues)

    def _exception(self, index: int, stage: Stage, exc: Exception,
                   issues: tuple[Issue, ...] = ()) -> RecordResult[OutputT]:
        default_json_error = (stage == "parse" and type(self.processor).parse is Processor.parse
                              and isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError)))
        code = "invalid_json" if default_json_error else "callback_error"
        return RecordResult(
            index=index,
            status="error",
            errors=(Error(code, "", stage, "Invalid JSON" if default_json_error else "Python callback failed"),),
            issues=issues,
            error_stage=stage,
            error_type=type(exc).__name__,
            error_message=str(exc) if self.settings.expose_error_details else None,
        )

    def _finalize(self, index: int, value: OutputT,
                  input_issues: tuple[Issue, ...]) -> RecordResult[OutputT]:
        try:
            output_issues = self._measured(
                "output_quality",
                lambda: self._run_rules(self._output_rules, value, "output"),
                self._sample(index),
            )
            issues = input_issues + output_issues
            if any(i.severity == "reject" for i in output_issues):
                return RecordResult(index=index, status="rejected", issues=issues)
            return RecordResult(index=index, status="ok", value=value, issues=issues)
        except Exception as exc:
            return self._exception(index, "output_quality", exc, input_issues)

    def process_batch(self, records: Sequence[Any]) -> list[RecordResult[OutputT]]:
        """Process one bounded batch; return statuses in exact input order."""
        begin = perf_counter_ns()
        self.metrics.start()
        if not records:
            self.metrics.batch(0, perf_counter_ns()-begin)
            return []
        results: list[RecordResult[OutputT] | None] = [None] * len(records)
        pending: list[tuple[int, int, InputT, tuple[Issue, ...]]] = []
        for slot, raw in enumerate(records):
            index = self._index
            self._index += 1
            try:
                parsed = self._measured("parse", lambda: self.processor.parse(raw),
                                        self._sample(index))
            except Exception as exc:
                results[slot] = self._exception(index, "parse", exc)
                continue
            try:
                issues = self._measured(
                    "input_quality",
                    lambda: self._run_rules(self._input_rules, parsed, "input"),
                    self._sample(index),
                )
            except Exception as exc:
                results[slot] = self._exception(index, "input_quality", exc)
                continue
            if any(i.severity == "reject" for i in issues):
                results[slot] = RecordResult(index=index, status="rejected", issues=issues)
            else:
                pending.append((slot, index, parsed, issues))

        def scalar_transform() -> None:
            for slot, index, parsed, issues in pending:
                try:
                    transformed = self._measured(
                        "transform", lambda item=parsed: self.processor.transform(item),
                        self._sample(index),
                    )
                    results[slot] = self._finalize(index, transformed, issues)
                except Exception as exc:
                    results[slot] = self._exception(index, "transform", exc, issues)

        if pending:
            if self._custom_batch and len(pending) > 1:
                self._batch_count += 1
                try:
                    outputs = self._measured(
                        "transform_batch",
                        lambda: self.processor.transform_batch([p[2] for p in pending]),
                        self._sample(self._batch_count - 1),
                    )
                    if len(outputs) != len(pending):
                        raise BatchSizeMismatch(
                            f"transform_batch returned {len(outputs)} rows, "
                            f"expected {len(pending)}"
                        )
                except Exception as exc:
                    self.metrics.batch_fallbacks += 1
                    if self.settings.fallback_to_scalar:
                        scalar_transform()
                    else:
                        for slot, index, _parsed, issues in pending:
                            results[slot] = self._exception(index, "transform_batch", exc, issues)
                else:
                    for (slot, index, _parsed, issues), output in zip(pending, outputs):
                        results[slot] = self._finalize(index, output, issues)
            else:
                scalar_transform()

        # Exactly one result for every input, including malformed/invalid entries.
        final: list[RecordResult[OutputT]] = []
        for result in results:
            assert result is not None, "internal runtime error: dropped input record"
            if not result.errors:
                errors = tuple(Error(i.rule, "", "validation", i.message) for i in result.issues if i.severity == "reject")
                if result.error_stage:
                    errors += (Error("callback_error", "", result.error_stage, "Python callback failed"),)
                result = replace(result, errors=errors)
            self.metrics.observe(result)
            if result.ok:
                self._ok_count += 1
                if (self.settings.output_fields and
                        self._ok_count % self.settings.field_sample_every == 0):
                    self.quality.observe(result.value)
            final.append(result)
        self.metrics.batch(len(records), perf_counter_ns()-begin)
        if self.settings.on_error == "raise":
            for result in final:
                if not result.ok:
                    raise ProcessingError(result)
        return [r for r in final if r.ok] if self.settings.on_error == "skip" else final

    def process_one(self, record: Any) -> RecordResult[OutputT]:
        settings = self.settings
        try:
            if settings.on_error == "skip": self.settings = replace(settings, on_error="collect")
            return self.process_batch([record])[0]
        finally:
            self.settings = settings

    def process_iter(self, records: Iterable[Any]) -> Iterator[RecordResult[OutputT]]:
        """Lazy iteration with bounded batches (no full-input materialization)."""
        iterator = iter(records)
        while batch := list(islice(iterator, self.settings.batch_size)):
            yield from self.process_batch(batch)

    def snapshot(self) -> dict[str, Any]:
        return {"metrics": self.metrics.snapshot(), "quality": self.quality.snapshot()}

    def profile(self, records: Iterable[Any], *, max_records: int = 1000,
                top: int = 15) -> ProfileReport:
        """Opt-in cProfile + tracemalloc over a bounded sample; consumes records.

        All sampled records are processed and included in metrics. No results retained.
        """
        if type(max_records) is not int or type(top) is not int or max_records <= 0 or top <= 0:
            raise ValueError("max_records and top must be positive")
        profiler = cProfile.Profile()
        tracing_started_here = not tracemalloc.is_tracing()
        if tracing_started_here:
            tracemalloc.start()
        before_peak = tracemalloc.get_traced_memory()[1]
        begin = perf_counter_ns()
        count = 0
        def sample() -> Iterator[Any]:
            nonlocal count
            for record in islice(records, max_records):
                count += 1
                yield record
        try:
            profiler.enable()
            try:
                for _ in self.process_iter(sample()):
                    pass
            finally:
                profiler.disable()
            elapsed = (perf_counter_ns() - begin) / 1e6
            peak = tracemalloc.get_traced_memory()[1]
            report_stream = io.StringIO()
            pstats.Stats(profiler, stream=report_stream).sort_stats("cumulative").print_stats(top)
            return ProfileReport(count, elapsed,
                                 max(0, peak - before_peak), report_stream.getvalue())
        finally:
            if tracing_started_here:
                tracemalloc.stop()
