"""Example of OPTIONAL vectorized batch extension. Requires: pip install polars"""
from __future__ import annotations

import polars as pl
from redmud import Processor, Runtime, Settings


class Sales(Processor[dict, dict]):
    def transform(self, item: dict) -> dict:
        # Scalar fallback is required when batch optimization fails.
        return {"id": item["id"], "gross": item["price"] * item["qty"]}

    def transform_batch(self, items: list[dict]) -> list[dict]:
        return (pl.from_dicts(items)
                .select("id", (pl.col("price") * pl.col("qty")).alias("gross"))
                .to_dicts())


if __name__ == "__main__":
    engine = Runtime(Sales(), Settings(batch_size=500))
    records = ({"id": i, "price": i + 5, "qty": 2} for i in range(10_000))
    print(sum(result.ok for result in engine.process_iter(records)))
    print(engine.snapshot())
