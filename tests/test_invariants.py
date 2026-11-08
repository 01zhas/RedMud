"""AC-201: seeded independent oracles, not expression-tree replay in Python."""
import copy
import json
import operator
import random
import unittest
from redmud import Pipeline, Processor, Runtime, Settings, field as F, list_sum

SEED = 20261107
MIN, MAX = -2**63, 2**63-1


def plan():
    item = (Pipeline().require({'price': 'int', 'quantity': 'int'})
            .check('positive', F('quantity') > 0)
            .derive('total', F('price') * F('quantity')))
    order = Pipeline().map_list('items', item).derive('total', list_sum('items', 'total'))
    return Pipeline().map_list('orders', order).derive('total', list_sum('orders', 'total'))


class Failure(Exception):
    def __init__(self, status, code, path, stage):
        self.details = status, code, path, stage


def reference(row):
    """Small fixture-specific oracle with explicitly checked integer intermediates."""
    row = copy.deepcopy(row)
    for oi, order in enumerate(row['orders']):
        opath = f'orders[{oi}]'
        for ii, item in enumerate(order['items']):
            scope = f'{opath}.items[{ii}]'
            for name in ('price', 'quantity'):
                path = scope + '.' + name
                if name not in item:
                    raise Failure('rejected', 'missing_field', path, 'validation')
                value = item[name]
                if value is None or type(value) is not int or not MIN <= value <= MAX:
                    raise Failure('rejected', 'null_value' if value is None else 'invalid_type', path, 'validation')
            if item['quantity'] <= 0:
                raise Failure('rejected', 'positive', scope, 'validation')
            value = item['price'] * item['quantity']
            if not MIN <= value <= MAX:
                raise Failure('error', 'overflow', scope + '.total', 'transform')
            item['total'] = value
        total = 0
        for item in order['items']:
            total += item['total']
            if not MIN <= total <= MAX:
                raise Failure('error', 'overflow', opath + '.items', 'transform')
        order['total'] = total
    total = 0
    for order in row['orders']:
        total += order['total']
        if not MIN <= total <= MAX:
            raise Failure('error', 'overflow', 'orders', 'transform')
    row['total'] = total
    return row


def signature(result):
    return result.index, result.status, result.value, tuple((e.code,e.path,e.stage) for e in result.errors)


class ReferenceProcessor(Processor):
    def transform(self, row):
        return reference(row)


class TestInvariants(unittest.TestCase):
    def fixtures(self):
        rng = random.Random(SEED)
        rows = []
        for i in range(120):
            rows.append({'id': i, 'orders': [
                {'items': [{'price': rng.randint(-10000, 10000), 'quantity': rng.randint(0, 5)}
                           for _ in range(rng.randrange(5))]}
                for _ in range(rng.randrange(4))]})
        rows += [
            {'orders': [{'items': [{'price': MAX, 'quantity': 2}]}]},
            {'orders': [{'items': [{'price': MAX, 'quantity': 1}, {'price': 1, 'quantity': 1}]}]},
            {'orders': [{'items': [{'price': 1, 'quantity': None}]}]},
            {'orders': [{'items': [{'price': True, 'quantity': 1}]}]},
            {'orders': [{'items': [{'quantity': 1}]}]},
            {'orders': []}]
        return rows

    def test_seeded_nested_scalar_batch_stream_replay(self):
        rows = self.fixtures()
        before = copy.deepcopy(rows)
        expected = []
        for i, row in enumerate(rows):
            try:
                expected.append((i, 'ok', reference(row), ()))
            except Failure as failure:
                status,code,path,stage = failure.details
                expected.append((i,status,None,((code,path,stage),)))
        for encode in (lambda r:r, json.dumps, lambda r:json.dumps(r).encode()):
            inputs = [encode(r) for r in rows]
            for mode in ('one','batch','stream','replay'):
                p = plan()
                if mode == 'one': results = [p.run_one(r) for r in inputs]
                elif mode == 'batch': results = p.run_batch(inputs)
                elif mode == 'replay':
                    a = [signature(r) for r in p.run_batch(inputs)]
                    results = p.run_batch(inputs)
                    self.assertEqual(a, [(r.index-len(rows),r.status,r.value,tuple((e.code,e.path,e.stage) for e in r.errors)) for r in results])
                    results = plan().run_batch(inputs)
                else: results = list(p.run_iter(iter(inputs),batch_size=7))
                with self.subTest(seed=SEED, encoding=encode,mode=mode):
                    self.assertEqual([signature(r) for r in results],expected)
        self.assertEqual(rows,before)

    def test_python_fallback_matches_independent_valid_values(self):
        rows=[]
        for row in self.fixtures():
            try: reference(row)
            except Failure: continue
            rows.append(row)
        expected=[reference(r) for r in rows]
        for size in (1,7,1000):
            runtime=Runtime(ReferenceProcessor(),Settings(batch_size=size))
            results=list(runtime.process_iter(json.dumps(r).encode() for r in rows))
            self.assertTrue(all(r.ok for r in results))
            self.assertEqual([r.value for r in results],expected)
            self.assertEqual([r.index for r in results],list(range(len(rows))))

    def test_generated_numeric_edges(self):
        values=[MIN,MIN+1,-2**53-1,-1,0,1,2**53+1,MAX,MAX+1,2**64-1]
        for operation in (operator.add,operator.sub,operator.mul,operator.gt,operator.ge):
            expr=operation(F('x'),F('y'))
            rows=[{'x':x,'y':y} for x in values for y in values]
            outcomes=Pipeline().derive('v',expr).run_batch(rows)
            for row,r in zip(rows,outcomes):
                with self.subTest(op=operation.__name__,row=row):
                    invalid=next((k for k in ('x','y') if not MIN<=row[k]<=MAX),None)
                    if invalid:
                        self.assertEqual((r.errors[0].code,r.errors[0].path),('invalid_type',invalid))
                        continue
                    value=operation(row['x'],row['y'])
                    if type(value) is int and not MIN<=value<=MAX:
                        self.assertEqual((r.errors[0].code,r.errors[0].path),('overflow','v'))
                    else:
                        self.assertTrue(r.ok)
                        self.assertEqual(r.value['v'],value)

    def test_generated_callback_batch_fallback_and_length(self):
        rows=[{'id':i,'orders':[]} for i in range(37)]
        class WrongBatch(ReferenceProcessor):
            def transform_batch(self,items): return []
            def transform(self,row):
                if row['id']%7==0: raise ValueError('private callback detail')
                return reference(row)
        for fallback in (True,False):
            runtime=Runtime(WrongBatch(),Settings(fallback_to_scalar=fallback))
            out=runtime.process_batch(rows)
            self.assertEqual([r.index for r in out],list(range(37)))
            self.assertEqual(runtime.metrics.batch_fallbacks,1)
            self.assertEqual([r.ok for r in out],[fallback and i%7!=0 for i in range(37)])
            self.assertTrue(all('private callback detail' not in repr(r) for r in out))
            self.assertEqual(runtime.metrics.processed,37)
