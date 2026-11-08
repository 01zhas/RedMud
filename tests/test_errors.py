import json
import unittest
from redmud import Pipeline, Processor, Runtime, Rule, Settings, field as F

class Identity(Processor):
    def transform(self,row):return row

class TestErrors(unittest.TestCase):
    def test_ac107_native_classification_and_redaction(self):
        secret='private-payload-123'
        cases=[(Pipeline(),b'{'+secret.encode(),'error','invalid_json','parse'),
               (Pipeline(),{'x':object()},'error','invalid_input','parse'),
               (Pipeline().require({'x':'int'}),{'x':secret},'rejected','invalid_type','validation'),
               (Pipeline().check('positive',F('x')>0),{'x':-1},'rejected','positive','validation'),
               (Pipeline().derive('v',F('x')+1),{'x':None},'error','null_value','transform'),
               (Pipeline().derive('v',F('x')+1),{'x':2**63-1},'error','overflow','transform')]
        for p,raw,status,code,stage in cases:
            with self.subTest(code=code):
                r=p.run_one(raw)
                self.assertEqual((r.status,r.errors[0].code,r.errors[0].stage),(status,code,stage))
                self.assertIsNone(r.value)
                self.assertNotIn(secret,repr(r))
                self.assertNotIn(secret,json.dumps(p.snapshot()))
                self.assertEqual(p.metrics.error_counts[code],1)
        p=Pipeline().derive('partial',1).check('fail',F('partial')>1)
        self.assertIsNone(p.run_one({}).value)
    def test_ac107_python_stages_and_safe_exception(self):
        secret='private-payload-123'
        class Broken(Identity):
            def transform(self,row):raise ValueError(secret)
        for hook,engine in [('parse',Runtime(Identity())),('transform',Runtime(Broken())),
                            ('input_quality',Runtime(Identity(),input_rules=[Rule('boom',lambda r:1/0)])),
                            ('output_quality',Runtime(Identity(),output_rules=[Rule('boom',lambda r:1/0)]))]:
            r=engine.process_one(b'{' if hook=='parse' else {})
            self.assertEqual(r.status,'error')
            self.assertEqual(r.errors[0].stage,hook)
            self.assertEqual(r.errors[0].code,'invalid_json' if hook=='parse' else 'callback_error')
            self.assertNotIn(secret,repr(r))
            self.assertNotIn(secret,json.dumps(engine.snapshot()))
        e=Runtime(Broken(),Settings(expose_error_details=True))
        self.assertEqual(e.process_one({}).error_message,secret)
        for direction in ('input','output'):
            e=Runtime(Identity(),**{direction+'_rules':[Rule('reject',lambda r:False)]})
            r=e.process_one({})
            self.assertEqual((r.status,r.errors[0].code,r.errors[0].stage),('rejected','reject','validation'))
        e=Runtime(Identity(),input_rules=[Rule('warn',lambda r:False,severity='warn')])
        self.assertTrue(e.process_one({}).ok)
    def test_ac107_custom_parser_is_callback(self):
        class Parser(Identity):
            def parse(self,raw):raise json.JSONDecodeError('hidden','hidden',0)
        self.assertEqual(Runtime(Parser()).process_one(b'{').errors[0].code,'callback_error')
