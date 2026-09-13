"""Create an explicit allowlist handoff; credentials and caches never enter the archive."""
import hashlib
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'artifacts/open-relief-handoff.tar.gz'
paths = [ROOT / name for name in (
    'README.md', '.gitignore', 'HANDOFF.md', 'task.md', '.env.example', 'pyproject.toml',
    'requirements-local.lock.txt', 'requirements-gpu.txt', 'Dockerfile.gpu', 'frontend', 'src', 'tests', 'scripts',
    'configs', 'docs', 'reports', 'open-relief-data', 'refrences/hfid_hv1.csv',
    'artifacts/multimodal', 'artifacts/dataset', 'artifacts/demo-final',
    'artifacts/evaluation', 'artifacts/ablations', 'artifacts/timef',
    'artifacts/annotation-example.json', 'artifacts/annotations-final-pilot.jsonl', 'artifacts/annotations-final-pilot.manifest.json',
    'artifacts/annotations-training.jsonl', 'artifacts/annotations-training.manifest.json',
    'artifacts/nebius',
)]
paths.extend((ROOT / 'artifacts').glob('monthly-*.jsonl'))
paths.extend((ROOT / 'artifacts').glob('monthly-*.manifest.json'))
files = set()
for path in paths:
    candidates = path.rglob('*') if path.is_dir() else [path]
    for candidate in candidates:
        if not candidate.is_file() or candidate.is_symlink():
            continue
        relative = candidate.relative_to(ROOT)
        if any(part.startswith(('.venv', '.git', '.pytest_cache')) or part in ('__pycache__', 'node_modules', 'dist', '.vercel')
               or part.endswith('.egg-info') for part in relative.parts):
            continue
        if candidate.suffix == '.pyc' or (candidate.name.startswith('.env') and candidate.name != '.env.example'):
            continue
        if candidate.suffix == '.pt':
            # Checkpoints are delivered separately (HF mirror + SHA-256 in docs/SUBMISSION.md);
            # a 54.7MB binary doesn't belong in a code/docs handoff archive.
            continue
        files.add(candidate)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(OUTPUT, 'w:gz') as archive:
    for path in sorted(files):
        archive.add(path, arcname=Path('open-relief') / path.relative_to(ROOT), recursive=False)
with tarfile.open(OUTPUT) as archive:
    names = archive.getnames()
    assert not any(Path(name).name == '.env' or 'annotation-cache' in name for name in names)
with OUTPUT.open('rb') as handle:
    digest = hashlib.file_digest(handle, 'sha256').hexdigest()
OUTPUT.with_suffix(OUTPUT.suffix + '.sha256').write_text(digest + '  ' + OUTPUT.name + '\n')
print(f'{OUTPUT}: {len(files)} files; {OUTPUT.stat().st_size / 1e6:.1f} MB; SHA256 {digest}')
