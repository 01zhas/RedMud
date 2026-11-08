"""Read public upstream metadata before choosing pinned CI actions."""
import json
from pathlib import Path
from urllib.request import Request, urlopen

out=Path('docs/evidence/m2')
records=[]
for name in ('checkout','setup-python','upload-artifact'):
    base='https://api.github.com/repos/actions/'+name
    def get(path):
        with urlopen(Request(base+path,headers={'User-Agent':'RedMud-CI-audit','Accept':'application/vnd.github+json'}),timeout=30) as r:
            return json.load(r)
    release=get('/releases/latest')
    tag=release['tag_name']
    ref=get('/git/ref/tags/'+tag)
    obj=ref['object']
    while obj['type']=='tag':obj=get('/git/tags/'+obj['sha'])['object']
    assert obj['type']=='commit'
    sha=obj['sha']
    for file in ('LICENSE','action.yml'):
        url=f'https://raw.githubusercontent.com/actions/{name}/{sha}/{file}'
        with urlopen(Request(url,headers={'User-Agent':'RedMud-CI-audit'}),timeout=30) as r:body=r.read()
        (out/(name+'-'+file.replace('.','-')+'.txt')).write_bytes(body)
    license=get('/license')
    assert license['license']['spdx_id']=='MIT'
    records.append(dict(repository='actions/'+name,tag=tag,sha=sha,license='MIT',source=release['html_url']))
(out/'ci-action-pins.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
