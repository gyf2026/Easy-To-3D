#!/usr/bin/env python3
"""Run Easy-To-3D from this skill directory.

Resolution order:
1. The copy bundled in this skill at scripts/easy_to_3d. Installed skills ship it,
   so nothing has to be installed or downloaded separately.
2. A source checkout two levels up (skills/structural-design/scripts -> repo core/),
   so the same skill works while developing the workbench itself.
3. An importable easy_to_3d package already present on this machine.

Arguments are passed through unchanged, so every documented command works as
`python3 <skill>/scripts/et3d.py --json <command> ...`.

`--bundle-info` is the one exception: it prints which runtime this skill will use
and the build record it shipped with, so a stale or hand-edited copy is visible
without reading any code.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLED = HERE / "easy_to_3d"
CHECKOUT = HERE.parents[2] / "core" if len(HERE.parents) > 2 else None
BUILD_RECORD = HERE / "BUILD.json"


def locate():
    if (BUNDLED / "__init__.py").is_file():
        return "bundled", BUNDLED
    if CHECKOUT is not None and (CHECKOUT / "easy_to_3d" / "__init__.py").is_file():
        return "checkout", CHECKOUT / "easy_to_3d"
    try:
        import easy_to_3d
    except ImportError:
        return None, None
    return "installed", Path(easy_to_3d.__file__).resolve().parent


def activate():
    origin, path = locate()
    if origin == "bundled":
        sys.path.insert(0, str(HERE))
    elif origin == "checkout":
        sys.path.insert(0, str(CHECKOUT))
    elif origin == "installed":
        print("[et3d] using installed easy-to-3d at " + str(path), file=sys.stderr)
    return origin


def bundle_info():
    origin, path = locate()
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
    report["runtime_path"] = str(path) if path else None
    report["skill_directory"] = str(HERE.parent)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if origin else 2


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--bundle-info":
        return bundle_info()
    origin = activate()
    if origin is None:
        print(
            "Easy-To-3D runtime not found.\n"
            "Looked for a bundled copy at " + str(BUNDLED / "__init__.py") +
            " and for an importable easy_to_3d package.\n"
            "Reinstall the structural-design skill, or install the package with\n"
            "  pip install git+https://github.com/gyf2026/Easy-To-3D",
            file=sys.stderr,
        )
        return 2
    from easy_to_3d.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
