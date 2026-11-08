"""Inspect built artifacts and dated scanner reports; no scanner is reimplemented."""
import email
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

folder = Path('target/security-wheels')
notice = Path('THIRD_PARTY_NOTICES.md').read_bytes()
wheel = next(folder.glob('*.whl'))
with zipfile.ZipFile(wheel) as z:
    notices = [n for n in z.namelist() if n.endswith('THIRD_PARTY_NOTICES.md')]
    assert len(notices) == 1
    assert z.read(notices[0]) == notice
    metadata = email.message_from_bytes(z.read(next(n for n in z.namelist() if n.endswith('/METADATA'))))
    assert not metadata.get_all('Requires-Dist')
    assert metadata['Name'] == 'redmud'
sdist = next(folder.glob('*.tar.gz'))
with tarfile.open(sdist) as t:
    notices = [n for n in t.getnames() if n.endswith('THIRD_PARTY_NOTICES.md')]
    assert len(notices) == 1
    assert t.extractfile(notices[0]).read() == notice
rust = json.loads(Path('docs/evidence/m1/security/rust-advisories.json').read_text())
assert not rust['vulnerabilities']['found'] and not rust['warnings']
assert rust['settings']['ignore'] == []
metadata = json.loads(Path('docs/evidence/m1/final-cargo-metadata.json').read_text())
assert next(p for p in metadata['packages'] if p['name'] == 'pyo3')['version'] == '0.29.3'
assert len(metadata['packages']) == rust['lockfile']['dependency-count']
info = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (wheel,sdist,Path('Cargo.lock'),Path('THIRD_PARTY_NOTICES.md'))}
Path('docs/evidence/m1/final-artifacts.json').write_text(json.dumps(info,indent=2)+'\n')
print('PASS: wheel/sdist notices match exact current text; wheel has no Python runtime dependencies.')
print('PASS: PyO3 0.29.3, exact lockfile/report package count, no Rust findings/warnings/ignores.')
print('RustSec database:',rust['database'])
print('Artifact hashes written to docs/evidence/m1/final-artifacts.json')
