"""Assemble the self-contained structural-design skill, stamp it, and ship it.

The skill published to a skill library must run without a separate install, so the
runtime (core/easy_to_3d), the offline viewer and the JSON schemas travel with the
skill. A skill library may cap how deeply a package may nest directories, so the
runtime ships as one archive that the launcher unpacks on first use. Layout:

    <output>/structural-design/
    ├── SKILL.md
    ├── references/*.md
    └── scripts/
        ├── et3d.py
        ├── BUILD.json
        └── easy_to_3d.zip        <- the runtime, viewer and schemas

Every shipped path is at most two levels below the skill root. verify() enforces
that, so a later change cannot quietly reintroduce deep nesting.

The bundle is a derived artifact, never a second source of truth: every byte in it
comes from a file in this repository, and scripts/BUILD.json records the version,
the git commit and a SHA-256 per source file, per shipped file and per archive
member. That record is what makes "is the published skill still in sync with the
repository?" a mechanical question.

Modes:
  (default)  Build a fresh bundle plus the installable zip.
  --check    Compare an existing bundle against the current sources and report
             whether the skill library copy is stale, fresh or tampered with.
  --install  Copy the fresh bundle over a locally installed skill (previous copy
             is kept as a backup outside the skills directory).

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
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'structural-design'
BUNDLE = 'structural-design'
BUILD_FILE = 'BUILD.json'
RUNTIME_DIR = 'scripts/easy_to_3d/'
RUNTIME_ARCHIVE = 'scripts/easy_to_3d.zip'
RUNTIME_PREFIX = 'easy_to_3d/'
MAX_DEPTH = 2
# A fixed timestamp makes the runtime archive reproducible: two builds of the same
# sources produce the same bytes, so a changed hash always means changed code.
ARCHIVE_EPOCH = (2020, 1, 1, 0, 0, 0)
TEXT_SUFFIXES = {'.md', '.py', '.json', '.js', '.css', '.html'}
VIEWER_SUFFIXES = {'.js', '.css', '.html'}
TRACKED_FOR_DIRTY = ('core', 'viewer', 'schemas', 'skills', 'tools', 'pyproject.toml', '.github')
# Fields the skill library's upload parser requires; a missing one is rejected before review.
MARKET_FIELDS = ('name', 'display_name', 'display_name_en', 'description',
                 'description_zh', 'description_en', 'version', 'author')
CATEGORIES = ('3D 建模与打印', '设计工具', '工程计算')


def frontmatter(text):
    """Top-level keys of a SKILL.md header, without pulling in a YAML dependency."""
    if not text.startswith('---'):
        return {}
    end = text.find('\n---', 3)
    if end == -1:
        return {}
    data, key = {}, None
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line[0] not in ' \t' and ':' in line and not line.startswith('-'):
            key, _, value = line.partition(':')
            key, value = key.strip(), value.strip()
            data[key] = [] if not value else value
        elif key and line.lstrip().startswith('-'):
            if not isinstance(data.get(key), list):
                data[key] = []
            item = line.lstrip()[1:].strip()
            data[key].append(item[1:-1] if len(item) > 1 and item[0] == item[-1] and item[0] in '"\'' else item)
    return data


def verify_frontmatter(text, version):
    """Catch what the upload form would reject, before the form does."""
    data = frontmatter(text)
    missing = [key for key in MARKET_FIELDS if not data.get(key)]
    if missing:
        raise ValueError('SKILL.md frontmatter is missing required market fields: ' + repr(missing))
    if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', str(data['name'])):
        raise ValueError('name must be lowercase letters, digits and single hyphens: ' + repr(data['name']))
    if str(data['version']) != version:
        raise ValueError(f'SKILL.md declares version {data["version"]}, the runtime is {version}; '
                         'the market listing would disagree with --bundle-info')
    if not data.get('examples_zh'):
        raise ValueError('SKILL.md needs examples_zh: the detail page shows Chinese examples, '
                         'and reviewers tend to run them as the acceptance test')
    for key, value in data.items():
        for item in (value if isinstance(value, list) else [value]):
            item = str(item)
            if ': ' in item or item[:1] in ('#', '-', '?', '!', '&', '*', '|', '>', '@', '`', '"', "'"):
                raise ValueError(f'frontmatter {key} would not survive YAML parsing; quote and reword it: '
                                 + repr(item[:70]))
    return data



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


def bundle_record(mapping, sources, bundle, archive_digest, member_count):
    """The stamp. Three views of one build, each answering a different question.

    sources         repository path -> digest: has the repository moved on?
    bundle          path inside the skill -> digest: what content shipped?
    files           path on disk inside the skill -> digest: was it altered after
                    the build? The runtime archive appears here as one entry, and
                    runtime_archive.members digs inside it when that entry disagrees.
    """
    files = {path: digest for path, digest in bundle.items()
             if not path.startswith(RUNTIME_DIR)}
    files[RUNTIME_ARCHIVE] = archive_digest
    fingerprint = hashlib.sha256(
        '\n'.join(f'{name} {sources[name]}' for name in sorted(sources)).encode()).hexdigest()
    total = sum(path.stat().st_size for path in mapping)
    return {
        'skill': BUNDLE,
        'runtime': {'package': 'easy-to-3d', 'version': runtime_version()},
        'source': source_provenance(),
        'built_at': datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        'builder': 'tools/build_skill.py',
        'layout': {'skill_md': 'SKILL.md', 'launcher': 'scripts/et3d.py',
                   'runtime': RUNTIME_ARCHIVE, 'max_depth': MAX_DEPTH},
        'counts': {'source_files': len(sources), 'runtime_members': member_count,
                   'entries': len(files) + 1, 'uncompressed_bytes': total},
        'fingerprint': fingerprint,
        'sources': sources,
        'bundle': bundle,
        'files': files,
        'runtime_archive': {'path': RUNTIME_ARCHIVE, 'sha256': archive_digest,
                            'members': runtime_members(bundle)},
    }


def runtime_members(bundle):
    """Zip member name -> digest, keyed exactly as the archive stores them."""
    return {RUNTIME_PREFIX + path[len(RUNTIME_DIR):]: digest
            for path, digest in bundle.items() if path.startswith(RUNTIME_DIR)}


def write_runtime_archive(path, mapping):
    """One zip instead of a directory tree: keeps every shipped path shallow.

    Timestamps are fixed so identical sources produce identical bytes; a changed
    hash then always means changed code, never a changed checkout time.
    """
    members = {destination[len(RUNTIME_DIR):]: source
               for source, destination in mapping.items()
               if destination.startswith(RUNTIME_DIR)}
    if not members:
        raise ValueError('The runtime has no files to archive: ' + RUNTIME_DIR)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(RUNTIME_PREFIX + name, date_time=ARCHIVE_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, members[name].read_bytes())
    return len(members)


def archive_members(path):
    with zipfile.ZipFile(path) as archive:
        return {info.filename: hashlib.sha256(archive.read(info.filename)).hexdigest()
                for info in archive.infolist() if not info.is_dir()}


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
    sources = {relative(path): sha256(path) for path in mapping}
    bundle = {mapping[path]: sources[relative(path)] for path in mapping}
    for source, destination in mapping.items():
        if destination.startswith(RUNTIME_DIR):
            continue
        path = target / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, path)
    member_count = write_runtime_archive(target / RUNTIME_ARCHIVE, mapping)
    record = bundle_record(mapping, sources, bundle, sha256(target / RUNTIME_ARCHIVE), member_count)
    (target / 'scripts' / BUILD_FILE).write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return target, record


def depth_of(relative_path):
    return relative_path.replace(os.sep, '/').count('/')


def verify_depth(target):
    """Every shipped path sits at most MAX_DEPTH levels below the skill root.

    A skill library may cap nesting, and a package that nests deeper can be
    rejected on upload. Checked here so a later addition cannot break it silently.
    """
    deep = sorted(str(path.relative_to(target)) for path in payload_files(target)
                  if depth_of(str(path.relative_to(target))) > MAX_DEPTH)
    if deep:
        raise ValueError(f'Shipped paths must stay within {MAX_DEPTH} levels of the skill root; '
                         + 'these are deeper: ' + repr(deep[:5]))


def verify(target, record):
    """Refuse to ship a bundle that cannot be imported, that leaks local paths, or
    whose stamped hashes disagree with the bytes on disk."""
    skill_md = (target / 'SKILL.md').read_text(encoding='utf-8')
    listing = verify_frontmatter(skill_md, record['runtime']['version'])
    if 'scripts/et3d.py' not in skill_md:
        raise ValueError('SKILL.md does not tell the Agent how to start the bundled runtime')
    if BUILD_FILE not in skill_md:
        raise ValueError('SKILL.md does not tell the reader where the build record lives')
    if not (target / RUNTIME_ARCHIVE).is_file():
        raise ValueError('The bundled runtime archive is missing: ' + RUNTIME_ARCHIVE)
    verify_depth(target)
    leaks = []
    checked = [(str(path.relative_to(target)), path.read_text(encoding='utf-8', errors='replace'))
               for path in files(target, TEXT_SUFFIXES)]
    with zipfile.ZipFile(target / RUNTIME_ARCHIVE) as archive:
        for info in archive.infolist():
            if Path(info.filename).suffix in TEXT_SUFFIXES and not info.is_dir():
                checked.append((RUNTIME_ARCHIVE + '!' + info.filename,
                                archive.read(info.filename).decode('utf-8', 'replace')))
    for name, text in checked:
        for needle in (str(ROOT), '/Users/', 'C:\\Users\\'):
            if needle in text:
                leaks.append((name, needle))
    if leaks:
        raise ValueError('Local absolute paths must not ship: ' + repr(leaks[:5]))
    shipped = {str(path.relative_to(target)): sha256(path) for path in bundle_files(target)}
    stamped = record['files']
    if shipped != stamped:
        missing = sorted(set(stamped) - set(shipped))
        extra = sorted(set(shipped) - set(stamped))
        differing = sorted(k for k in set(shipped) & set(stamped) if shipped[k] != stamped[k])
        raise ValueError('Bundle contents disagree with BUILD.json: '
                         + repr({'missing': missing[:5], 'extra': extra[:5], 'differing': differing[:5]}))
    if archive_members(target / RUNTIME_ARCHIVE) != record['runtime_archive']['members']:
        raise ValueError('The runtime archive does not match the members recorded in BUILD.json')
    # Run the launcher the way a user would: unpack, import, find the viewer.
    with tempfile.TemporaryDirectory(prefix='et3d-verify-') as cache:
        result = subprocess.run([sys.executable, str(target / 'scripts' / 'et3d.py'), '--self-check'],
                                capture_output=True, text=True, cwd=str(target),
                                env=dict(os.environ, EASY_TO_3D_CACHE=cache,
                                         PYTHONDONTWRITEBYTECODE='1'))
    if result.returncode != 0:
        raise ValueError('Bundled runtime does not start: '
                         + (result.stderr.strip() or result.stdout.strip())[:400])
    state = json.loads(result.stdout)
    if not state['web_present']:
        raise ValueError('Bundled viewer is missing after unpacking the runtime archive: ' + repr(state))
    if state['version'] != record['runtime']['version']:
        raise ValueError(f'Stamp says {record["runtime"]["version"]}, runtime reports {state["version"]}')
    return record['counts']['source_files'], listing


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
    packed = 'files' in record and (target / RUNTIME_ARCHIVE).is_file()
    shipped = {str(path.relative_to(target)): sha256(path) for path in bundle_files(target)}
    # A pre-archive bundle listed the runtime file by file; a packed one lists the
    # archive as a single entry. Compare against whichever this copy was built with.
    stamped = record['files'] if packed else record.get('bundle', {})
    tampered = sorted(k for k in set(shipped) & set(stamped) if shipped[k] != stamped[k])
    unlisted = sorted(set(shipped) - set(stamped))
    absent = sorted(set(stamped) - set(shipped))
    inside = {'readable': True, 'tampered': [], 'unlisted': [], 'absent': []}
    if packed:
        try:
            members = archive_members(target / RUNTIME_ARCHIVE)
        except (OSError, zipfile.BadZipFile):
            inside['readable'] = False
        else:
            wanted = record['runtime_archive']['members']
            inside['tampered'] = sorted(k for k in set(members) & set(wanted)
                                        if members[k] != wanted[k])
            inside['unlisted'] = sorted(set(members) - set(wanted))
            inside['absent'] = sorted(set(wanted) - set(members))
    if added or removed or changed:
        state = 'stale'
    elif tampered or unlisted or absent or not inside['readable'] or any(
            inside[key] for key in ('tampered', 'unlisted', 'absent')):
        state = 'tampered'
    else:
        state = 'fresh'
    result = {
        'state': state,
        'bundle': str(target),
        'bundle_layout': 'archive' if packed else 'unpacked',
        'bundled_version': record.get('runtime', {}).get('version'),
        'bundled_commit': (record.get('source') or {}).get('commit'),
        'bundled_dirty': (record.get('source') or {}).get('dirty'),
        'built_at': record.get('built_at'),
        'repository_version': runtime_version(),
        'source_drift': {'added': added, 'removed': removed, 'changed': changed},
        'bundle_integrity': {'tampered': tampered, 'unlisted': unlisted, 'absent': absent},
    }
    if packed:
        result['runtime_integrity'] = inside
    if state == 'fresh':
        result['detail'] = 'Bundle matches the working tree.'
    elif state == 'stale':
        result['detail'] = ('The repository has moved since this bundle was built; '
                            'rebuild and publish a new skill version.')
    else:
        result['detail'] = 'Bundle files no longer match their own BUILD.json; do not trust this copy.'
    return result


def install(target, skills_root):
    """Replace a locally installed copy so the local Agent uses the same bytes.

    The replaced copy is moved to a sibling directory, never into the skills
    directory itself: every directory that holds a SKILL.md is discovered as a
    skill, so a backup named structural-design.bak-* would load as another copy
    of the same skill and show up as duplicates in the client's skill list.
    """
    skills_root = skills_root.expanduser().resolve()
    if not skills_root.is_dir():
        raise ValueError('Skills directory does not exist: ' + str(skills_root))
    destination = skills_root / BUNDLE
    if destination.exists():
        vault = skills_root.parent / (skills_root.name + '-backups')
        if not vault.is_dir():
            vault.mkdir(parents=True)
        backup = vault / (BUNDLE + '.bak-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        shutil.move(str(destination), str(backup))
    else:
        backup = None
    shutil.copytree(target, destination)
    return {'installed': str(destination), 'backup': str(backup) if backup else None}


def zip_skill(target, output):
    archive = output.parent / (target.name + '.zip')
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, 'w') as bundle:
        for path in payload_files(target):
            # Storing an already-compressed archive beats deflating it twice.
            method = zipfile.ZIP_STORED if path.suffix == '.zip' else zipfile.ZIP_DEFLATED
            bundle.write(path, path.relative_to(target.parent), compress_type=method)
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
    runtime = f'{target.name}/{RUNTIME_ARCHIVE}'
    if runtime not in names:
        raise ValueError('Archive must carry the bundled runtime at ' + runtime)
    if len(names) != len(expected):
        raise ValueError(f'Archive has {len(names)} entries, bundle has {len(expected)}')
    deep = sorted(name for name in names if name.count('/') > MAX_DEPTH)
    if deep:
        raise ValueError(f'Archive entries must stay within {MAX_DEPTH} levels of the skill root; '
                         + 'these are deeper: ' + repr(deep[:5]))


def release_notes(record, archive, output, listing):
    """A paste-ready upload card: identity, form fields, review answers, checks."""
    source = record['source']
    origin = source.get('tag') or (source['commit'][:7] if source.get('commit') else 'unknown')
    state = 'clean' if not source['dirty'] else 'dirty working tree'
    try:
        shown = output.relative_to(ROOT).as_posix()
    except ValueError:
        shown = str(output)
    lines = [
        f"# {listing['display_name']} · {record['runtime']['version']}",
        '',
        f"- 包体：`{archive.name}`（{archive.stat().st_size // 1024} KB，"
        f"{record['counts']['entries']} 个条目承载 {record['counts']['source_files']} 个文件；"
        f"运行时压成 `scripts/easy_to_3d.zip`，包内路径最深 {record['layout']['max_depth']} 层）",
        f"- 源码：{source.get('repository') or 'local'} @ {origin}（{state}，分支 {source.get('branch')}）",
        f"- 构建：{record['built_at']}",
        f"- 指纹：`{record['fingerprint'][:16]}`",
        '',
    ]
    if source['dirty']:
        lines += [
            '> 这个包是从未提交的改动构建的。先提交、打 tag、重建再上传，',
            '> 否则上架的技能会声称属于一个并不包含它代码的 commit。',
            '',
        ]
    lines += [
        '## 表单字段（直接复制）',
        '',
        f"- 标识 name：`{listing['name']}`",
        f"- 中文展示名：{listing['display_name']}",
        f"- 英文展示名：{listing['display_name_en']}",
        f"- 版本：`{listing['version']}`",
        f"- 作者：{listing['author']}",
        '',
        '中文简介：',
        '',
        '```text',
        str(listing['description_zh']),
        '```',
        '',
        '英文简介：',
        '',
        '```text',
        str(listing['description_en']),
        '```',
        '',
        '详情页「试试这样用」：',
        '',
    ]
    examples = listing.get('examples_zh') or []
    lines += [f'{number}. {item}' for number, item in enumerate(examples, 1)]
    if not examples:
        lines.append('（缺，在 SKILL.md 的 examples_zh 里补）')
    lines += [
        '',
        '建议类目：' + '、'.join(CATEGORIES[:2]) + '（后台最多选 5 个，按实际可选项挑）',
        '',
        '图标：`dist/structural-design-icon.png`（512×512，`python3 tools/make_skill_icon.py` 可重画；'
        '上传时单独提交，不放进 zip）',
        '',
        '## 审核会问的四件事',
        '',
        '**1. 前置条件。** 需要本机已有 FreeCAD 或 Blender 之一，技能自带运行时但不自带 CAD 内核。'
        '没找到时先问用户是否已安装、索取可执行文件完整路径并用 `--executable` 配置；'
        '确实没装才给官方下载链接、匹配系统与架构的稳定版本，经用户同意后安装，'
        '装完必须 `--probe` 实测。不承诺零配置出模型。',
        '',
        '**2. 能力边界。** 参数化零件、外壳、支架、板件、小装配体，以及对已有网格的改版。'
        '不做有机曲面的自动保证、不切片成机器 G-code、不判定可制造性或合规性——'
        '未实测前一律是 unknown。',
        '',
        '**3. 安全说明。** 查看器只监听 `127.0.0.1`，随机端口、一次性 token，并校验 Host 与 Origin；'
        '没有任何可执行任意命令的 HTTP 端点。建模通过本机 CAD 子进程完成，这是技能的工作方式。'
        '技能本体不发起网络请求，不上传模型、项目或用户数据。',
        '',
        '**4. 体积。** 解压后 '
        + f"{record['counts']['uncompressed_bytes'] / 1048576:.1f} MB"
        + '（Three.js 占大头），zip '
        + f"{archive.stat().st_size / 1024:.0f} KB" + '。'
        '包内只有一个运行时归档文件，首次运行自动解压到用户缓存目录，之后直接复用；'
        '所有随包路径都在技能根目录下两层以内。',
        '',
        '## 上传前自检',
        '',
        '```',
        f'python3 tools/build_skill.py --check --output {shown}',
        '```',
        '',
        '期望 `"state": "fresh"`。`stale` 表示构建之后仓库又动过，需重建；'
        '`tampered` 表示包内文件与自身记录不符，不要上传。',
        '',
        '## 上线后核对',
        '',
        '```',
        'python3 <skill>/scripts/et3d.py --bundle-info',
        '```',
        '',
        '打印的版本、commit、指纹应与本卡一致。技能库那份是静态快照，没有回推通道：'
        '上游更新后要重建 zip、重新上传，再用 `--install` 同步本机副本。',
    ]
    recent = git('log', '-6', '--oneline', '--no-decorate')
    if recent:
        lines += ['', '## 最近提交', '', '```', recent, '```']
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
    count, listing = verify(target, record)
    archive = zip_skill(target, output)
    summary = {
        'skill': str(target),
        'zip': str(archive),
        'version': record['runtime']['version'],
        'commit': record['source']['commit'],
        'tag': record['source']['tag'],
        'dirty': record['source']['dirty'],
        'files': count,
        'entries': record['counts']['entries'],
        'runtime_members': record['counts']['runtime_members'],
        'max_depth': record['layout']['max_depth'],
        'uncompressed_bytes': record['counts']['uncompressed_bytes'],
        'zip_bytes': archive.stat().st_size,
        'fingerprint': record['fingerprint'],
        'runtime': 'bundled',
        'install_required': False,
    }
    if args.notes:
        summary['notes'] = str(release_notes(record, archive, output, listing))
    if args.install:
        summary['local_install'] = install(target, Path(args.install))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
