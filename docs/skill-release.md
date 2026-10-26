# Skill release: keeping the library copy in sync

The `structural-design` skill ships the whole workbench inside itself, so a skill
library copy is a **snapshot**. There is no push channel from this repository into
the library. Sync is therefore a build plus an upload, and the build has to be
reproducible enough that "which code is the published skill running?" is a question
with a mechanical answer.

## One source of truth

The bundle is derived, never edited. `tools/build_skill.py` copies exactly these
sources into `structural-design/scripts/`, collapsing the runtime into one archive
so no shipped path sits more than two levels below the skill root:

| Source | In the bundle |
| --- | --- |
| `core/easy_to_3d/**.py`, `viewer/**`, `schemas/*.json` | inside `scripts/easy_to_3d.zip` |
| `skills/structural-design/SKILL.md`, `references/`, `scripts/et3d.py` | as-is |

The launcher unpacks that archive once per build fingerprint into the user's cache
directory and reuses it, so the first command of a session costs one extraction.
`verify()` fails the build if any shipped path goes deeper than two levels, and
again if the archive's members disagree with the stamp, so the depth limit cannot
regress quietly.

`dist/` is gitignored and rebuildable; nothing in the repository imports from it.
Never hand-edit a bundle or an installed skill directory: the next rebuild silently
reverts it, and until then the copy claims a commit that does not contain it.

## The listing header

The library parser rejects a zip before human review when `SKILL.md` is missing a
required field, so the header is part of the deliverable, not decoration.
`tools/build_skill.py` validates it on every build and refuses to ship otherwise.

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | Lowercase letters, digits, single hyphens |
| `display_name`, `display_name_en` | yes | Shown in the market listing |
| `description` | yes | Purpose plus trigger words; the Agent matches on this |
| `description_zh`, `description_en` | yes | Detail-page introduction |
| `version` | yes | Must equal `pyproject.toml`, or the listing contradicts `--bundle-info` |
| `author` | yes | Partner or account name |
| `examples_zh`, `examples_en` | recommended | Detail-page "try it like this"; reviewers tend to run these |

Values must survive plain YAML: a `: ` inside an unquoted value, or a leading `#`,
`-` or quote, is rejected instead of silently truncating the field.

The listing icon is generated rather than stored:

```
python3 tools/make_skill_icon.py      # dist/structural-design-icon.png, 512x512
```

Upload the icon separately in the library form; it is not part of the zip.

## Release

1. Bump `version` in `pyproject.toml`, mirror it in `core/easy_to_3d/__init__.py`
   and in the `SKILL.md` header (the builder refuses to run when any of them
   disagree), commit, and tag `v<version>`.
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

`--notes` writes `dist/structural-design-release.md`, a card that answers the upload
form rather than just describing the build. It carries the fields to paste — `name`,
both display names, version, author, the Chinese and English descriptions, and the
three Chinese examples for the detail page — plus a suggested category, the command
that redraws the icon, the four answers reviewers ask for (prerequisites, scope,
safety, size), the pre-upload `--check` and the `--bundle-info` call to verify what
was actually served after publishing. Read the version, commit and fingerprint off the
same card so the listing and the release cannot drift apart.

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

Prints the stamped version, commit, tag, build time, fingerprint, which runtime the
launcher will actually load (`bundled`, `checkout`, or `installed`), and — for a
bundled runtime — whether it came from the archive or a plain directory, plus the
path it was unpacked to. A user reporting a bug can include this output instead of
describing their setup.

## Keeping the local Agent on the new version

```
python3 tools/build_skill.py --output dist/skill --force --install ~/.workbuddy/skills
```

The previous copy is moved to `~/.workbuddy/skills-backups/structural-design.bak-<timestamp>`
rather than deleted. It goes to a sibling directory, not into the skills directory:
every directory holding a `SKILL.md` is discovered as a skill, so a backup left
beside its successor loads as a second copy of the same skill.
