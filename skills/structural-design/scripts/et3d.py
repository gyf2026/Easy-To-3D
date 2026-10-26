#!/usr/bin/env python3
"""Run Easy-To-3D from this skill directory.

Resolution order:
1. The runtime bundled in this skill. Installed skills ship it as a single file,
   scripts/easy_to_3d.zip, which is unpacked once into the user's cache directory
   and reused from there. A plain scripts/easy_to_3d/ directory is used as-is if
   one is present, so an unbundled working copy still runs.
2. A source checkout two levels up (skills/structural-design/scripts -> repo core/),
   so the same skill works while developing the workbench itself.
3. An importable easy_to_3d package already present on this machine.

The bundled runtime ships as one archive because a skill library may cap how deep
a package may nest directories; the archive keeps every shipped path at most two
levels below the skill root.

Arguments are passed through unchanged, so every documented command works as
`python3 <skill>/scripts/et3d.py --json <command> ...`.

`--bundle-info` is the one exception: it prints which runtime this skill will use
and the build record it shipped with, so a stale or hand-edited copy is visible
without reading any code.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

MINIMUM = (3, 10)

HERE = Path(__file__).resolve().parent
BUNDLED = HERE / "easy_to_3d"
ARCHIVE = HERE / "easy_to_3d.zip"
CHECKOUT = HERE.parents[2] / "core" if len(HERE.parents) > 2 else None
BUILD_RECORD = HERE / "BUILD.json"
CACHE_NAME = "easy-to-3d"


def cache_root():
    """Where a per-user cache belongs on this platform, without a helper package."""
    override = os.environ.get("EASY_TO_3D_CACHE")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Caches")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / CACHE_NAME


def archive_stamp(archive):
    """A directory name that changes exactly when the archive's contents change."""
    if BUILD_RECORD.is_file():
        try:
            record = json.loads(BUILD_RECORD.read_text(encoding="utf-8"))
            stamp = record.get("fingerprint")
            if isinstance(stamp, str) and len(stamp) >= 16:
                return stamp[:16]
        except (ValueError, OSError):
            pass
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:16]


def safe_members(bundle):
    """Reject a member that would escape the extraction directory."""
    for info in bundle.infolist():
        name = info.filename.replace("\\", "/")
        parts = [part for part in name.split("/") if part not in ("", ".")]
        if name.startswith("/") or ".." in parts or (parts and ":" in parts[0]):
            raise ValueError("unsafe member in runtime archive: " + info.filename)


def unpack_into(archive, base):
    stamp = archive_stamp(archive)
    home = base / stamp
    target = home / "easy_to_3d"
    if (target / "__init__.py").is_file():
        return target
    base.mkdir(parents=True, exist_ok=True)
    staging = base / (".staging-" + stamp + "-" + str(os.getpid()))
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    try:
        with zipfile.ZipFile(archive) as bundle:
            safe_members(bundle)
            bundle.extractall(staging)
        if not (staging / "easy_to_3d" / "__init__.py").is_file():
            raise ValueError("runtime archive has no easy_to_3d/__init__.py")
        try:
            os.replace(str(staging), str(home))
        except OSError:
            # Another process finished first, or the name is taken; our copy is
            # redundant either way, and the winner's copy is re-checked below.
            shutil.rmtree(staging, ignore_errors=True)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if not (target / "__init__.py").is_file():
        raise ValueError("runtime archive did not unpack to " + str(target))
    return target


def unpack(archive):
    """Unpack once per build fingerprint; fall back to a private temp dir if the
    user's cache is not writable."""
    try:
        return unpack_into(archive, cache_root()), "cache"
    except OSError:
        return unpack_into(archive, Path(tempfile.mkdtemp(prefix=CACHE_NAME + "-"))), "temp"


def locate():
    """(origin, importable parent directory, layout)."""
    if (BUNDLED / "__init__.py").is_file():
        return "bundled", HERE, "directory"
    if ARCHIVE.is_file():
        path, where = unpack(ARCHIVE)
        return "bundled", path.parent, "archive/" + where
    if CHECKOUT is not None and (CHECKOUT / "easy_to_3d" / "__init__.py").is_file():
        return "checkout", CHECKOUT, "checkout"
    try:
        import easy_to_3d
    except ImportError:
        return None, None, None
    return "installed", Path(easy_to_3d.__file__).resolve().parent.parent, "installed"


def activate():
    origin, parent, layout = locate()
    if origin in ("bundled", "checkout"):
        sys.path.insert(0, str(parent))
    elif origin == "installed":
        print("[et3d] using installed easy-to-3d at " + str(parent), file=sys.stderr)
    return origin, layout


def bundle_info():
    origin, parent, layout = locate()
    if BUILD_RECORD.is_file():
        record = json.loads(BUILD_RECORD.read_text(encoding="utf-8"))
        source = record.get("source") or {}
        report = {
            "bundle": "stamped",
            "version": (record.get("runtime") or {}).get("version"),
            "commit": source.get("commit"),
            "tag": source.get("tag"),
            "dirty": source.get("dirty"),
            "built_at": record.get("built_at"),
            "fingerprint": record.get("fingerprint"),
        }
    else:
        report = {
            "bundle": "unstamped",
            "detail": "No scripts/BUILD.json; this skill directory is a source checkout or a "
                      "pre-stamping bundle.",
        }
    report["runtime_origin"] = origin
    report["runtime_layout"] = layout
    report["runtime_path"] = str(parent / "easy_to_3d") if parent else None
    report["skill_directory"] = str(HERE.parent)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if origin else 2


def self_check():
    """Prove the activated runtime imports and can find its own data files."""
    from easy_to_3d import __version__
    from easy_to_3d.server import WEB
    report = {
        "version": __version__,
        "web_directory": str(WEB),
        "web_present": WEB.is_dir(),
        "web_files": sorted(p.name for p in WEB.glob("*")) if WEB.is_dir() else [],
    }
    for module in ("easy_to_3d.project", "easy_to_3d.glb", "easy_to_3d.checks",
                   "easy_to_3d.server", "easy_to_3d.cli"):
        try:
            __import__(module)
            report[module] = "ok"
        except Exception as error:  # noqa: BLE001 - report anything, do not mask it
            report[module] = type(error).__name__ + ": " + str(error)[:200]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["web_present"] and all(
        report[m] == "ok" for m in report if m.startswith("easy_to_3d.")) else 1


def too_old():
    """Report a too-old interpreter as a one-line repair instruction.

    Kept free of newer syntax on purpose: this is the one place that must still
    parse and speak on an interpreter the runtime itself cannot run on.
    """
    found = "%d.%d.%d" % (sys.version_info[0], sys.version_info[1], sys.version_info[2])
    launcher = str(HERE / "et3d.py")
    sys.stderr.write(
        "Easy-To-3D needs Python 3.10 or newer; this is Python " + found + "\n"
        "  interpreter: " + sys.executable + "\n"
        "Rerun the same command with a newer one, for example:\n"
        "  py -3.13 " + launcher + " ...      (Windows)\n"
        "  python3.13 " + launcher + " ...    (macOS, Linux)\n"
        "Nothing is broken; the interpreter is just older than the runtime.\n"
    )


def main():
    if sys.version_info < MINIMUM:
        too_old()
        return 2
    if len(sys.argv) > 1 and sys.argv[1] == "--bundle-info":
        return bundle_info()
    origin, _layout = activate()
    if origin is None:
        print(
            "Easy-To-3D runtime not found.\n"
            "Looked for " + str(BUNDLED / "__init__.py") + " and " + str(ARCHIVE) +
            ", and for an importable easy_to_3d package.\n"
            "Reinstall the structural-design skill, or install the package with\n"
            "  pip install git+https://github.com/gyf2026/Easy-To-3D",
            file=sys.stderr,
        )
        return 2
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        return self_check()
    from easy_to_3d.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
