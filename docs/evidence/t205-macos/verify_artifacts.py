"""Verify current product identity and independently installed package artifacts."""
import email
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

root = Path(__file__).resolve().parents[3]
evidence = Path(__file__).resolve().parent
before = json.loads((evidence / 'source-before.json').read_text())
mutable = {'TASKS.md', 'ROADMAP.md', 'EVIDENCE.md', 'docs/home-verification.ru.md'}
for name, digest in before.items():
    if name not in mutable:
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
product = [root / 'Cargo.lock', root / 'Cargo.toml', root / 'pyproject.toml']
for folder in ('python', 'crates'):
    product.extend(p for p in (root / folder).rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.so')
results = []
for version in ('3.11.15', '3.12.13', '3.13.3'):
    out = root / 'target/t205-macos-package' / f'Darwin-arm64-{version}'
    result = json.loads((out / 'result.json').read_text())
    wheels = list((out / 'wheel').glob('*.whl'))
    sdists = list((out / 'sdist').glob('*.tar.gz'))
    assert len(wheels) == len(sdists) == 1
    wheel, sdist = wheels[0], sdists[0]
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata = email.message_from_bytes(archive.read(next(n for n in names if n.endswith('/METADATA'))))
        assert not metadata.get_all('Requires-Dist')
        assert any(n.endswith('THIRD_PARTY_NOTICES.md') for n in names)
        for path in (root / 'python/redmud').glob('*'):
            if path.is_file() and path.suffix != '.so':
                assert archive.read('redmud/' + path.name) == path.read_bytes(), path
        native = next(n for n in names if n.startswith('redmud/_native') and n.endswith('.so'))
        binary = out / 'native-identity.so'
        binary.write_bytes(archive.read(native))
        arch = subprocess.check_output(['lipo', '-archs', str(binary)], text=True).strip()
        assert arch == 'arm64', arch
        binary.unlink()
    with tarfile.open(sdist) as archive:
        for path in product:
            member = 'redmud-0.2.0/' + str(path.relative_to(root))
            assert archive.extractfile(member).read() == path.read_bytes(), member
        assert archive.extractfile('redmud-0.2.0/THIRD_PARTY_NOTICES.md').read() == (root / 'THIRD_PARTY_NOTICES.md').read_bytes()
    result['native_architecture'] = arch
    result['sha256'] = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (wheel, sdist)}
    result['verified_current_product_bytes'] = True
    results.append(result)
(evidence / 'artifacts.json').write_text(json.dumps(results, indent=2)+'\n')
print('PASS: three local macOS Python versions, six independent installs recorded.')
print('PASS: wheel Python modules and sdist build inputs match current source; notices retained; no Requires-Dist; native Mach-O arm64.')
print('PASS: original source unchanged except explicitly allowed progress documentation.')
