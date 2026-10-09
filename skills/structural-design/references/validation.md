# Checks and stopping

Check exact workspace inputs; reports contain an input fingerprint and become stale when source, script, parameters or preview changes. Distinguish artifact completeness, input snapshot completeness and environment rebuild compatibility. A software upgrade does not invalidate unchanged historical artifacts for viewing.

Default automatic correction limit: 3 rounds and 900 seconds. Stop sooner after repeated same failure, subprocess failure/timeout or quality regression. Record each proposed change, actual execution and relevant recheck. Save unresolved work as candidate/incomplete, never accepted.

Mesh checking measures dimensions, welded boundary/nonmanifold edges, winding, degenerate triangles and signed volume; it cannot infer wall thickness, clearances or support feasibility. Native geometry validity must be checked by the actual backend. Requirements need independent measurements, not success prose or checks based on script constants alone.

Before exporting run `version verify --project <path> --version <id>`. Corruption blocks exports; current environment mismatch alone does not prevent access to history. Tests distinguish logic, real HTTP/browser, backend and Agent scenario evidence.

Before asking the user to review a generated model, compare every confirmed structural requirement against independent native measurements and inspect actual model views for qualitative layout and shape requirements. Record what was checked and the evidence. Correct detected mismatches within the limits above and recheck the changed geometry plus unrelated confirmed constraints. An explicit hard-check failure must not be presented as ready for normal user review; retain it only as an incomplete/debug candidate and explain the blocker. Unknown checks and unresolved assumptions must remain visible to the user. A passed numerical report alone does not establish visual or semantic compliance, manufacturing suitability, or user acceptance.
