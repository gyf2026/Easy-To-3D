---
name: structural-design
display_name: 3D设计与评审修改
display_name_en: 3D Design, Review and Revision
description: Build and revise mechanical parts, enclosures and small static assemblies with Easy-To-3D, using native CAD or Blender scripts, versioned 3D reviews, drawings and print exports. Use for Easy-To-3D design projects; artistic sculpting remains experimental. 触发词：建模、结构设计、3D打印、支架、外壳、零件、改模型、看模型、旋转模型、加个孔、加高、减薄、版本对比、新旧对比、导出STL、导出图纸、FreeCAD、Blender、机械结构。
description_zh: 面向机械零件、外壳与小装配体的设计与改版工作台：Agent 写 FreeCAD/Blender 脚本建模，用户在浏览器里旋转查看、在模型表面点位置写点评，Agent 按点评出子版本再同视角新旧对比。含毫米单位与坐标约定、逐版本不可变快照、需求测量比对、图纸与打印导出。需要本机已有可用的 FreeCAD 或 Blender；没有时会引导用户提供安装位置或按官方来源安装。
description_en: A design and revision workbench for mechanical parts, enclosures and small assemblies. The Agent writes FreeCAD or Blender scripts; the user rotates the model in a browser, annotates points on its surfaces, and the Agent publishes a child version that is compared side by side from the same camera. Millimetre conventions, immutable version snapshots, requirement measurement checks, drawings and print export. Requires a working local FreeCAD or Blender; when neither exists the Agent asks for its location or guides an official installation.
examples_zh:
- 帮我做一个 60×40 的 L 型支架，底板 4 mm 厚，两个 6 mm 孔距边 10 mm，最后导出 STL
- 把上一版立板再加高 8 mm，槽口从 4 个改成 3 个，然后出个新版本让我左右对比
- 我想给这个外壳侧面加一排散热孔，按我在模型上点的那几处位置改
examples_en:
- Make a 60×40 L-bracket with a 4 mm base plate and two 6 mm holes 10 mm from the edge, then export an STL
- Raise the upright 8 mm over the last version, change four slots to three, and publish a new version I can compare side by side
- Add a row of vents to the side of this enclosure, following the spots I marked on the model
version: 0.1.0a8
author: gyf2026
---

# Easy-To-3D structural design

Use the user's Agent client for reasoning and freely authored modeling scripts. Easy-To-3D stores requirements, versions, previews and structured review; it does not prescribe geometry operations or interpret feedback through keyword rules.

## Runtime

The workbench ships inside this skill, so there is nothing to install, download or
add to `PATH`. Every `et3d` below is shorthand for the launcher next to this file;
substitute the form that matches the host OS.

| Host | Launcher |
|---|---|
| macOS, Linux | `python3 <skill>/scripts/et3d.py` |
| Windows | `py -3 <skill>\scripts\et3d.py`, or `python` when `py` is absent |

`<skill>` is the directory containing this `SKILL.md`. The runtime lives in
`<skill>/scripts/easy_to_3d.zip`; the launcher unpacks it once per build into the
user's cache directory and reuses it, so the first command of a session may take a
second longer than the rest. That cache is disposable — delete it and the next run
recreates it. There is no third-party dependency to install: the runtime is standard
library only.

**Any CPython from 3.10 up runs it.** It has been run on Windows with 3.10 through
3.15 and on macOS with 3.13, so a newer interpreter is never a reason to expect a
break. Interpreters below 3.10 refuse in one line, naming the version and the
executable they were handed, instead of dying inside a module.

That refusal is a repair instruction, not a dead end. Read the version in it, pick a
newer interpreter the machine already has — `py -3.13`, `py -3.12`, `python3.13`, or
whichever one your own runtime ships — and rerun the same command with it. A missing
module reported by an otherwise working interpreter means the same thing: try the
other launcher form before concluding the skill is broken. Only escalate to the user
when no interpreter 3.10+ exists at all. `et3d --json doctor` is the first check when
any command fails.

`scripts/BUILD.json` records the version, source commit and a SHA-256 per file this
bundle was built from. Run `et3d --bundle-info` to print them together with the
runtime actually loaded. These files are best left as shipped: a local edit makes
that record inaccurate and is replaced by the next install, so upstream fixes and
local improvements are better carried by a new build than by patching this copy.

## What this needs from the machine

The workbench does not carry a CAD kernel. It drives one that is already on the
machine, so a working **FreeCAD or Blender** — one is enough, not both — is the one
real prerequisite. Establish this before promising any model:

1. Run `et3d --json doctor --backend all` and read each backend's `found`, `launch`
   and `script_export`. `script_export` stays `unknown` until you pass `--probe`;
   never report it as working on the strength of `found` alone.
2. **If a backend is found**, use it. Do not install a second one "to be safe".
3. **If none is found**, ask the user first, in this order: is it already installed
   somewhere? If yes, ask for the full path to the executable and configure it with
   `et3d --json doctor --backend <name> --executable "<path>" --probe`. Point out
   that this is the program itself, not the install folder, the `.app` bundle or the
   installer.
4. **If it is genuinely not installed**, say so plainly, then offer the official
   download from `setup_guidance.download`, a build matching the host OS and CPU
   architecture, the install location and the privileges it needs. Let the user pick
   between installing it themselves and having you install it. Only after consent do
   you download, install, verify any published checksum, configure the path and
   rerun `--probe`. Reuse that consent for the same installation.

`doctor` returns `setup_guidance` with `download`, `executable_hint`,
`recommended_configuration` and the exact `configure_command` for this runtime —
hand those to the user verbatim instead of rewriting them from memory.

A missing backend is a blocked route, not a failed design. Until one is available,
offer what needs no CAD: reviewing an existing mesh, importing an external result and
managing versions. Do not claim a new model was produced.

## Start or resume

Run `et3d --json project inspect --project <path>` for an existing project. Read its current requirements, selected version, pending batches and incomplete workspaces. Project ID is authoritative; names can collide. For a new project use `et3d project init --parent <user-design-directory> --name <object> --feature <key-feature>`.

Read [environment](references/environment.md) before first modeling or after a backend failure. Local doctor output does not establish the current model's vision capability. Verify image delivery with a known geometry image in the actual session; record pass/fail/unknown and test context. Image generation is optional. Reuse existing installations; neither backend is mandatory if the other meets the task.

Gather critical dimensions and structural intent together. Store unresolved assumptions visibly. Existing user confirmations and authorization remain valid. Read [requirements](references/requirements.md) when creating or changing the requirements card.

## Build and deliver

Select a verified client generation/edit route or a task-appropriate local backend. External results follow the import and handoff contract. For local modeling, create a workspace, write any appropriate FreeCAD or Blender script, preserve its inputs, and run through `et3d run --workspace <path> --timeout <seconds> -- <argv>`. A backend can exit 0 after a script exception, so confirm the run produced `artifacts.json` and read its stderr before checking or publishing. Examples illustrate export contracts; they are not a closed library. Read [backend workflow](references/backends.md) for the workspace artifacts contract.

For precision structures, first produce a white model and consistent orthographic views for layout confirmation. Organic appearance tasks may start with a textured candidate. Record the exact version the user confirms. Then refine and check the relevant hard constraints. Use `et3d check --workspace <path> --profile structure`; add print or patent only when selected. A missing print configuration never blocks structural review. Native validity and requirement checks need actual measurement evidence; unknown is not pass.

A candidate may contain explicit unresolved checks. Failed or timed-out execution cannot be published. Publish through `et3d version publish --project <path> --workspace <workspace-id> --summary <change>`, then open `et3d view --project <path>`. Never edit published models, scripts or requirements snapshots in place.

Read [validation](references/validation.md) for revision limits and verification. Read [drawings and print](references/deliverables.md) only for those uses. Export success and manufacturing or patent suitability are separate results. Prefer saving, verified whole-project backup and delivery through Agent commands; `et3d delivery-guide --project <path> --version <id>` returns concrete argv and printer configuration questions. Viewer exports are optional.

## Review and revise

Read [review](references/review.md) when the user submits a review batch. Restore each annotation's original model version, explicit millimetre coordinates, camera and hidden parts with `et3d --json review restore --project <path> --annotation <id>`. Do not use screenshots or triangle indices as cross-version identity. Create a child workspace from the reviewed version, preserve unrelated confirmed dimensions, publish a new version, and respond to every annotation with `et3d review respond`, giving result version and evidence. Only the user accepts subjective feedback.

If interrupted, failed, or changing chat, inspect the project again. Keep incomplete workspaces and execution logs. Report what is implemented, what actually passed, what is unknown, and the next concrete action; do not mark a model accepted based only on Agent confidence.

## Viewing, importing, routing

The viewer runs on `127.0.0.1` and is opened by `et3d view`. Keep it in the Agent conversation: start it, read the printed URL, and give that URL to the user.

For existing meshes or a client's external 3D generator, read [external models](references/external-models.md). Preserve appearance and the original file, discover actual editing capabilities, and import returned results as children of the reviewed version.

Read [user workflow](references/user-workflow.md) to discover current client capabilities, select a task-appropriate route, and keep setup/save/print operations in the Agent conversation.

## Language and naming

Use the language the user uses to communicate with the Agent (zh/en/ja/fr), unless the user requests otherwise. Pass `et3d project init --language <code>` and use that language for `--name`, `--feature`, design summaries and human-facing generated/export filenames. Keep technical keys and fixed artifact-contract paths unchanged. Open `et3d view --language <code>` for the current conversation, including existing projects; never rename published artifacts or existing project paths in place. Unsupported conversation languages fall back to Chinese and offer the four supported choices. The user can change the viewer language manually.

Visible review numbers are consecutive among non-deleted annotations and may change after deletion. Use annotation IDs plus source version/batch IDs as authoritative references, never numbers alone.

## Scope and limits

In scope: parametric and prismatic parts, enclosures, brackets, plates, small static assemblies, and revision of an existing mesh. Out of scope, and worth saying out loud rather than attempting: free-form organic sculpting as an automated guarantee, slicing to a specific printer's G-code, and any statement that a model is manufacturable, food-safe or certifiable — those stay `unknown` until measured and accepted by the user.

The Agent reasons and writes the geometry script; this skill stores requirements, versions, previews and structured review. It does not turn prose into geometry by itself, does not keyword-match feedback into commands, and does not decide that a model is finished. "Not checked" and "passed" are different answers everywhere in this skill.
