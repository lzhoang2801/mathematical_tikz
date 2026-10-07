# TikZ reference comparison v2: development demo

The evaluator, cases, and run artifacts live in `problem_tikz`. The command below uses MathPaper's existing Python environment and shared TikZ wrapper/compiler integration; it does not run dataset selection or evaluation from MathPaper. The compiler service must be ready on localhost port 18080.

The comparator receives only `target_tikz` and `output_tikz`. Instructions, source crops, and current TikZ are retained for human context in the review page; they do not enter the score. The target remains an unapproved candidate, and a match does not establish that it satisfies the source exercise or all selected givens.

`docs/dataset-selection/tikz-pair-demo.jsonl` contains 17 development controls derived from three existing candidates: identity pairs and controlled mutations. Their `expected_status` and `expected_checks` are developer-declared expectations used to report per-case disagreements. They are not independent human judgments or an accuracy estimate. Same-source variants remain grouped; there is no held-out claim.

## Run from the problem_tikz root

```powershell
../mathmath/.venv/Scripts/python.exe -B -m evaluation.run --cases docs/dataset-selection/tikz-pair-demo.jsonl --output runs/tikz-evaluation-v4/controls --check
```

The evaluator compiles the original TikZ through the shared HTTP compiler, uses the returned uninstrumented PDF for path/text measurements, and saves evidence and a preview under the requested output directory. The report contains the evaluator/toolchain profile, observations, controlled-case expectations, and any disagreements. `--check` exits nonzero when an expected status or check disagrees. No model or Jev call is made. Use a fresh output directory if the compiler/observer/wrapper profile has changed.

## Evidence and checks

A second, non-painting discovery compile records executed PGF coordinates, nodes, and standard angle-library `\pic` metadata. Its measurements are accepted only when the toolchain matches and its rendered PNG bytes equal the original render. The comparator binds visible point labels to uniquely containing instrumented PGF nodes and their coordinate attachments; filled point dots are optional and are not required. Missing or ambiguous label/node bindings remain unknown rather than being guessed. The report retains the original PDF path and artifacts used for the visual checks.

| Check | Evidence | Limit |
| --- | --- | --- |
| `compile` | Original target/output compile result | A compile failure is explicit; service or extraction uncertainty is not a semantic pass. |
| `point_geometry` | Labeled point coordinates: each configuration's pairwise distance matrix is normalized by its own diameter; compares absolute normalized distances, local log ratios, shared-vertex angles, and direction angles for every nondegenerate pair of labeled segments | Translation, rotation, uniform scale, and reflection preserve these proportions/angles. Missing, ambiguous, degenerate, or uncertain observations can make the check unknown. |
| `orientation` | Chirality from similarity alignment, reported separately from point geometry | A reflection can match distance/angle geometry while differing in orientation. Collinear point sets have no planar chirality. |
| `annotations` | Executed standard `angles`-library angle/right-angle `\pic` anchors and softpaths, uniquely matched to painted paths in the original PDF | A local positive glyph-scale normalization is applied only to a uniquely matched standard annotation with aligned anchors. Its vertex, wedge, and painted presence still must match. Hand-drawn glyphs and arrow tips have no such local scale normalization; they are assessed only as emitted paths/fills. |
| `strokes`, `fills` | Actual paths and filled regions extracted from the uninstrumented PDF; symmetric coverage in both directions, with short path components checked separately | Unsupported clips/complex fills and path-extraction problems remain limitations or unknown evidence. |
| `text` | Visible PDF text inventory | No semantic reading or measurement-to-segment assignment. |
| `point_markers` | Executed empty-circle-node path dimensions, matched to emitted fills; dot count/positions as `observed` diagnostics | Optional glyphs; omitted from pass/fail expectations. |
| `visibility` | Sampled raster color support along reference paths | Screening, not proof of exact compositing. |
| `readability` | Native font outlines intersected with painted stroke areas; text/glyph overlaps and clipping | A collision screen only. Unresolved glyphs retain an explicit bounding-box fallback and cannot certify no new warning. Dash gaps, exact compositing, human legibility, and numeric-label attachment are not certified. |

Defaults are experimental: absolute normalized-distance tolerance `0.005`; local pair-ratio log tolerance `0.02`; angular tolerance `1°`; path tolerance `0.006` of the reference extent; coverage minimum `0.985`. For each path component, the effective tolerance is the lesser of the global path tolerance and `max(0.02 pt, 2% of component length)`. Only uniquely identified standard angle `\pic` glyphs receive their own local positive scale normalization. Manual marks and arrow-tip scale are outside that policy. These settings have not been calibrated against independent human judgments or held-out data.

Readability uses native PyMuPDF glyph paths, with contours flattened to `0.08 PDF pt` and a `0.02 square PDF pt` intersection threshold. These are experimental screening tolerances. The open space inside a glyph bounding box is not glyph ink. Circle-node path dimensions are captured after outer separation and matched to the original PDF; invisible node padding cannot justify treating a real circle as an optional point marker.

Aggregate `match` means measured checks agree; `different` means a supported check found a difference; `unknown` means required evidence is unresolved or unsupported; `review` is a screening warning, not a human judgment. These statuses apply to comparison with this target only.

This is reference-proportion fidelity, not full mathematical or task correctness. The evaluator does not compare the image with its source statement or verify every selected problem condition. It can preserve an inaccurate target, accept a diagram that omits an instruction-specific condition absent from the target, or flag another valid construction. `unknown` means required evidence could not be established; it must not be interpreted as a pass. The numeric-label relocation control also does not test whether a label is attached to the right segment, and the local B perturbation is not a calibrated near-threshold angular test.

## Geometry and readability are independent

A point-distance matrix describes the labeled point configuration; it does not establish that every required curve or edge was painted correctly. In `pair-demo-edit-uniform-scale-2`, all labeled point proportions match but the circumcircle is too large relative to those points. The emitted-path comparison must reject this defect even if every label is perfectly readable. Any collision with H is an additional readability finding, not the basis for rejecting the circle geometry.

A read-only audit of the saved `demo/review.json` PDFs identified the dashed circle as path 6 on both sides. Under the saved labeled-point alignment, its radius changes from about `49.09 pt` to `98.18 pt`, while the point-configuration diameter is `196.39 pt`. Target C, D, and E lie within `0.006 pt` of the actual cubic curve; each output point misses the aligned output circle by about `49.09 pt` (approximately `0.25` of that diameter). Both directions of path-6 coverage are zero. These normalized residuals demonstrate an incidence failure independently of the collision screen.

The original developer expectations remain unchanged. In particular, disagreements in the oversized-circle readability annotation and anisotropic arrowhead fill annotation are retained in the report; they must not be silently relabeled after observing the run.

## Recorded local run: 2026-10-03

The final [report](../runs/tikz-evaluation-v2/final/report.json) and [visual review](../runs/tikz-evaluation-v2/final/preview.html) contain 17 compiled controls from three source groups. All nine declared equivalent pairs have aggregate `match`; all eight declared defect pairs have aggregate `different`. This is agreement on developer controls, not a held-out accuracy measurement.

Two original per-check expectations still disagree: the oversized-circle case produces `readability=review`, and anisotropic stretch produces `fills=different`. Their overall expected outcomes are unchanged and both defects are rejected. Accordingly, `--check` exits 1; this run must not be described as having no control disagreements. The source manifest hash matches the initial run. No expected values were revised.

The final run stores compiler artifacts and hashes, executed-point and node evidence, per-check residuals, the Python/dependency versions, and copies of every scoring module with verified hashes. Reports from before the inferred-space fix remain under `before-space-fix-*` in the same directory. Earlier discovery failures remain in `runs/tikz-evaluation-v2/demo/initial-*`.

Functional verification: 43 tests passed, including omitted point dots, label reflow, label collision, circle/fill preservation, missing short strokes, right-angle annotation resizing/wedges, reflection policy, ambiguous bindings, tiny disjoint-segment angle changes, native C aperture/stem outlines, and inferred spaces. Scoped Ruff and `git diff --check` passed. No formatter or live model/judge call was run. The five approved MathPaper restoration files match their recorded restoration hashes; new evaluation work remains in this repository.

## Before routine evaluation

The [evaluation implementation](evaluation.md) now returns numeric measurements and four dimension results alongside the existing checks in one report. `evaluation.run --report runs/tikz-evaluation-v3/final/report.json --output runs/tikz-evaluation-v4/verified` re-evaluates the verified original artifacts offline. Source groups, task boundaries, incomplete evidence and original control expectations remain explicit.

Review target/instruction/source alignment, then calibrate the checks with independent human judgments, source-disjoint variants, naturally occurring errors, and valid alternatives. Report false accepts/rejects and unknown coverage only after that review. This 17-case development set is not such an evaluation.
