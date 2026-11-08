from dataclasses import dataclass
from decimal import Decimal
import unittest

from redmud.quality import FieldProfile, OutputProfiler, Rule, get_path


@dataclass
class Nested:
    value: int


class TestQuality(unittest.TestCase):
    def test_paths_support_mappings_and_dataclasses(self):
        self.assertEqual(get_path({"obj": Nested(42)}, "obj.value"), 42)
        self.assertNotEqual(get_path({}, "obj.value"), None)

    def test_profile_none_missing_and_types(self):
        p = OutputProfiler(("v",))
        for value in (None, 2, 4, True):
            p.observe({"v": value})
        p.observe({})
        v = p.snapshot()["fields"]["v"]
        self.assertEqual((v["observed"], v["nulls"], v["missing"]), (5, 1, 1))
        self.assertEqual(v["numeric_count"], 2)
        self.assertEqual(v["mean"], 3)
        self.assertEqual(v["stddev_population"], 1)

    def test_decimal_profile_is_descriptive_not_exact(self):
        p = OutputProfiler(("amount",))
        p.observe({"amount": Decimal("1.25")})
        p.observe({"amount": Decimal("2.75")})
        stats = p.snapshot()["fields"]["amount"]
        self.assertEqual(stats["numeric_count"], 2)
        self.assertEqual(stats["mean"], 2.0)

    def test_bad_rule_name_rejected(self):
        with self.assertRaises(ValueError):
            Rule("bad\"name", lambda x: True)

    def test_invalid_paths_rejected(self):
        with self.assertRaises(ValueError):
            OutputProfiler(("a", "a"))
        with self.assertRaises(ValueError):
            OutputProfiler(("a..b",))


if __name__ == "__main__":
    unittest.main()
