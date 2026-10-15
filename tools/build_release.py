"""Build public candidates from an explicit source allowlist, never from dist/."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    'pyproject.toml', 'setup.py', 'MANIFEST.in', 'README.md', 'README.zh-CN.md',
    'LICENSE', 'LICENSE-STATUS.md', 'CONTRIBUTING.md', 'SECURITY.md', 'AGENTS.md',
)
DOCS = (
    'decisions.md', 'platform-support.md', 'compatibility.md', 'external-models.md',
    'user-workflow.md', 'agent-delivery.md', 'quickstart.md', 'cli-workflow.zh-CN.md',
    'releases/v0.1.0a1.md', 'releases/v0.1.0a2.md', 'releases/v0.1.0a3.md',
    'images/review-comparison.png',
    'images/aerosense-feedback.png', 'images/aerosense-comparison.png',
    'images/aerosense-bottom-feedback.png',
    'images/square-enclosure-comparison.png', 'images/square-enclosure-feedback.png',
)
TREES = {
    'core/easy_to_3d': {'.py'}, 'viewer': {'.js', '.css', '.html'},
    'schemas': {'.json'}, 'skills/structural-design': {'.md'},
    'backend-examples/freecad': {'.py'}, 'backend-examples/blender': {'.py'},
    'integrations': {'.md'}, '.github': {'.yml', '.yaml'},
}


def public_sources(root):
    paths = {root / p for p in ROOT_FILES}
    paths.update(root / 'docs' / p for p in DOCS)
    paths.update(root / p for p in (
        'viewer/vendor/THREE-LICENSE', 'tools/build_release.py', 'tools/generate_schemas.py'))
    for directory, suffixes in TREES.items():
        for path in (root / directory).rglob('*'):
            if path.is_file() and path.suffix in suffixes and '__pycache__' not in path.parts:
                paths.add(path)
    for path in sorted(paths):
        if not path.is_file():
            raise ValueError(f'Missing public source: {path.relative_to(root)}')
        relative = path.relative_to(root)
        if any((root / Path(*relative.parts[:i])).is_symlink()
               for i in range(1, len(relative.parts) + 1)):
            raise ValueError(f'Symlinks are not release inputs: {relative}')
        yield path


def build(root, output):
    if output.exists():
        raise ValueError('Output already exists; choose a fresh directory.')
    version = re.search(r'^version\s*=\s*"([^"]+)"',
                        (root / 'pyproject.toml').read_text(), re.M).group(1)
    with tempfile.TemporaryDirectory(prefix='easy-to-3d-release-') as tmp:
        source = Path(tmp) / 'source'
        for path in public_sources(root):
            target = source / path.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        artifacts = Path(tmp) / 'artifacts'
        subprocess.run([sys.executable, '-m', 'build', '--no-isolation',
                        '--outdir', str(artifacts)], cwd=source, check=True)
        skill_zip = artifacts / f'easy-to-3d-structural-design-{version}.zip'
        with zipfile.ZipFile(skill_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted((source / 'skills/structural-design').rglob('*.md')):
                archive.write(path, path.relative_to(source / 'skills'))
            archive.write(source / 'LICENSE', 'structural-design/LICENSE')
        expected = {
            f'easy_to_3d-{version}-py3-none-any.whl',
            f'easy_to_3d-{version}.tar.gz', skill_zip.name,
        }
        if {p.name for p in artifacts.iterdir()} != expected:
            raise ValueError('Unexpected build output; candidate not copied.')
        manifest = {
            'version': version, 'kind': 'release candidate; publication not implied',
            'license': 'Apache-2.0', 'algorithm': 'sha256',
            'files': {name: hashlib.sha256((artifacts / name).read_bytes()).hexdigest()
                      for name in sorted(expected)},
        }
        (artifacts / 'checksums.json').write_text(json.dumps(manifest, indent=2) + '\n')
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(artifacts, output)
        return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/public-candidate')
    args = parser.parse_args()
    try:
        result = build(ROOT, args.output.resolve())
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
