# Skill release: keeping the library copy in sync

The `structural-design` skill ships the whole workbench inside itself, so a skill
library copy is a **snapshot**. There is no push channel from this repository into
the library. Sync is therefore a build plus an upload, and the build has to be
reproducible enough that "which code is the published skill running?" is a question
with a mechanical answer.

## One source of truth

The bundle is derived, never edited. `tools/build_skill.py` copies exactly these
sources into `structural-design/scripts/`:

| Source | In the bundle |
| --- | --- |
| `core/easy_to_3d/**.py` | `scripts/easy_to_3d/` |
| `viewer/**` | `scripts/easy_to_3d/web/` |
| `schemas/*.json` | `scripts/easy_to_3d/schemas/` |
| `skills/structural-design/SKILL.md`, `references/`, `scripts/et3d.py` | as-is |

`dist/` is gitignored and rebuildable; nothing in the repository imports from it.
Never hand-edit a bundle or an installed skill directory: the next rebuild silently
reverts it, and until then the copy claims a commit that does not contain it.

## Release

1. Bump `version` in `pyproject.toml`, mirror it in `core/easy_to_3d/__init__.py`
   (the builder refuses to run when they disagree), commit, and tag `v<version>`.
2. Push the tag. `.github/workflows/skill-bundle.yml` builds the bundle, fails if
   the stamp disagrees with the checkout, and attaches `structural-design.zip` plus
   `structural-design-release.md` to the GitHub release. The builder also compares
   the archive against the assembled directory, so a zip missing `BUILD.json` (or
   missing any other file the bundle has) fails the build instead of shipping.
3. Download the zip from the release and upload it as the new skill version in the
   skill library. This step stays manual: the upload form lives in the account that
   owns the listing, and marketplace rules forbid automating submissions.

Build locally with the same command CI uses when the release has to happen without
a push:

```
python3 tools/build_skill.py --output dist/skill --notes
python3 tools/build_skill.py --check --output dist/skill
```

`--notes` writes `dist/structural-design-release.md`, a card with the version,
commit, fingerprint and upload checklist for the library form.

## Detecting drift

```
python3 tools/build_skill.py --check --output dist/skill
python3 tools/build_skill.py --check --output ~/.workbuddy/skills
```

| `state` | Meaning | Action |
| --- | --- | --- |
| `fresh` | Bundle bytes match the working tree | Nothing |
| `stale` | Sources changed after the build | Rebuild and publish a new version |
| `tampered` | Bundle no longer matches its own `BUILD.json` | Discard it; rebuild |
| `missing` | No `BUILD.json` (pre-stamping or foreign copy) | Rebuild |

`--check` exits non-zero for anything but `fresh`, so it can gate a release job.

## Verifying an installed copy

```
python3 <skill>/scripts/et3d.py --bundle-info
```

Prints the stamped version, commit, tag, build time, fingerprint, and which runtime
the launcher will actually load (`bundled`, `checkout`, or `installed`). A user
reporting a bug can include this output instead of describing their setup.

## Keeping the local Agent on the new version

```
python3 tools/build_skill.py --output dist/skill --force --install ~/.workbuddy/skills
```

The previous copy is moved to `~/.workbuddy/skills/structural-design.bak-<timestamp>`
rather than deleted.
