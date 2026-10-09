"""Atomic file storage, bounded paths and cross-process locking."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import uuid

class ContractError(ValueError):
    pass

class Conflict(ContractError):
    pass

def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

def uid(prefix):
    return prefix + '_' + uuid.uuid4().hex[:16]

def read(path):
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream)

def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return 'sha256:' + result.hexdigest()

def fingerprint(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def confined(root, relative):
    root = Path(root).resolve()
    candidate = Path(relative)
    if candidate.is_absolute() or '..' in candidate.parts:
        raise ContractError('Path must be relative and contained in project')
    target = (root / candidate).resolve()
    if not target.is_relative_to(root):
        raise ContractError('Path escapes project')
    return target

@contextlib.contextmanager
def lock(root, timeout=10):
    """OS-released lock; a crashed process cannot strand it."""
    path = Path(root) / '.write.lock'
    with path.open('a+b') as stream:
        deadline = time.monotonic() + timeout
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                stream.write(b'0'); stream.flush()
            def acquire():
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            def release():
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            def acquire():
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            def release():
                fcntl.flock(stream, fcntl.LOCK_UN)
        while True:
            try:
                acquire(); break
            except OSError:
                if time.monotonic() >= deadline:
                    raise Conflict('Project is busy; retry')
                time.sleep(.025)
        try:
            yield
        finally:
            release()
