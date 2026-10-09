# Free scripting and artifacts

Each workspace contains `source/`, `scripts/`, `dependencies/`, `preview/`, `drawings/`, `exports/`, `checks/`, `requirements.snapshot.json` and `workspace.json`.

`artifacts.json` schema 1.0 specifies native (`.FCStd`/`.blend`), GLB preview, script, project units `mm`, `source_to_project`, `preview_to_project`, `bounding_box_project` (min/max vectors), objects (id/name), backend and reproducibility. Matrices are row-major affine 4x4; translation is indices 3,7,11. Project is right-handed Z-up. GLB is metres/Y-up. Use explicit conversion, never guess unit from coordinate magnitude or stretch imports to match an expected box.

FreeCAD example lives in `backend-examples/freecad/calibration.py`; Blender example in `backend-examples/blender/calibration.py`. Supply the core Python module path to backend execution without modifying its bundled Python. Source/script/dependency snapshots must be inside workspace before publication. Preserve native CAD, not just tessellated mesh. Object hints are optional but useful; triangle numbers identify only that exact preview hash.

The GLB checker supports uncompressed static triangles. Sparse, compressed, morph or skinned geometry is rejected for checking rather than silently flattened. Viewer support does not automatically confer editability or rebuildability.
