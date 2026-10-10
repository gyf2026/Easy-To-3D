# Agent-led workflow

Discover tools actually exposed by the current host. Never infer generation or local geometry editing from a client/model name. Run lightweight `doctor --cache <local-cache.json>` first. Probe only the local backend needed by the task. Cache is invalidated by platform/tool/path/probe changes and expires after seven days; use --refresh after failure. Do not put local capability caches in Git.

Test generation, geometry_edit, texture_edit, local_download, execution, vision and slicing separately. Use the session report below with client/model/tools_fingerprint, timezone-aware tested_at, pass/fail/unknown and evidence for every pass. Supply --session-report to doctor. It is Agent-supplied evidence, not core verification of host private APIs. Retest after context changes; unknown is not missing. Keep credentials in the client's existing facilities.

Gather only task-blocking missing requirements. Select explicit organic/precision/mesh-edit/texture/save/print and use `workflow-guide --task <task> --report <doctor-report.json>`. Explain the selected route in one short sentence. Organic appearance may prefer verified client generation; precision prefers CAD. Mesh edits prefer verified local geometry editing, otherwise Blender. Texture editing is separate. Do not insist on a cloud service when a verified local route is available.

Find existing installs and ask for a path before proposing installation. Give a concrete official version, architecture, installation location and privileges; after user consent download, verify, install and probe. Reuse applicable consent. Do not demand all tools, auto-upload private models or trigger unapproved paid calls.

Before showing a candidate, check actual geometry, dimensions, declared units/up-axis and rendered views against the user's requirements. Correct recoverable failures and recheck. For precise structure confirm white-model layout first; organic appearance may use a textured first candidate. Separate measured pass, subjective confirmation and unknown physical/printing behavior.

Submitted ✅ means sent to Agent, not completed or accepted. Read exact source version and review batch via handoff. Restore marked views, keep unrelated requirements and immutable originals. If only regeneration is possible, explain possible changes before using it. Publish child of reviewed source, verify changed/preserved constraints, respond individually and open comparison. Users do not shuttle JSON or select parents manually.

Save and export in the conversation. Flush browser drafts before verified whole-project backup. Core exports STL; other formats require validated conversion. Use delivery-guide for actual version-bound commands, ask only missing printer/material/profile details, and use the installed slicer's real CLI. Verify machine files and report paths and limitations. Do not start printing.

Session report example (replace context and date with the actual current session; never copy a fixture as evidence):

```json
{
  "context": {"client": "actual client and version", "model": "actual model", "tools_fingerprint": "actual tools and versions"},
  "tested_at": "2026-10-10T00:00:00+00:00",
  "capabilities": {
    "generation": {"status": "unknown"},
    "geometry_edit": {"status": "unknown"},
    "texture_edit": {"status": "unknown"},
    "local_download": {"status": "unknown"},
    "execution": {"status": "unknown"},
    "vision": {"status": "unknown"},
    "slicing": {"status": "unknown"}
  }
}
```

For a measured pass, add an evidence string naming the actual test and evidence location. Reports older than seven days become unknown. Keep the report in the user's local environment, outside the source repository.


Language and naming: use the language the user uses to communicate with the Agent (zh/en/ja/fr), unless the user requests otherwise. Pass `project init --language <code>` and use that language for `--name`, `--feature`, design summaries and human-facing generated/export filenames. Keep technical keys and fixed artifact-contract paths unchanged. Open `view --language <code>` for the current conversation, including existing projects; never rename published artifacts or existing project paths in place. Unsupported conversation languages fall back to Chinese and offer the four supported choices. The user can change the viewer language manually.

Visible review numbers are consecutive among non-deleted annotations and may change after deletion. Use annotation IDs plus source version/batch IDs as authoritative references, never numbers alone.
