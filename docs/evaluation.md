# Evaluation methodology

This document describes the implemented method in [evaluator.py](../evaluation/evaluator.py) (`tikz-evaluation:v7`). It evaluates mathematical diagrams for grades 6–12 through four dimensions: **Compile rate, Mathematical correctness, Content coverage, and Visual readability**. Each result reports measurements, executable checks, evidence and unresolved limitations; there is no weighted overall quality score.

## 1. Evaluation contract

| Task | Model input | Evaluation reference |
| --- | --- | --- |
| Generate | Self-contained mathematical givens and drawing scope | Reviewed `target_tikz` |
| Edit | `current_tikz` and mathematical edit instruction | Reviewed completed `target_tikz`, including preserved content |
| Reconstruct | Diagram crop and instruction | Reviewed `target_tikz` aligned with the crop |

Before evaluating outputs, review and freeze the instruction, target and minimal `evaluation_rubric` together. The rubric specifies mandatory mathematical relationships as executable predicates; shared checks handle compilation, rendered content and collisions. Givens describe mathematical definitions and conditions, while the drawing scope identifies the objects and information that must be visible. Proof goals are not assumed. Targets and rubrics remain outside generation inputs.

The evaluator measures **reference fidelity plus supplied mathematical requirements**. A target is a reviewed example, not an oracle established by compilation. Output and target predicates are evaluated independently: agreement with an erroneous target cannot turn a failed predicate into a pass. Conversely, a valid configuration allowed by the instruction may differ from the target; the current comparator does not recognize all such alternatives.

The methodological precedent is separating observations from executable checks, as in [DiagramIR, §§2.2–2.3](https://arxiv.org/html/2511.08283v1). Here observations come from executed PGF and the original PDF rather than model-generated IR. DiagramIR's schema, heuristic correspondences and aggregate Boolean score are not adopted.

## 2. Evidence acquisition

The shared MathPaper validator, wrapper and compiler produce the original PDF, PNG and diagnostic log. One additional non-painting PGF probe records executed label attachments and standard angle-mark anchors and paths. Probe evidence is accepted only when compilation succeeds, the toolchain matches, the log is complete and the PNG bytes equal the original render.

Executed PGF positions are mapped into the original PDF coordinate frame. A mathematical point is identified by its visible point label and resolved attachment, independently of where its glyph is placed. Point dots are optional; undrawn helper coordinates are not extra mathematical points. Duplicate or ambiguous labels remain unresolved.

PDF paths, text and native glyph outlines are captured and reused. [PyMuPDF's drawing API](https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_drawings) exposes vector paths and paint attributes, but path existence alone does not prove final visibility under clipping or compositing. Raster support therefore supplements vector evidence. Each distinct valid TikZ needs at most two compiler requests; verified saved observations can be rescored without compiler or model calls.

## 3. Four measurements

### Compile rate

For known output validation/compiler outcomes,

$$
C = 100\,\frac{N_{\mathrm{successful}}}
{N_{\mathrm{successful}}+N_{\mathrm{failed}}}.
$$

Upfront source rejection is a known failure. Transport failures or unavailable compiler evidence are counted separately. Compilation supplies execution evidence; mathematical and visual quality require the remaining checks.

### Mathematical correctness

For corresponding resolved labels, let $p_i^T,p_i^O$ be target and output points. Define each configuration's diameter and normalized pair distances:

$$
L^r=\max_{i<j}\|p_i^r-p_j^r\|,
\qquad
d_{ij}^r=\frac{\|p_i^r-p_j^r\|}{L^r},
\qquad r\in\{T,O\}.
$$

The evaluator compares every corresponding pair and reports

$$
E_d=\max_{i<j}|d_{ij}^O-d_{ij}^T|,
\qquad
E_{\log}=\max_{i<j}\left|\log d_{ij}^O-\log d_{ij}^T\right|.
$$

`point_distance_max_error` measures absolute proportional deviation; `point_ratio_max_log_error` measures reciprocal-symmetric relative deviation. Printed lengths are not required to equal physical canvas lengths. Normalization preserves ratios and removes translation, rotation and uniform scale. Reflection also preserves distances, so chirality is checked separately through point alignment; reflection is disallowed by default.

**Why complete distances are useful.** Let $S_{ij}=d_{ij}^2$ and $J=I-\mathbf1\mathbf1^\top/n$. The centered Gram matrix is $G=-JSJ/2$. Equal complete normalized distances therefore determine the same centered inner products and point configuration up to an orthogonal transformation. This is the classical distance-geometry result reviewed by [Dokmanić et al. (2015), §II](https://arxiv.org/abs/1502.07541). It justifies reference-shape comparison without enumerating every inferred angle.

Finite distance tolerances can still conceal a large angle change between very short segments. Required relations therefore receive direct checks from the frozen rubric. For nonzero segment vectors $u,v$, examples are

$$
r_\perp=\frac{|u\cdot v|}{\|u\|\|v\|},
\qquad
r_\parallel=\frac{|u_xv_y-u_yv_x|}{\|u\|\|v\|}.
$$

The implementation also checks equal lengths, length ratios, midpoint, collinearity, point order, circle membership, concyclicity, tangency and explicit distinctness. Each result retains residuals, tolerances, branch/order conditions and point evidence IDs. Geometric relations use measured coordinates; they do not establish that the corresponding support or symbol was drawn. Constraint-based evaluation alongside visual assessment is also used by [GeoLoom, §§5.1–5.2](https://arxiv.org/html/2512.08180v2).

The log expression applies to positive distances; coincident-point cases are handled separately. Numerical uncertainty crossing a distance threshold produces `unknown`. Missing/extra points are distinguished from unresolved correspondence. Zero distances and degenerate constructions receive explicit outcomes rather than artificial log floors.

### Content coverage

One best-fit similarity transform aligns output points and paths to the target. Paths sharing the same color, solid/dashed setting and opacity are unioned before measuring stroke length or fill area. Counterpart matching requires equal dash style and color/opacity differences below $0.05$. Stroke width is ungraded for content matching; its actual width still affects collision screening. For source groups $A_k$, compatible counterpart support $B_k$, tolerance neighborhood $B_k^\tau$, and measure $\mu$,

$$
\operatorname{coverage}(A\to B)
=100\,\frac{\sum_k\mu(A_k\cap B_k^\tau)}
{\sum_k\mu(A_k)}.
$$

Stroke coverage uses $\mu=\mathrm{length}$; fill coverage uses $\mu=\mathrm{area}$. Both directions are reported: target-to-output detects omissions, while output-to-target detects additions. A separate minimum component coverage prevents a missing short edge from disappearing inside a high total percentage. Splitting or repeating an identical PDF path does not increase its weight.

Rendered text is checked as a missing/extra inventory. Coverage measures painted reference content, not the fraction of instructional facts satisfied. An oversized circle can retain correct labeled points while failing path coverage.

Required relation marks belong in the reviewed target. Standard angle arcs and right-angle corners may change size when their executed anchors and sectors correspond; emitted paths still determine presence and placement. Equality ticks and other marks receive rendered-content evidence, but semantic assignment of tick patterns or arc counts to equality classes is not independently verified.

Raster visibility samples solid-stroke support. Dash cadence and phase are ungraded; dashed-path raster support is diagnostic, while missing dashed geometry remains subject to vector coverage.

### Visual readability

Let $G_\ell$ be a resolved label's native glyph ink and $S$ the union of strokes buffered by half their widths. The output collision measurement is

$$
I=100\,\frac{\sum_\ell\operatorname{area}(G_\ell\cap S)}
{\sum_\ell\operatorname{area}(G_\ell)}.
$$

`stroke_collision_ink_pct` reports intersecting ink area; `stroke_collision_label_pct` reports the fraction of resolved labels with screened collisions. Label/label overlaps, within-label glyph overlaps and clipped labels are counted separately.

Label movement is allowed when its mathematical attachment remains resolved and its placement remains readable. The readability dimension screens the **absolute output**; an existing collision in the target does not excuse it. New warnings relative to the target are separate diagnostics. Unresolved glyph outlines use bounding-box fallbacks for warnings and retain uncertainty. The screen does not certify label/fill collisions, dash gaps, final compositing or overall pedagogical usefulness.

## 4. Decisions and numerical policy

Checks report `match`, `different`, `unknown` or `review`. A definite difference dominates uncertainty; otherwise uncertainty dominates review. Rubric predicates report `pass`, `fail` or `unknown`: every check must pass for its criterion to pass, and every supplied criterion must pass for `instruction_requirements_status` to be `pass`. An empty rubric does not certify requirements. `target_requirements_status` reports the same predicates on the target independently.

The overall `status` combines reference checks and rubric results. It is not a certificate that all four dimensions passed: reference readability checks concern new warnings, while `dimensions.visual_readability` uses absolute output warnings. Read dimension results alongside `reference_status` and requirement statuses.

| Measurement/check | Current default |
| --- | --- |
| Normalized distance difference | $0.005$ |
| Absolute log distance ratio | $0.02$, directly in log units |
| Perpendicular/parallel residual | $\sin(1^\circ)$ |
| General relative predicate tolerance | $0.005$; ordering predicates retain separate bounds |
| Aggregate coverage neighborhood | $0.006L^T$ |
| Stroke component neighborhood | $\min(0.006L^T,\max(0.02\,\mathrm{pt},0.02\,\ell))$ |
| Minimum component coverage | $98.5\%$ |
| Screened ink intersection | $>0.02\,\mathrm{pt}^2$ |

These are implemented experimental defaults tested on development cases, not held-out calibrated standards. Curve and glyph flattening, label attachment and raster sampling also limit measurement precision.

## 5. Reporting and validity

[run.py](../evaluation/run.py) reports each task, system, split and control/model/candidate cohort separately. Every scheduled case remains in the counts, including generation failures and missing results. With $M$ matches, $D$ differences, $F$ known generation failures and $N$ scheduled cases,

$$
\mathrm{success}_{\mathrm{observed}}=100\,\frac{M}{M+D+F},
\qquad
\mathrm{determinate\ coverage}=100\,\frac{M+D+F}{N}.
$$

The frozen-requirement pass percentage is $100N_{\mathrm{requirements\ pass}}/N$. It describes the supplied executable requirements, not unrestricted mathematical accuracy. Always retain failure, unknown, review and unavailable counts alongside percentages.

Numeric metrics retain `observed`, `partial`, `unavailable` or `not_applicable` states and evidence counts. Observed means exclude partial/unavailable values while retaining their counts. To prevent augmentation from overweighting one source, the runner also averages within each source group and then equally across groups. Related givens and all their Generate/Edit/Reconstruct variants stay in one split.

Reproducibility records include frozen inputs/rubric hashes, original artifacts, toolchain identity, evaluator source snapshots and runtime versions. Cache reuse verifies input and artifact hashes. Development regressions cover valid similarity transforms, label movement, deliberate geometry/path errors, missing marks, wrong sectors, collisions and unsupported evidence. They establish software behavior; held-out human validation is still needed to estimate evaluator reliability.

Automatic semantic scope is currently measured **2D labeled-point geometry and explicit predicates**. Spatial truth cannot be inferred from a projection; algebraic semantics, absolute physical scale, complete equality-mark meaning and all instruction-allowed alternative configurations remain outside these checks. Complex fills, clipping/compositing and unsupported attachments can leave evidence unresolved. Source fidelity and target approval require independent review. These limits follow the same distinction between restricted observable correctness and full task validity acknowledged in [DiagramIR, §4](https://arxiv.org/html/2511.08283v1).
