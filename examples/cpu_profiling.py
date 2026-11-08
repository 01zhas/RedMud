"""Run: python examples/cpu_profiling.py"""
from redmud import Processor, Runtime, Settings


class Transform(Processor[dict, dict]):
    def transform(self, item):
        return {"value": sum(x * x for x in range(item["n"]))}


if __name__ == "__main__":
    engine = Runtime(Transform(), Settings(batch_size=128, timing_sample_every=1,
                                          output_fields=("value",)))
    report = engine.profile(({"n": 200} for _ in range(2000)), max_records=500)
    print(f"profiled={report.records}, elapsed={report.elapsed_ms:.1f}ms, "
          f"peak_traced_bytes={report.peak_traced_bytes}")
    print(report.top_functions)
    print(engine.snapshot())
