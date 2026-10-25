"""Assemble the self-contained structural-design skill, stamp it, and ship it.

The skill published to a skill library must run without a separate install, so the
runtime (core/easy_to_3d), the offline viewer and the JSON schemas are copied into
the skill's scripts/ directory. Layout produced:

    <output>/structural-design/
    ├── SKILL.md
    ├── references/*.md
    └── scripts/
        ├── et3d.py
        ├── BUILD.json
        └── easy_to_3d/{*.py, web/, schemas/}

The bundle is a derived artifact, never a second source of truth: every file in it
is byte-identical to a file in this repository, and scripts/BUILD.json records the
version, the git commit and a SHA-256 per source file. That record is what makes
"is the published skill still in sync with the repository?" a mechanical question.

Modes:
  (default)  Build a fresh bundle plus the installable zip.
  --check    Compare an existing bundle against the current sources and report
             whether the skill library copy is stale, fresh or tampered with.
  --install  Copy the fresh bundle over a locally installed skill (previous copy
             is kept as a timestamped backup).

Nothing is read from dist/. A rebuild refuses to overwrite unless --force is given,
so a stale bundle can never be mistaken for a fresh build.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'structural-design'
BUNDLE = 'structural-design'
BUILD_FILE = 'BUILD.json'
TEXT_SUFFIXES = {'.md', '.py', '.json', '.js', '.css', '.html'}
VIEWER_SUFFIXES = {'.js', '.css', '.html'}
TRACKED_FOR_DIRTY = ('core', 'viewer', 'schemas', 'skills', 'tools', 'pyproject.toml', '.github')


def files(directory, suffixes):
    return sorted(p for p in directory.rglob('*')
                  if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts)


def bundle_files(target):
    """Every file the bundle should ship, with BUILD.json excluded from its own record."""
    return sorted(p for p in target.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.name != BUILD_FILE)


def payload_files(target):
    """Everything the archive must carry, including the build record itself."""
    return sorted(p for p in target.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts)


def relative(path):
    return path.relative_to(ROOT).as_posix()


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def table_map():
    """Source file -> path inside the bundle. The only place the layout is defined."""
    mapping = {SKILL / 'SKILL.md': 'SKILL.md'}
    for path in files(SKILL / 'references', {'.md'}):
        mapping[path] = 'references/' + path.name
    for path in files(SKILL / 'scripts', {'.py'}):
        mapping[path] = 'scripts/' + path.name
    for path in files(ROOT / 'core' / 'easy_to_3d', {'.py'}):
        mapping[path] = 'scripts/easy_to_3d/' + path.name
    for path in files(ROOT / 'viewer', VIEWER_SUFFIXES):
        mapping[path] = 'scripts/easy_to_3d/web/' + path.relative_to(ROOT / 'viewer').as_posix()
    mapping[ROOT / 'viewer' / 'vendor' / 'THREE-LICENSE'] = 'scripts/easy_to_3d/web/vendor/THREE-LICENSE'
    for path in files(ROOT / 'schemas', {'.json'}):
        mapping[path] = 'scripts/easy_to_3d/schemas/' + path.name
    for path in mapping:
        if not path.is_file():
            raise ValueError('Missing source file for the bundle: ' + str(path))
    return mapping


def declared_version():
    text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    found = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return found.group(1) if found else None


def runtime_version():
    text = (ROOT / 'core' / 'easy_to_3d' / '__init__.py').read_text(encoding='utf-8')
    found = re.search(r'(?m)^__version__\s*=\s*"([^"]+)"', text)
    return found.group(1) if found else None


def git(*args):
    try:
        result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def source_provenance():
    """Enough identity for anyone holding the bundle to name the code it came from."""
    dirty = git('status', '--porcelain', '--', *TRACKED_FOR_DIRTY) or ''
    dirty_paths = sorted({line[3:].strip() for line in dirty.splitlines() if line.strip()})
    commit = git('rev-parse', 'HEAD')
    tag = git('describe', '--tags', '--exact-match', 'HEAD') if commit else None
    remote = git('remote', 'get-url', 'origin') or ''
    slug = re.sub(r'\.git$', '', re.sub(r'^.*[:/]([^/]+/[^/]+)$', r'\1', remote)) if remote else None
    return {
        'repository': 'https://github.com/' + slug if slug else None,
        'commit': commit,
        'tag': tag,
        'branch': git('rev-parse', '--abbrev-ref', 'HEAD'),
        'dirty': bool(dirty_paths),
        'dirty_paths': dirty_paths,
    }


def bundle_record(mapping):
    sources = {relative(path): sha256(path) for path in mapping}
    bundled = {mapping[path]: sources[relative(path)] for path in mapping}
    fingerprint = hashlib.sha256(
        '\n'.join(f'{name} {sources[name]}' for name in sorted(sources)).encode()).hexdigest()
    total = sum(path.stat().st_size for path in mapping)
    return {
        'skill': BUNDLE,
        'runtime': {'package': 'easy-to-3d', 'version': runtime_version()},
        'source': source_provenance(),
        'built_at': datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        'builder': 'tools/build_skill.py',
        'counts': {'source_files': len(mapping), 'files': len(mapping) + 1,
                   'uncompressed_bytes': total},
        'fingerprint': fingerprint,
        'sources': sources,
        'bundle': bundled,
    }


def build(output, force=False):
    declared, runtime = declared_version(), runtime_version()
    if not declared or not runtime:
        raise ValueError('Cannot read the version from pyproject.toml or core/easy_to_3d/__init__.py')
    if declared != runtime:
        raise ValueError(f'Version drift: pyproject.toml says {declared}, '
                         f'core/easy_to_3d/__init__.py says {runtime}')
    target = output / BUNDLE
    if target.exists():
        if not force:
            raise ValueError('Output already exists; pass --force to rebuild: ' + str(target))
        shutil.rmtree(target)
    mapping = table_map()
    record = bundle_record(mapping)
    for source, destination in mapping.items():
        path = target / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, path)
    (target / 'scripts' / BUILD_FILE).write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return target, record


def verify(target, record):
    """Refuse to ship a bundle that cannot be imported, that leaks local paths, or
    whose stamped hashes disagree with the bytes on disk."""
    skill_md = (target / 'SKILL.md').read_text(encoding='utf-8')
    if not skill_md.startswith('---') or 'name:' not in skill_md or 'description:' not in skill_md:
        raise ValueError('SKILL.md frontmatter is incomplete')
    if 'scripts/et3d.py' not in skill_md:
        raise ValueError('SKILL.md does not tell the Agent how to start the bundled runtime')
    if BUILD_FILE not in skill_md:
        raise ValueError('SKILL.md does not tell the reader where the build record lives')
    leaks = []
    for path in files(target, TEXT_SUFFIXES):
        text = path.read_text(encoding='utf-8', errors='replace')
        for needle in (str(ROOT), '/Users/', 'C:\\Users\\'):
            if needle in text:
                leaks.append((str(path.relative_to(target)), needle))
    if leaks:
        raise ValueError('Local absolute paths must not ship: ' + repr(leaks[:5]))
    shipped = {str(path.relative_to(target)): sha256(path) for path in bundle_files(target)}
    stamped = record['bundle']
    if shipped != stamped:
        missing = sorted(set(stamped) - set(shipped))
        extra = sorted(set(shipped) - set(stamped))
        differing = sorted(k for k in set(shipped) & set(stamped) if shipped[k] != stamped[k])
        raise ValueError('Bundle contents disagree with BUILD.json: '
                         + repr({'missing': missing[:5], 'extra': extra[:5], 'differing': differing[:5]}))
    probe = ('import sys,json;from easy_to_3d.project import Project;'
             'from easy_to_3d.server import WEB;'
             'import easy_to_3d;'
             'print(json.dumps({"web":WEB.is_dir(),'
             '"glb":hasattr(__import__("easy_to_3d.glb",fromlist=["x"]),"write_glb"),'
             '"version":easy_to_3d.__version__}))')
    result = subprocess.run([sys.executable, '-c', probe], capture_output=True, text=True,
                            cwd=target / 'scripts',
                            env=dict(os.environ, PYTHONPATH=str(target / 'scripts'), PYTHONDONTWRITEBYTECODE='1'))
    if result.returncode != 0:
        raise ValueError('Bundled runtime does not import: ' + result.stderr.strip()[:400])
    state = json.loads(result.stdout)
    if not state['web'] or not state['glb']:
        raise ValueError('Bundled viewer or GLB writer is missing: ' + repr(state))
    if state['version'] != record['runtime']['version']:
        raise ValueError(f'Stamp says {record["runtime"]["version"]}, runtime reports {state["version"]}')
    return len(bundle_files(target)) + 1


def check(output):
    """Is the bundle that someone already has still what this repository builds now?"""
    target = output / BUNDLE
    record_path = target / 'scripts' / BUILD_FILE
    if not record_path.is_file():
        return {'state': 'missing', 'bundle': str(target),
                'detail': 'No scripts/' + BUILD_FILE + '; this copy predates build stamping '
                          'or was not produced by tools/build_skill.py.'}
    record = json.loads(record_path.read_text(encoding='utf-8'))
    current = {relative(path): sha256(path) for path in table_map()}
    recorded = record.get('sources', {})
    added = sorted(set(current) - set(recorded))
    removed = sorted(set(recorded) - set(current))
    changed = sorted(k for k in set(current) & set(recorded) if current[k] != recorded[k])
    shipped = {str(path.relative_to(target)): sha256(path) for path in bundle_files(target)}
    stamped = record.get('bundle', {})
    tampered = sorted(k for k in set(shipped) & set(stamped) if shipped[k] != stamped[k])
    unlisted = sorted(set(shipped) - set(stamped))
    absent = sorted(set(stamped) - set(shipped))
    if added or removed or changed:
        state = 'stale'
    elif tampered or unlisted or absent:
        state = 'tampered'
    else:
        state = 'fresh'
    result = {
        'state': state,
        'bundle': str(target),
        'bundled_version': record.get('runtime', {}).get('version'),
        'bundled_commit': (record.get('source') or {}).get('commit'),
        'bundled_dirty': (record.get('source') or {}).get('dirty'),
        'built_at': record.get('built_at'),
        'repository_version': runtime_version(),
        'source_drift': {'added': added, 'removed': removed, 'changed': changed},
        'bundle_integrity': {'tampered': tampered, 'unlisted': unlisted, 'absent': absent},
    }
    if state == 'fresh':
        result['detail'] = 'Bundle matches the working tree.'
    elif state == 'stale':
        result['detail'] = ('The repository has moved since this bundle was built; '
                            'rebuild and publish a new skill version.')
    else:
        result['detail'] = 'Bundle files no longer match their own BUILD.json; do not trust this copy.'
    return result


def install(target, skills_root):
    """Replace a locally installed copy so the local Agent uses the same bytes."""
    skills_root = skills_root.expanduser().resolve()
    if not skills_root.is_dir():
        raise ValueError('Skills directory does not exist: ' + str(skills_root))
    destination = skills_root / BUNDLE
    if destination.exists():
        backup = skills_root / (BUNDLE + '.bak-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        shutil.move(str(destination), str(backup))
    else:
        backup = None
    shutil.copytree(target, destination)
    return {'installed': str(destination), 'backup': str(backup) if backup else None}


def zip_skill(target, output):
    archive = output.parent / (target.name + '.zip')
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in payload_files(target):
            bundle.write(path, path.relative_to(target.parent))
    verify_archive(archive, target)
    return archive


def verify_archive(archive, target):
    """The directory can be right while the archive is wrong; check what ships."""
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
    expected = {str(path.relative_to(target.parent)).replace(os.sep, '/')
                for path in payload_files(target)}
    missing = sorted(expected - set(names))
    if missing:
        raise ValueError('Archive is missing files that the bundle has: ' + repr(missing[:5]))
    stamp = f'{target.name}/scripts/{BUILD_FILE}'
    if stamp not in names:
        raise ValueError('Archive must carry the build record at ' + stamp)
    if len(names) != len(expected):
        raise ValueError(f'Archive has {len(names)} entries, bundle has {len(expected)}')


def release_notes(record, archive, output):
    """A paste-ready card for the skill library's upload form."""
    source = record['source']
    origin = source.get('tag') or (source['commit'][:7] if source.get('commit') else 'unknown')
    state = 'clean' if not source['dirty'] else 'dirty working tree'
    try:
        shown = output.relative_to(ROOT).as_posix()
    except ValueError:
        shown = str(output)
    lines = [
        f"# {BUNDLE} · {record['runtime']['version']}",
        '',
        f"- Bundle: `{archive.name}` ({archive.stat().st_size // 1024} KB, "
        f"{record['counts']['files']} files)",
        f"- Source: {source.get('repository') or 'local'} @ {origin} ({state}, branch {source.get('branch')})",
        f"- Built: {record['built_at']}",
        f"- Fingerprint: `{record['fingerprint'][:16]}`",
        '',
    ]
    if source['dirty']:
        lines += [
            '> Built from uncommitted changes. Commit, tag, and rebuild before uploading, or the',
            '> published skill will claim a commit that does not contain its own code.',
            '',
        ]
    lines += [
        '## Verify before uploading',
        '',
        '```',
        f'python3 tools/build_skill.py --check --output {shown}',
        '```',
        'Expect `"state": "fresh"`. A `stale` result means the repository moved after the build.',
        '',
        '## After the skill is live',
        '',
        'Anyone holding the installed skill can confirm which code it runs:',
        '',
        '```',
        'python3 <skill>/scripts/et3d.py --bundle-info',
        '```',
        '',
        'It prints the same version, commit and fingerprint recorded here.',
    ]
    recent = git('log', '-6', '--oneline', '--no-decorate')
    if recent:
        lines += ['', '## Recent commits', '', '```', recent, '```']
    text = '\n'.join(lines) + '\n'
    archive.parent.joinpath(BUNDLE + '-release.md').write_text(text, encoding='utf-8')
    return archive.parent / (BUNDLE + '-release.md')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', required=True,
                        help='Directory that holds (or will hold) structural-design/')
    parser.add_argument('--force', action='store_true', help='Rebuild over an existing bundle')
    parser.add_argument('--check', action='store_true',
                        help='Report whether an existing bundle is fresh, stale or tampered')
    parser.add_argument('--install', metavar='SKILLS_DIR',
                        help='Copy the fresh bundle into this skills directory, keeping a backup')
    parser.add_argument('--notes', action='store_true',
                        help='Write <bundle>-release.md next to the zip')
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve()

    if args.check:
        verdict = check(output)
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 0 if verdict['state'] == 'fresh' else 1

    target, record = build(output, force=args.force)
    count = verify(target, record)
    archive = zip_skill(target, output)
    summary = {
        'skill': str(target),
        'zip': str(archive),
        'version': record['runtime']['version'],
        'commit': record['source']['commit'],
        'tag': record['source']['tag'],
        'dirty': record['source']['dirty'],
        'files': count,
        'uncompressed_bytes': record['counts']['uncompressed_bytes'],
        'zip_bytes': archive.stat().st_size,
        'fingerprint': record['fingerprint'],
        'runtime': 'bundled',
        'install_required': False,
    }
    if args.notes:
        summary['notes'] = str(release_notes(record, archive, output))
    if args.install:
        summary['local_install'] = install(target, Path(args.install))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
