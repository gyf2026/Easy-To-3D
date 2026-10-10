---
name: structural-design
description: Build and revise mechanical parts, enclosures and small static assemblies with Easy-To-3D, using native CAD or Blender scripts, versioned 3D reviews, drawings and print exports. Use for Easy-To-3D design projects; artistic sculpting remains experimental.
---

# Easy-To-3D structural design

Use the user's Agent client for reasoning and freely authored modeling scripts. Easy-To-3D stores requirements, versions, previews and structured review; it does not prescribe geometry operations or interpret feedback through keyword rules.

For existing meshes or a client's external 3D generator, read [external models](references/external-models.md). Preserve appearance and the original file, discover actual editing capabilities, and import returned results as children of the reviewed version.

Read [user workflow](references/user-workflow.md) to discover current client capabilities, select a task-appropriate route, and keep setup/save/print operations in the Agent conversation.

## Start or resume

Run `easy-to-3d --json project inspect --project <path>` for an existing project. Read its current requirements, selected version, pending batches and incomplete workspaces. Project ID is authoritative; names can collide. For a new project use `project init --parent <user-design-directory> --name <object> --feature <key-feature>`.

Read [environment](references/environment.md) before first modeling or after a backend failure. Local doctor output does not establish the current model's vision capability. Verify image delivery with a known geometry image in the actual session; record pass/fail/unknown and test context. Image generation is optional. Reuse existing installations; neither backend is mandatory if the other meets the task.

Gather critical dimensions and structural intent together. Store unresolved assumptions visibly. Existing user confirmations and authorization remain valid. Read [requirements](references/requirements.md) when creating or changing the requirements card.

## Build and deliver

Select a verified client generation/edit route or a task-appropriate local backend. External results follow the import and handoff contract. For local modeling, create a workspace, write any appropriate FreeCAD or Blender script, preserve its inputs, and run through `easy-to-3d run --workspace <path> --timeout <seconds> -- <argv>`. Examples illustrate export contracts; they are not a closed library. Read [backend workflow](references/backends.md) for the workspace artifacts contract.

For precision structures, first produce a white model and consistent orthographic views for layout confirmation. Organic appearance tasks may start with a textured candidate. Record the exact version the user confirms. Then refine and check the relevant hard constraints. Use `check --workspace <path> --profile structure`; add print or patent only when selected. A missing print configuration never blocks structural review. Native validity and requirement checks need actual measurement evidence; unknown is not pass.

A candidate may contain explicit unresolved checks. Failed or timed-out execution cannot be published. Publish through `version publish --project <path> --workspace <workspace-id> --summary <change>`, then open `view --project <path>`. Never edit published models, scripts or requirements snapshots in place.

Read [validation](references/validation.md) for revision limits and verification. Read [drawings and print](references/deliverables.md) only for those uses. Export success and manufacturing or patent suitability are separate results. Prefer saving, verified whole-project backup and delivery through Agent commands; `delivery-guide --project <path> --version <id>` returns concrete argv and printer configuration questions. Viewer exports are optional.

## Review and revise

Read [review](references/review.md) when the user submits a review batch. Restore each annotation's original model version, explicit millimetre coordinates, camera and hidden parts. Do not use screenshots or triangle indices as cross-version identity. Create a child workspace from the reviewed version, preserve unrelated confirmed dimensions, publish a new version, and respond separately to every annotation with result version and evidence. Only the user accepts subjective feedback.

If interrupted, failed, or changing chat, inspect the project again. Keep incomplete workspaces and execution logs. Report what is implemented, what actually passed, what is unknown, and the next concrete action; do not mark a model accepted based only on Agent confidence.


Language and naming: use the language the user uses to communicate with the Agent (zh/en/ja/fr), unless the user requests otherwise. Pass `project init --language <code>` and use that language for `--name`, `--feature`, design summaries and human-facing generated/export filenames. Keep technical keys and fixed artifact-contract paths unchanged. Open `view --language <code>` for the current conversation, including existing projects; never rename published artifacts or existing project paths in place. Unsupported conversation languages fall back to Chinese and offer the four supported choices. The user can change the viewer language manually.

Visible review numbers are consecutive among non-deleted annotations and may change after deletion. Use annotation IDs plus source version/batch IDs as authoritative references, never numbers alone.
