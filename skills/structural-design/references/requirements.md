# Requirements card

`requirements/current.json` uses schema 1.0, a revision number, and items containing `id`, `source`, `description`, `status` (proposed/confirmed/assumed/superseded), `priority` (hard/preference), `verification`, optional `value`, `units`, `variants`, `annotation_ids`. Preserve the original source and never call an inferred dimension user-confirmed.

Use Project.requirements_set with the current revision for optimistic concurrency. Workspace creation snapshots the selected variant card, falling back to the project card. A new variant from a historical version inherits that version’s snapshot. Use requirements --variant <id> (or Project.requirements_set(..., variant_id=id)) for branch-specific changes; preserve its independent revision number. Update the chosen card before creating a revision workspace. Without --variant, edits affect the project card only. Continuing --parent without an explicit variant keeps the parent variant.

Print use adds manufacturing process, target size/unit, available build space, known wall thickness and clearance conditions. Unknown process-dependent properties remain unverified. When text, reference images and measurements conflict, explicit user-confirmed requirements take precedence; unresolved critical conflicts need clarification.
