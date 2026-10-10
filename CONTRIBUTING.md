# Contributing

Bug reports, reproducible examples, documentation improvements and focused pull requests are welcome. Please describe the user-visible problem, expected behavior and environment. Use synthetic or shareable models; remove private paths, credentials and personal designs.

## Development

Use Python 3.10+ and install `python -m pip install '.[dev]'`. Build a fresh release candidate with `python tools/build_release.py --output <new-directory>`. The output directory must not already exist.

Keep user projects outside the source checkout. Modeling scripts remain unrestricted; the core manages stable artifacts and review records. Changes to coordinates, cameras, publication or review protocols should update schemas and the design decisions. Requirements, source artifacts and published versions are immutable; revisions create child versions. Report execution, validation and user acceptance separately.

## Validation scope

Public CI builds packages, installs the wheel and starts the CLI on the configured platforms. The full functional suite and raw validation evidence are maintained separately and are not currently distributed. Contributors can provide a minimal reproduction and manual verification steps; maintainers run the relevant internal regressions before merging behavior changes. A green CI result is not complete functional validation.

Do not mark an untested platform or client as supported. Distinguish synthetic fixtures from real backend tests and update [compatibility](docs/compatibility.md) with the scope of actual evidence. Document skipped or unknown checks.

Code is licensed under Apache-2.0. Preserve third-party notices and submit only material you have the right to contribute.
