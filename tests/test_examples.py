import unittest
from redmud import Runtime
from examples.cart import CartTransform, sample
from examples.source_sink_agnostic import (
    fake_api_source, fake_database_source, collect_for_destination,
)


class TestExamples(unittest.TestCase):
    def test_sources_produce_compatible_results(self):
        sink = []
        collect_for_destination(fake_api_source(), sink)
        collect_for_destination(fake_database_source(), sink)
        self.assertEqual([x["result"] for x in sink], [20, 40, 60, 80])

    def test_example_cart_malformed_json(self):
        engine = Runtime(CartTransform())
        out = engine.process_batch([sample(1), b'{oops', sample(2)])
        self.assertEqual([r.status for r in out], ["ok", "error", "ok"])
        self.assertEqual(out[0].value["total_minor"], out[2].value["total_minor"])


if __name__ == '__main__':
    unittest.main()
