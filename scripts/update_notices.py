"""Copy exact cached upstream legal texts for the locked Cargo graph.

This is notice maintenance, not a legal-policy or vulnerability scanner.
Run cargo fetch/build first. --check never changes the notices or inventory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
parser.add_argument('--inventory', type=Path)
args = parser.parse_args()
metadata = json.loads(subprocess.check_output(
    ['cargo', 'metadata', '--locked', '--offline', '--format-version', '1'], text=True))
records = []
sections = ['# Third-party notices\n\nGenerated from the exact Cargo.lock graph; includes build-only and target-specific\npackages conservatively. License expressions are upstream metadata; original\nlicense texts below are retained verbatim. These notices do not change RedMud\nMIT licensing or replace the upstream terms.\n']
for package in sorted(metadata['packages'], key=lambda p: (p['name'], p['version'])):
    if not package['source']:
        continue
    folder = Path(package['manifest_path']).parent
    legal = sorted(p for p in folder.iterdir() if p.is_file() and any(
        name in p.name.upper() for name in ('LICENSE', 'LICENCE', 'COPYRIGHT', 'NOTICE')))
    if not legal or not package['license']:
        raise SystemExit(f'Missing upstream legal metadata/texts: {package["name"]}')
    records.append(dict(name=package['name'], version=package['version'],
                        license_expression=package['license'], source=package['source'],
                        files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in legal}))
    sections.append(f'\n## {package["name"]} {package["version"]}\n\nDeclared: `{package["license"]}`\n')
    for path in legal:
        sections.append('\n### ' + path.name + '\n\n```text\n' + path.read_text().rstrip() + '\n```\n')
notices = Path('THIRD_PARTY_NOTICES.md')
content = ''.join(sections)
inventory = json.dumps(records, indent=2) + '\n'
if args.check:
    assert notices.read_text() == content, 'Notices differ from locked upstream files'
    if args.inventory:
        assert args.inventory.read_text() == inventory, 'License inventory is stale'
else:
    notices.write_text(content)
    if args.inventory:
        args.inventory.parent.mkdir(parents=True, exist_ok=True)
        args.inventory.write_text(inventory)
print(f'PASS: {len(records)} external locked packages, copied legal texts and inventory verified.')
