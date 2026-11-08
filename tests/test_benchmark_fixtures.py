import unittest
from benchmarks.workloads import NAMES, Plain, engine, rows, call, signature, verify

class TestBenchmarkFixtures(unittest.TestCase):
    def test_all_modes_have_equal_values_validation_and_errors(self):
        for workload in NAMES:
            for kind in ('bytes','dict'):
                with self.subTest(workload=workload,kind=kind):
                    self.assertEqual(verify(workload,kind,count=80),80)
    def test_mixed_fixture_contains_success_rule_reject_and_parse_failure(self):
        results=Plain('mixed_rejects').run_batch(list(rows('mixed_rejects',100,'bytes')))
        self.assertEqual({r.status for r in results},{'ok','rejected','error'})
        self.assertEqual([r.index for r in results],list(range(100)))
    def test_fixture_seed_and_repeated_batches_are_deterministic(self):
        sample=list(rows('nested_sums',16,'dict'))
        self.assertEqual(sample,list(rows('nested_sums',16,'dict')))
        expected=Plain('nested_sums').run_batch(sample)
        native=engine('native','nested_sums',4)
        results=[]
        for i in range(0,len(sample),4):results+=call(native,sample[i:i+4])
        self.assertEqual([signature(r) for r in results],[signature(r) for r in expected])

    def test_measurement_summary_units_and_percentiles(self):
        from benchmarks.run import summarize, percentile
        case={'records':100}
        samples=[{'phase':'timing','call_ns':1_000_000_000,'batch_ns':[1_000_000,3_000_000],'counts':{'ok':100},'digest':'same'},
                 {'phase':'timing','call_ns':2_000_000_000,'batch_ns':[2_000_000,4_000_000],'counts':{'ok':100},'digest':'same'},
                 {'phase':'rss','rss_peak_bytes':1000,'counts':{'ok':100},'digest':'same'},
                 {'phase':'traced','python_traced_peak_bytes':500,'counts':{'ok':100},'digest':'same'}]
        result=summarize(case,samples)
        self.assertEqual(result['call_seconds_median'],1.5)
        self.assertAlmostEqual(result['records_per_second'],100/1.5)
        self.assertEqual((result['batch_p50_ms'],result['batch_p95_ms']),(2,4))
        self.assertEqual((result['rss_peak_bytes_median'],result['python_traced_peak_bytes']),(1000,500))
        self.assertEqual(percentile([4,1,2,3],.95),4)

    def test_linux_memory_meter_uses_post_exec_high_water(self):
        import sys
        if not sys.platform.startswith('linux'):self.skipTest('Linux /proc-specific meter')
        from benchmarks.run import peak_rss
        value,source=peak_rss()
        self.assertEqual(source,'linux-proc-VmHWM')
        self.assertGreater(value,0)
        self.assertEqual(value%1024,0)
