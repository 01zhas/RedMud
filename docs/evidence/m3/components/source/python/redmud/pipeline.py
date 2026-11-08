"""Declarative, immutable plans executed by the Rust extension."""
from __future__ import annotations
import json
from collections.abc import Iterable, Iterator, Mapping
from itertools import islice
from time import perf_counter_ns
from typing import Any
from .runtime import RecordResult, ProcessingError, Runtime
from .metrics import Metrics
from .quality import OutputProfiler, Error
from ._limits import MAX_DEPTH, DepthLimit, check_config

class Expr:
    def __init__(self, tree: dict[str, Any]):
        self.tree = tree
    def _binary(self, op: str, other: Any) -> Expr:
        return Expr(dict(op=op, left=self.tree, right=literal(other).tree))
    def __add__(self, other: Any) -> Expr: return self._binary('add', other)
    def __sub__(self, other: Any) -> Expr: return self._binary('sub', other)
    def __mul__(self, other: Any) -> Expr: return self._binary('mul', other)
    def __gt__(self, other: Any) -> Expr: return self._binary('gt', other)
    def __ge__(self, other: Any) -> Expr: return self._binary('ge', other)
    def __eq__(self, other: Any) -> Expr: return self._binary('eq', other)  # type: ignore[override]
    def __bool__(self) -> bool:
        raise TypeError('Use native expressions, not Python boolean operators')

def literal(value: Any) -> Expr:
    return value if isinstance(value, Expr) else Expr(dict(op='literal', value=value))
def field(path: str) -> Expr:
    return Expr(dict(op='field', path=path))
def list_sum(path: str, field: str) -> Expr:
    return Expr(dict(op='sum', path=path, field=field))
def when(condition: Expr, yes: Any, no: Any) -> Expr:
    return Expr(dict(op='if', condition=condition.tree, yes=literal(yes).tree, no=literal(no).tree))

def _validate_json_input(value: Any, active: set[int], depth: int = 1, path: str = "") -> None:
    """Reject json.dumps coercions (notably dict keys and tuple -> list)."""
    if depth > MAX_DEPTH:
        raise DepthLimit(path)
    if value is None or type(value) in (str, int, float, bool):
        return
    if type(value) not in (dict, list):
        raise ValueError('Unsupported input')
    identity = id(value)
    if identity in active:
        raise ValueError('Cyclic input')
    active.add(identity)
    try:
        if isinstance(value, dict):
            if any(not isinstance(key, str) for key in value): raise ValueError('Non-string key')
            for key in sorted(value):
                child = key if not path else path + '.' + key
                _validate_json_input(value[key], active, depth+1, child)
        else:
            for i,item in enumerate(value): _validate_json_input(item, active, depth+1, f"{path}[{i}]")
    finally:
        active.remove(identity)

class Pipeline:
    """Builder returns new pipelines; each instance caches its native plan.

    Instances own mutable counters and should be used by one caller at a time.
    """
    def __init__(self, *, on_error: str = 'collect', metrics: bool = True,
                 output_fields: tuple[str, ...] = (), _steps: tuple = ()):
        if on_error not in ('collect', 'raise', 'skip'):
            raise ValueError('on_error must be collect, raise or skip')
        self.on_error, self.enabled = on_error, metrics
        self._steps = _steps
        self._compiled = None
        self._index = 0
        self.metrics = Metrics()
        self.quality = OutputProfiler(output_fields)
        self.output_fields = output_fields
    def _append(self, **step: Any) -> Pipeline:
        # JSON copy protects the plan from subsequent mutation by its caller.
        try:
            check_config(step)
            step = json.loads(json.dumps(step, allow_nan=False))
        except (TypeError, ValueError, RecursionError):
            raise ValueError('Invalid execution plan') from None
        return Pipeline(on_error=self.on_error, metrics=self.enabled,
                        output_fields=self.output_fields, _steps=(*self._steps, step))
    def require(self, schema: Mapping[str, Any]) -> Pipeline:
        return self._append(op='require', schema=dict(schema))
    def check(self, name: str, expr: Expr, message: str = 'Data quality check failed') -> Pipeline:
        return self._append(op='check', name=name, expr=expr.tree, message=message)
    def derive(self, name: str, expr: Expr) -> Pipeline:
        return self._append(op='derive', name=name, expr=literal(expr).tree)
    def map_list(self, path: str, pipeline: Pipeline) -> Pipeline:
        return self._append(op='map', path=path, plan=dict(steps=pipeline._steps))
    def prepare(self) -> Pipeline:
        if self._compiled is None:
            from ._native import NativePlan
            try:
                check_config(dict(steps=self._steps))
                self._compiled = NativePlan(json.dumps(dict(steps=self._steps), allow_nan=False))
            except (TypeError, ValueError, UnicodeError, RecursionError):
                raise ValueError('Invalid execution plan') from None
        return self
    def run_batch(self, records: Iterable[Any]) -> list[RecordResult]:
        self.prepare()
        begin = perf_counter_ns() if self.enabled else 0
        if self.enabled: self.metrics.start()
        encoded = []
        failures = {}
        for i, raw in enumerate(records):
            try:
                if isinstance(raw, str): raw = raw.encode('utf-8')
                elif not isinstance(raw, bytes):
                    _validate_json_input(raw, set())
                    raw = json.dumps(raw, allow_nan=False).encode('utf-8')
                encoded.append(raw)
            except DepthLimit as exc:
                encoded.append(b'null')
                failures[i] = Error('depth_limit', exc.path, 'parse', 'Depth limit exceeded')
            except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
                encoded.append(b'null')
                failures[i] = Error('invalid_input', '', 'parse', 'Input is not JSON compatible')
        outputs = self._compiled.run_batch(encoded)
        results = []
        for i, output in enumerate(outputs):
            data = json.loads(output)
            errors = ((failures[i],) if i in failures else tuple(Error(**e) for e in data['errors']))
            result = RecordResult(index=self._index, status=('rejected' if errors[0].stage == 'validation' else 'error') if errors else 'ok',
                                  value=None if errors else data['value'], errors=errors,
                                  error_stage=errors[0].stage if errors else None)
            self._index += 1
            if self.enabled: self.metrics.observe(result)
            if result.ok and self.output_fields: self.quality.observe(result.value)
            results.append(result)
        if self.enabled:
            self.metrics.batch(len(encoded), perf_counter_ns()-begin)
        if self.on_error == 'raise':
            for result in results:
                if not result.ok: raise ProcessingError(result)
        return [r for r in results if r.ok] if self.on_error == 'skip' else results
    def run_one(self, record: Any) -> RecordResult:
        # Even skip policy returns the rejected outcome for scalar calls.
        policy = self.on_error
        try:
            if policy == 'skip': self.on_error = 'collect'
            return self.run_batch([record])[0]
        finally: self.on_error = policy
    def run_iter(self, records: Iterable[Any], *, batch_size: int = 1000) -> Iterator[RecordResult]:
        if type(batch_size) is not int or batch_size <= 0: raise ValueError('batch_size must be positive')
        self.prepare()
        iterator = iter(records)
        while batch := list(islice(iterator, batch_size)):
            yield from self.run_batch(batch)
    def snapshot(self) -> dict[str, Any]:
        return dict(metrics=self.metrics.snapshot(), quality=self.quality.snapshot())
    process_iter = run_iter
    profile = Runtime.profile
