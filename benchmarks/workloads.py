"""Equivalent bounded-domain workloads with independent Python calculations.

All decoded fixture rows satisfy schema/domain; only top-level business checks
and malformed JSON reject, so legacy/native errors are comparable. This does
not claim equivalence of arbitrary Python callbacks to the native language.
"""
import copy
import json
from pathlib import Path
import random
import sys
from redmud import Pipeline, Processor, Runtime, Settings, RecordResult, Error, Rule, field as F, list_sum

SEED = 20261107
MIN_I64, MAX_I64 = -2**63, 2**63-1
NAMES = ('arithmetic','nested_json','nested_sums','multiple_derives','validation_heavy','mixed_rejects')


def checked(value):
    if not MIN_I64 <= value <= MAX_I64:
        raise OverflowError('reference i64 range')
    return value


def domain(value,depth=1):
    if depth>64: return False
    if type(value) is int: return -2**63 <= value <= 2**64-1
    if value is None or type(value) in (bool,str): return True
    if type(value) is list:return all(domain(v,depth+1) for v in value)
    if type(value) is dict:return all(type(k) is str and domain(v,depth+1) for k,v in value.items())
    return False  # fixture domain intentionally has no floats or custom objects


def depth_ok(value,depth=1):
    if depth>64:return False
    if isinstance(value,dict):return all(depth_ok(v,depth+1) for v in value.values())
    if isinstance(value,list):return all(depth_ok(v,depth+1) for v in value)
    return True


def ints(row,keys):
    return all(type(row.get(k)) is int and MIN_I64 <= row[k] <= MAX_I64 for k in keys)


def schema_ok(name,row):
    if name in ('arithmetic','mixed_rejects'):
        return ints(row,('id','price','quantity')) and row['price']>=0 and 0<=row['quantity']<=10
    if name=='nested_json':
        return (ints(row,('id',)) and type(row.get('customer')) is dict
                and type(row['customer'].get('region')) is str and type(row['customer'].get('active')) is bool
                and type(row.get('payload')) is dict and ints(row['payload'],('score',))
                and type(row['payload'].get('tags')) is list and all(type(t) is str for t in row['payload']['tags']))
    if name=='nested_sums':
        return (ints(row,('id',)) and type(row.get('orders')) is list
                and all(type(o) is dict and type(o.get('items')) is list and all(
                    type(i) is dict and ints(i,('price','quantity')) and i['price']>=0 and 1<=i['quantity']<=10
                    for i in o['items']) for o in row['orders']))
    common=ints(row,('id','price','quantity','fee','discount')) and row['price']>=0 and 0<=row['quantity']<=10 and row['fee']>=0 and 0<=row['discount']<=100
    if name=='multiple_derives':return common
    return common and ints(row,('score',)) and 0<=row['score']<=1000 and row.get('status') in ('open','closed')


def transform(name,row):
    # Preserve inputs and checked intermediate order just as the native plan does.
    out=dict(row)
    if name=='nested_json':out['score']=checked(row['payload']['score']+1)
    elif name=='nested_sums':
        orders=[]
        for order in row['orders']:
            items=[dict(item,total=checked(item['price']*item['quantity'])) for item in order['items']]
            total=0
            for item in items:total=checked(total+item['total'])
            orders.append(dict(order,items=items,total=total))
        total=0
        for order in orders:total=checked(total+order['total'])
        out.update(orders=orders,total=total)
    elif name=='multiple_derives':
        out['subtotal']=checked(row['price']*row['quantity'])
        out['with_fee']=checked(out['subtotal']+row['fee'])
        out['double']=checked(out['with_fee']*2)
        out['net']=checked(out['double']-row['discount'])
        out['total']=checked(out['net']+out['subtotal'])
    else:
        out['total']=checked(row['price']*row['quantity'])
        if name=='validation_heavy':out['total']=checked(checked(out['total']+row['fee'])-row['discount'])
    assert depth_ok(out)
    return out


def checks(name):
    if name in ('arithmetic','mixed_rejects','multiple_derives','validation_heavy'):
        result=[('positive',lambda r:r['quantity']>0)]
        if name=='validation_heavy':
            result += [('price_nonnegative',lambda r:r['price']>=0),('fee_nonnegative',lambda r:r['fee']>=0),
                       ('discount_nonnegative',lambda r:r['discount']>=0),('score_nonnegative',lambda r:r['score']>=0)]
        return result
    return []


def native_plan(name,metrics=True):
    integer='int'
    basic={'id':integer,'price':{'type':'int','min':0},'quantity':{'type':'int','min':0,'max':10}}
    if name=='nested_json':
        schema={'id':integer,'customer':{'fields':{'region':'str','active':'bool'}},
                'payload':{'fields':{'score':integer,'tags':{'items':'str'}}}}
    elif name=='nested_sums':
        schema={'id':integer,'orders':{'items':{'fields':{'items':{'items':{'fields':{
            'price':{'type':'int','min':0},'quantity':{'type':'int','min':1,'max':10}}}}}}}}
    else:
        schema=dict(basic)
        if name in ('multiple_derives','validation_heavy'):
            schema.update(fee={'type':'int','min':0},discount={'type':'int','min':0,'max':100})
        if name=='validation_heavy':schema.update(score={'type':'int','min':0,'max':1000},status={'type':'str','allowed':['open','closed']})
    p=Pipeline(metrics=metrics).require(schema)
    if checks(name):p=p.check('positive',F('quantity')>0)
    if name=='validation_heavy':
        for key in ('price','fee','discount','score'):p=p.check(key+'_nonnegative',F(key)>=0)
    if name=='nested_json':p=p.derive('score',F('payload.score')+1)
    elif name=='nested_sums':
        item=Pipeline().derive('total',F('price')*F('quantity'))
        order=Pipeline().map_list('items',item).derive('total',list_sum('items','total'))
        p=p.map_list('orders',order).derive('total',list_sum('orders','total'))
    elif name=='multiple_derives':
        p=(p.derive('subtotal',F('price')*F('quantity')).derive('with_fee',F('subtotal')+F('fee'))
           .derive('double',F('with_fee')*2).derive('net',F('double')-F('discount')).derive('total',F('net')+F('subtotal')))
    elif name=='validation_heavy':p=p.derive('total',(F('price')*F('quantity')+F('fee'))-F('discount'))
    else:p=p.derive('total',F('price')*F('quantity'))
    return p


def rows(name,count,kind,seed=SEED):
    rng=random.Random(seed)
    for i in range(count):
        if name=='mixed_rejects' and i%11==0:
            yield b'{malformed'  # same positions in bytes and dict modes
            continue
        row={'id':i,'price':rng.randrange(10000),'quantity':1+i%9}
        if name=='mixed_rejects' and i%7==0:row['quantity']=0
        if name=='nested_json':row={'id':i,'customer':{'region':'EU','active':bool(i%2)},'payload':{'score':i%1000,'tags':['alpha','beta']}}
        elif name=='nested_sums':row={'id':i,'orders':[{'items':[{'price':rng.randrange(1000),'quantity':1+j%3} for j in range(4)]} for _ in range(1+i%3)]}
        elif name in ('multiple_derives','validation_heavy'):
            row.update(fee=i%20,discount=i%100)
            if name=='validation_heavy':row.update(score=i%1001,status='open' if i%2 else 'closed')
        assert domain(row) and schema_ok(name,row),'fixture outside comparable validation domain'
        yield json.dumps(row,separators=(',',':'),allow_nan=False).encode() if kind=='bytes' else row


class Plain:
    """Plain stdlib parsing/validation/math, using the same public result containers."""
    def __init__(self,name):self.name,self.index=name,0
    def run_batch(self,batch):
        out=[]
        for raw in batch:
            i=self.index;self.index+=1
            try:row=json.loads(raw) if isinstance(raw,(bytes,str)) else raw
            except (ValueError,UnicodeError):
                out.append(RecordResult(i,'error',errors=(Error('invalid_json','','parse','Invalid JSON'),)));continue
            assert domain(row) and schema_ok(self.name,row)
            for code,predicate in checks(self.name):
                if not predicate(row):
                    out.append(RecordResult(i,'rejected',errors=(Error(code,'','validation','Data quality check failed'),)));break
            else:out.append(RecordResult(i,'ok',value=transform(self.name,row)))
        return out


class Business(Processor):
    def __init__(self,name):self.name=name
    def input_rules(self):
        return [Rule('schema_valid',lambda r:domain(r) and schema_ok(self.name,r)),
                *(Rule(code,fn) for code,fn in checks(self.name))]
    def transform(self,row):return transform(self.name,row)


def engine(name,workload,batch_size,tcore_source=None):
    if name=='plain':return Plain(workload)
    if name in ('native','native_off'):return native_plan(workload,metrics=name!='native_off').prepare()
    if name=='runtime':return Runtime(Business(workload),Settings(batch_size=batch_size,timing_sample_every=0))
    if name=='tcore':
        source=Path(tcore_source).resolve()
        assert (source/'tcore'/'__init__.py').is_file(),'Missing original TCore source'
        sys.path.insert(0,str(source))
        import tcore
        class Legacy(tcore.Processor):
            def input_rules(self):
                return [tcore.Rule('schema_valid',lambda r:domain(r) and schema_ok(workload,r)),
                        *(tcore.Rule(code,fn) for code,fn in checks(workload))]
            def transform(self,row):return transform(workload,row)
        return tcore.Runtime(Legacy(),tcore.Settings(batch_size=batch_size,timing_sample_every=0))
    raise ValueError('Unknown engine')


def call(engine,batch):
    method=getattr(engine,'run_batch',None) or engine.process_batch
    return method(batch)


def signature(result):
    if hasattr(result,'errors'):errors=tuple((e.code,e.path,e.stage) for e in result.errors)
    elif result.error_stage:
        assert result.error_stage=='parse' and result.error_type in ('JSONDecodeError','UnicodeDecodeError')
        errors=(('invalid_json','','parse'),)
    else:errors=tuple((e.rule,'','validation') for e in result.issues if e.severity=='reject')
    return result.index,result.status,result.value,errors


def verify(workload,kind,count=64,tcore_source=None):
    sample=list(rows(workload,count,kind))
    before=copy.deepcopy(sample)
    expected=[signature(r) for r in Plain(workload).run_batch(sample)]
    names=['runtime','native','native_off']+(['tcore'] if tcore_source else [])
    for name in names:
        actual=[signature(r) for r in call(engine(name,workload,64,tcore_source),sample)]
        assert actual==expected,(workload,kind,name,'non-equivalent outcomes')
        assert sample==before,(name,'mutated fixture')
    return len(expected)
