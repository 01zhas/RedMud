"""A transform-only runtime does not depend on where data comes from or goes."""
from __future__ import annotations

import json
from collections.abc import Iterable

from redmud import Processor, Runtime


class Multiply(Processor[dict, dict]):
    def transform(self, row):
        return {"id": row["id"], "result": row["x"] * 2}


def fake_api_source() -> Iterable[bytes]:
    yield json.dumps({"id": 1, "x": 10}).encode()
    yield json.dumps({"id": 2, "x": 20}).encode()


def fake_database_source() -> Iterable[dict]:
    yield {"id": 3, "x": 30}
    yield {"id": 4, "x": 40}


def collect_for_destination(source: Iterable, destination: list[dict]) -> None:
    transform = Runtime(Multiply())
    for record in transform.process_iter(source):
        if record.ok:
            destination.append(record.value)
        else:
            # In production the caller decides retries, audit and dead-letter handling.
            raise RuntimeError(f"Transform failed at position {record.index}")


if __name__ == "__main__":
    sink: list[dict] = []
    collect_for_destination(fake_api_source(), sink)
    collect_for_destination(fake_database_source(), sink)
    print(sink)
