from __future__ import annotations

import json
import unittest

from redmud import (BatchSizeMismatch, ProcessingError, Processor, Rule, Runtime,
                   Settings)


class Multiply(Processor[dict, dict]):
    def transform(self, item):
        return {"v": item["v"] * 2}


class Validated(Multiply):
    def input_rules(self):
        return (
            Rule("positive", lambda value: value["v"] > 0),
            Rule("odd_warning", lambda value: value["v"] % 2 == 0,
                 severity="warn"),
        )

    def output_rules(self):
        return (Rule("below_ten", lambda value: value["v"] < 10),)


class Vectorized(Multiply):
    def __init__(self):
        self.calls = 0

    def transform_batch(self, items):
        self.calls += 1
        return [{"v": value["v"] * 2} for value in items]


class FailVector(Vectorized):
    def transform_batch(self, items):
        raise RuntimeError("batch is unavailable")


class WrongLength(Vectorized):
    def transform_batch(self, items):
        return []


class RaiseScalar(Multiply):
    def transform(self, item):
        if item["v"] == 13:
            raise ArithmeticError("secret internal details")
        return super().transform(item)


class TestRuntime(unittest.TestCase):
    def test_json_and_identity_input(self):
        engine = Runtime(Multiply())
        result = list(engine.process_iter([b'{"v": 2}', '{"v": 3}', {"v": 4}]))
        self.assertEqual([r.value["v"] for r in result], [4, 6, 8])
        self.assertEqual([r.index for r in result], [0, 1, 2])

    def test_default_batch_sequence_has_no_custom_batch(self):
        engine = Runtime(Multiply(), Settings(batch_size=2))
        self.assertEqual(len(list(engine.process_iter([{"v": i} for i in range(5)]))), 5)

    def test_parse_failure_is_isolated(self):
        engine = Runtime(Multiply())
        out = engine.process_batch([b'{oops', b'{"v": 2}'])
        self.assertEqual([x.status for x in out], ["error", "ok"])
        self.assertEqual(out[0].error_stage, "parse")
        self.assertIsNone(out[0].error_message)

    def test_transform_failure_is_isolated(self):
        out = Runtime(RaiseScalar()).process_batch([{"v": 13}, {"v": 2}])
        self.assertEqual([x.status for x in out], ["error", "ok"])
        self.assertEqual(out[0].error_type, "ArithmeticError")
        self.assertNotIn("secret", str(out[0]))

    def test_opt_in_error_message(self):
        out = Runtime(RaiseScalar(), Settings(expose_error_details=True)).process_one({"v": 13})
        self.assertEqual(out.error_message, "secret internal details")

    def test_rule_warning_and_reject_and_output(self):
        engine = Runtime(Validated())
        out = engine.process_batch([{"v": 2}, {"v": 3}, {"v": -1}, {"v": 6}])
        self.assertEqual([r.status for r in out], ["ok", "ok", "rejected", "rejected"])
        self.assertEqual([r.issues[0].rule if r.issues else None for r in out],
                         [None, "odd_warning", "positive", "below_ten"])
        self.assertEqual(out[-1].issues[0].stage, "output")
        self.assertIsNone(out[-1].value)
        self.assertEqual(engine.metrics.statuses["rejected"], 2)

    def test_rule_exception_isolated(self):
        engine = Runtime(Multiply(), input_rules=[Rule("bad_key", lambda v: v["missing"] == 1)])
        out = engine.process_batch([{"v": 3}])
        self.assertEqual(out[0].status, "error")
        self.assertEqual(out[0].error_stage, "input_quality")

    def test_input_rules_duplicate_name(self):
        with self.assertRaises(ValueError):
            Runtime(Validated(), input_rules=[Rule("positive", lambda v: True)])

    def test_batch_vectorized_preserves_order_after_reject(self):
        engine = Runtime(Vectorized(), input_rules=[Rule("v_positive", lambda x: x["v"] > 0)])
        out = engine.process_batch([{"v": 1}, {"v": -1}, {"v": 3}])
        self.assertEqual([r.status for r in out], ["ok", "rejected", "ok"])
        self.assertEqual([r.value for r in out], [{"v": 2}, None, {"v": 6}])
        self.assertEqual(engine.processor.calls, 1)

    def test_batch_fallback_to_scalar(self):
        engine = Runtime(FailVector())
        out = engine.process_batch([{"v": 1}, {"v": 2}])
        self.assertEqual([r.value for r in out], [{"v": 2}, {"v": 4}])
        self.assertEqual(engine.metrics.batch_fallbacks, 1)

    def test_batch_mismatch_fallback_disabled(self):
        engine = Runtime(WrongLength(), Settings(fallback_to_scalar=False))
        out = engine.process_batch([{"v": 1}, {"v": 2}])
        self.assertTrue(all(r.error_type == "BatchSizeMismatch" for r in out))
        self.assertEqual(out[0].error_stage, "transform_batch")

    def test_batch_mismatch_fallback_enabled(self):
        engine = Runtime(WrongLength())
        out = engine.process_batch([{"v": 1}, {"v": 2}])
        self.assertTrue(all(r.ok for r in out))
        self.assertEqual(engine.metrics.batch_fallbacks, 1)

    def test_fail_fast(self):
        engine = Runtime(Multiply(), Settings(on_error="raise"))
        with self.assertRaises(ProcessingError) as ctx:
            engine.process_batch([b'{'])
        self.assertEqual(ctx.exception.result.error_stage, "parse")

    def test_iterator_lazy_and_bounded(self):
        seen = []
        def infinite():
            for i in range(1000):
                seen.append(i)
                yield {"v": i}
        engine = Runtime(Multiply(), Settings(batch_size=4))
        iterator = engine.process_iter(infinite())
        self.assertEqual(len(seen), 0)
        self.assertEqual(next(iterator).value, {"v": 0})
        self.assertEqual(len(seen), 4)
        self.assertEqual([next(iterator).index for _ in range(5)], [1,2,3,4,5])
        self.assertEqual(len(seen), 8)

    def test_empty_batch_and_empty_iterator(self):
        engine = Runtime(Multiply())
        self.assertEqual(engine.process_batch([]), [])
        self.assertEqual(list(engine.process_iter(iter([]))), [])

    def test_output_quality_profiles(self):
        engine = Runtime(Multiply(), Settings(output_fields=("v", "missing", "null")))
        out = engine.process_batch([{"v": 3}, {"v": 2}])
        self.assertTrue(all(x.ok for x in out))
        profile = engine.quality.snapshot()["fields"]
        self.assertEqual(profile["v"]["numeric_count"], 2)
        self.assertEqual(profile["v"]["mean"], 5.0)
        self.assertEqual(profile["missing"]["missing"], 2)
        self.assertEqual(profile["null"]["missing"], 2)
        self.assertNotIn("v\": 3", json.dumps(profile))

    def test_field_sampling(self):
        engine = Runtime(Multiply(), Settings(output_fields=("v",), field_sample_every=2))
        engine.process_batch([{"v": i} for i in range(5)])
        self.assertEqual(engine.quality.snapshot()["fields"]["v"]["observed"], 2)

    def test_prometheus_metrics(self):
        engine = Runtime(Multiply(), Settings(timing_sample_every=1))
        engine.process_batch([{"v": 2}])
        output = engine.metrics.prometheus_text()
        self.assertIn('redmud_records_total{status="ok"} 1', output)
        self.assertIn('redmud_stage_duration_seconds_count{stage="transform"}', output)

    def test_profile_reports_and_bounded_input(self):
        engine = Runtime(Multiply())
        report = engine.profile(({"v": i} for i in range(100)), max_records=7)
        self.assertEqual(report.records, 7)
        self.assertGreaterEqual(report.peak_traced_bytes, 0)
        self.assertIn("function calls", report.top_functions)
        self.assertEqual(engine.metrics.processed, 7)

    def test_settings_validation(self):
        for config in (dict(batch_size=0), dict(timing_sample_every=-1),
                       dict(field_sample_every=0), dict(on_error="discard")):
            with self.subTest(config=config), self.assertRaises(ValueError):
                Settings(**config)


    def test_output_rule_exception_isolated(self):
        engine = Runtime(Multiply(), output_rules=[Rule("bad_output", lambda x: x["not_there"] > 0)])
        out = engine.process_batch([{"v": 1}, {"v": 2}])
        self.assertEqual([r.status for r in out], ["error", "error"])
        self.assertEqual([r.error_stage for r in out], ["output_quality", "output_quality"])

    def test_output_warning_is_success(self):
        engine = Runtime(Multiply(), output_rules=[Rule("threshold", lambda x: x["v"] < 3, severity="warn")])
        out = engine.process_one({"v": 3})
        self.assertTrue(out.ok)
        self.assertEqual(out.value, {"v": 6})
        self.assertEqual(out.issues[0].severity, "warn")

    def test_many_mixed_records_never_drop_or_reorder(self):
        engine = Runtime(Validated(), Settings(batch_size=7))
        raw = [b'{broken' if i % 13 == 0 else {"v": i - 7} for i in range(123)]
        out = list(engine.process_iter(raw))
        self.assertEqual(len(out), len(raw))
        self.assertEqual([r.index for r in out], list(range(len(raw))))
        self.assertEqual(engine.metrics.processed, len(raw))
        self.assertEqual(sum(x.status == "error" for x in out), 10)

    def test_one_engine_monotonic_index_across_calls(self):
        engine = Runtime(Multiply())
        self.assertEqual(engine.process_one({"v": 1}).index, 0)
        self.assertEqual(engine.process_batch([{"v": 2}, {"v": 3}])[-1].index, 2)

    def test_none_as_successful_value(self):
        class NullProcessor(Processor[dict, type(None)]):
            def transform(self, item):
                return None
        out = Runtime(NullProcessor()).process_one({"x": 1})
        self.assertTrue(out.ok)
        self.assertIsNone(out.value)

    def test_elapsed_time_includes_calculation(self):
        import time
        class Slow(Processor[dict, dict]):
            def transform(self, item):
                time.sleep(0.005)
                return item
        engine = Runtime(Slow(), Settings(timing_sample_every=0))
        engine.process_one({"x": 1})
        self.assertGreaterEqual(engine.metrics.snapshot()["elapsed_seconds"], 0.004)

    def test_invalid_prometheus_prefix(self):
        engine = Runtime(Multiply())
        with self.assertRaises(ValueError):
            engine.metrics.prometheus_text("9bad")

    def test_nested_custom_parser(self):
        from examples.cart import CartTransform, sample
        engine = Runtime(CartTransform())
        out = engine.process_one(sample())
        self.assertEqual(out.status, "ok")
        self.assertEqual(out.value["total_minor"], 357000)
        self.assertEqual(out.value["subtotal_minor"], 395000)


if __name__ == "__main__":
    unittest.main()
