# TikZ evaluation

`evaluate(target_tikz, output_tikz)` returns four deterministic scores for supported Generate, Edit and Reconstruct pairs. The target defines observed geometric relations and required content. No LLM judge, per-case rubric or diagram-type selector enters scoring. Ordinary coordinate constants do not identify which lengths or angles an instruction prescribed.

## Method

1. Compile both TikZ inputs with the shared wrapper/compiler.
2. Observe native PGF constructors, painted paths, graphics state, node attachments and unpadded TeX text boxes in that compilation. Use one native coordinate frame: TeX points, y upwards.
3. Measure output readability independently; compare canonical target relations and content. Preserve completed metrics if another measurement is unavailable.

Separating geometric representation from deterministic checks follows [DiagramIR (Kumar et al., 2025), section 2.3](https://arxiv.org/html/2511.08283v1#S2.SS3). Here the observations come from executed PGF. The [PGF system interface](https://tikz.dev/pgfsys-commands) supplies path operations, canvas transforms, clipping, stroke state and synchronized text boxes; no source-coordinate parser or PDF extractor supplies scores.

## Metrics

| Metric | Score |
| --- | --- |
| **Compile** | `1` if the output validates and compiles; otherwise `0`. Dataset compile rate is the mean. |
| **Mathematical correctness** | Percentage of passed canonical target relation units; detected false or unresolved output relation marks add failed units. |
| **Content coverage** | Percentage of target point identities, maximal connections, circles, arcs, marked angles and segment-equality classes present. Connections and curves retain their solid/dashed style. Extra or unsupported objects and extra mark classes add failed units. |
| **Visual readability** | Percentage of output text nodes whose measured native text boxes clear other text boxes and painted paths, without clipping. Count each affected label once; exclude bar-only equality marks. |

Missing output evidence fails the corresponding unit; it never shrinks the target denominator. Failed output compilation gives four zeros. Unavailable measurements raise `EvaluationError` with `.scores` retaining established results and `None` only for unavailable metrics. In particular, unresolved output text-box or paint measurements make readability unavailable, not zero; measured compile, mathematics and coverage remain available. `EvaluationInfrastructureError` likewise retains completed scores and stops batch processing. These errors are evaluator availability failures, not invented model scores. No mathematical/content units gives 0; no scored text gives 100.

Degeneracy is checked within each relation: a zero-length midpoint segment or angle arm fails that requirement. Free auxiliary points may coincide or cross an incidental line without invalidating unrelated requirements. Observed target coincidences form one unit per set. A scene with no extracted relations has one unit for point presence and configuration dimension. Unrelated distinct points cannot dilute a broken relation. The percentage measures supported checks, not the probability of full problem correctness.

## Geometric relations

| Target observation | Output requirement |
| --- | --- |
| Maximal named line | One unit for collinearity and observed strict interior containment in painted segments, regardless of path splitting. Free feet can change order relative to other interior points. |
| Observed midpoint | One unit per midpoint and its endpoint pair; generic division ratios stay free. |
| Parallel painted carriers | One unit per direction group; one additional unit per observed equal-vector group. |
| Square corner mark | One perpendicularity unit per identified marked angle. |
| Matching segment ticks | One equal-length unit per class of marked named segments. |
| Full circle | One unit containing detected center, boundary, radius-segment and tangent relations. |
| Circular arc | Circle relations restricted to the painted interval, plus named endpoints and boundary-point order, allowing reversed traversal and reflection. Minor/semicircle/major branch class is retained; interior angular fractions remain free. |

Native circle/ellipse and arc constructors supply centers, axes and signed intervals. These facts bind to the exact cubics PGF paints, including saved paths and repeated uses. A transformed pair of equal, perpendicular axes identifies a circle; nonuniform deformation is not normalized away. A stroked boundary remains a mathematical object whether or not the path is also filled. Construction without paint contributes no object.

Co-circular intervals of the same style merge, so splitting or repainting a circular path does not change its units. Native short arcs have no 15-degree cutoff. Arcs still need named endpoints for mathematical matching. Unattributed cubic paths use the existing bounded circular-path fit; its short-arc ambiguity remains unsupported. Circles/arcs share one-to-one matching, bounded to 12 target and 12 output objects. Native arrow invocations identify arrow decorations independently of their shape; those decorations retain their painted support for readability.

These measurements use executed PGF geometry. The observer does not re-evaluate source coordinate expressions or infer constructor identity from TikZ text. Python checks geometric predicates and measured support after PGF resolves the drawing. Non-circular curves remain unsupported for mathematics instead of being silently omitted.

Relation-mark presence and mathematical truth are separate. Omitting ticks from equal segments loses coverage while their equal lengths can still pass mathematics. A visibly oblique corner mark can satisfy presence while failing perpendicularity. Matching tick classes use their segment membership, so consistently swapping single/double ticks or using short vector strokes instead of bar glyphs preserves credit. Native text-box orientation and placement, or a vector stroke crossing its carrier, must support each attachment. At subdivided sides, the shortest interval centered on the mark takes precedence; remaining ambiguity makes a reference unavailable and adds failed units for an output. Contradictory reference marks also make mathematics/coverage unavailable. This attachment convention cannot recover a different intended scope from visually identical paint.

The authoring gate in `evaluation/requirements.py` uses this same mark observer. Its explicit source requirements remain independent of the target/output scorer. Legs of a recognized corner are excluded from vector-tick detection, including where they cross a diagonal. Equal-angle arcs and printed angle values have separate authoring checks; they are not recovered as metric constraints by this scorer. A 180-degree collapsed corner can paint the same line as an ordinary segment, so its intended command is not identifiable from geometric evidence. Missing required corners are still detected.

For spatial **authoring**, `check_scene` accepts a solved XYZ witness and its declared projected coordinates. The observed PGF points must match that projection, allowing translation only (maximum 0.15 TeX point residual). A missing or failed binding holds the case and leaves world facts unverified. Bound XYZ coordinates check lengths, angles, plane membership and directed vectors; the PGF trace supplies painted carriers, arrow direction, marks and readability. An oblique corner can therefore denote a true world right angle. These XYZ inputs are not part of `evaluate(target_tikz, output_tikz)`: that scorer cannot establish general 3D metric truth from a projection and may withhold mathematics for spatial reference marks that contradict screen-space angles. Do not report such unavailable scores as model failures or claim that authoring support makes spatial model evaluation complete.

## Native observations and readability

Successful ordinary evaluation needs a complete compiler receipt and PGF log, with no returned PDF or raster. Each distinct input is instrumented once using the shared wrapper/compiler. If instrumentation fails to compile, a plain compile distinguishes a failed hook from an actual output compile failure. A missing, truncated, malformed or modified trace cannot earn geometry credit.

The observer preserves PGF's construction, buffering and insertion lifecycle. Cached native protocols are recorded at each invocation; unused definitions contribute no paint. Deferred TeX write markers order graphics scopes, transforms, clipping, opacity, path use and text boxes at shipout. This matters for inline nodes, which TikZ can construct before a path and insert afterward. A completion marker certifies that shipout evidence finished. Geometry and paint state are then read in this native order. Visible mathematical labels bind to their executed attachment points; internal coordinate names are not extra content, and duplicate visible identities stay unresolved.

Geometry uses continuous centerlines for dashed carriers; readability uses their painted dash fragments. Fill and stroke are independent paint components. An earlier fill is background; a later opaque fill masks earlier strokes and can cover text. A text node's own border/background is excluded by occurrence identity. Native insertion order also determines inherited opacity and clipping, including `behind path` nodes and explicit node opacity overrides.

Text is measured from `pgfsys@hboxsynced`, without padded node bounds or a guessed font fallback. Text boxes are conservative clearance regions: they do **not** establish glyph-ink collisions, glyph holes, kerning, or color contrast. A box overlap can penalize a visually legible label. Paint curves are flattened to 0.01 TeX pt; overlap is counted above 0.02 square TeX pt. Partial-opacity overlap is conservative; arbitrary blends, patterns, shading, fading and transparency groups are not certified. Hairlines, unsupported paint operations and unavailable boxes withhold readability rather than fabricate a score.

The optional preview requests PNGs during the same compile and embeds them alongside both TikZ inputs. Raster failure does not remove PGF-based scores. The shared compiler service still builds PDF internally: `Outputs(pdf=False)` removes the returned PDF, not the engine's PDF generation. This migration establishes PDF-independent **measurement**, not a compiler latency or model-quality improvement. Native observation caches bind `tikz-observations:pgf-v2` and the exact tracer SHA-256; old PDF observations or changed hooks require recompilation in a new run directory. Frozen study evidence is not rewritten.

## Mathematical basis

For correctly bound observations $X$ and target predicates $R_T$, define

$$
\mathcal S_T=\{X:\;r(X)=\mathrm{true}\text{ for every }r\in R_T\}.
$$

This solution set can contain multiple nonsimilar drawings. Free points, dependent points and constraints also underpin [GeoLoom (Wei et al., v2), section 4.2](https://arxiv.org/html/2512.08180v2#S4.SS2). Our predicates are extracted from the target; the proofs below establish exact geometric preservation, while the implementation tests numerical approximations.

**1. 2D coordinate freedom.** For $f(P)=sQP+t$, $s>0$ and $Q^\top Q=I$,

$$
\|f(P)-f(C)\|=s\|P-C\|,
\qquad (sQu)\cdot(sQv)=s^2(u\cdot v).
$$

Distance ratios, perpendicularity, circles and tangency are preserved. Thus translation, rotation, reflection and uniform scale preserve the checked relations. General affine transforms preserve affine dependencies, but can turn circles into ellipses and change right angles.

**2. Different 2D constructions, same relations.** Take $A=(0,0)$, $B=(0,h)$, $C=(b,0)$ with $b,h>0$, and $q=b^2+h^2$. Define

$$
M=(b/2,0),\quad N=(b/2,h/2),\quad
H=(bh^2/q,hb^2/q),\quad r=b/2.
$$

Substitution gives

$$
\begin{aligned}
2M&=A+C,\quad 2N=B+C,\quad H=B+\tfrac{h^2}{q}(C-B),\\
(H-A)\cdot(C-B)&=0,\qquad \|C-M\|=r.
\end{aligned}
$$

Changing $b/h$ changes the triangle's shape while preserving these midpoints, the altitude and circle $(C,CM)$. Full credit remains conditional on the other extracted relations and nondegeneracy guards. This proves why a single global similarity is unnecessarily restrictive.

**3. 3D dependencies can be checked in their 2D projection.** Let $P_i\in\mathbb R^3$ and $p_i=\pi(P_i)=LP_i+t$, with $L\in\mathbb R^{2\times3}$ of rank 2. For any affine combination,

$$
\pi\!\left(\sum_i\alpha_iP_i\right)
=\sum_i\alpha_i\pi(P_i),\qquad \sum_i\alpha_i=1.
$$

Proof: distribute $L$ and use $(\sum_i\alpha_i)t=t$. Midpoints, incidence, segment membership and equal-vector/parallel dependencies therefore survive when the relevant objects do not collapse. The linear orthographic special case is documented by [Tomasi and Kanade (1992), section 3.1, equation 9](https://cs.brown.edu/courses/cs143/2011/proj5/Tomasi_Kanade_IJCV_1992.pdf#page=4).

For the prism, take projected $A,B,C,d\in\mathbb R^2$ and set

$$
\begin{aligned}
A'&=A+d,\quad B'=B+d,\quad C'=C+d,\\
M&=B+\tfrac12d,\quad N=C+\tfrac12d,\\
H&=2B-A,\quad K=2C-A.
\end{aligned}
$$

Then $2M=B+B'=A'+H$, $2N=C+C'=A'+K$, $B'-A'=B-A$, and $C'-A'=C-A$. These identities hold for changing free points. Moreover,

$$
\Phi(x,y,z)=A+x(B-A)+y(C-A)+zd
$$

maps the canonical 3D prism with base $(0,e_1,e_2)$ and translation $e_3$ exactly to these projected vertices and dependencies. This supplies a 3D realization of this dependency system without requiring XYZ input to the evaluator.

**Boundary.** Projection is not invertible: for $v\ne0$ in $\ker L$, $\pi(P+v)=\pi(P)$. Consequently, projected checks certify the observed dependencies, not arbitrary spatial lengths, angles or hidden incidence; perspective projections also need different invariants. These derivations and cited methods do not prove extractor accuracy or score calibration. Target-inferred relations can be incidental to the original problem.

Changing $(C,CM)$ to $(C,CN)$ affects mathematics when the radii differ; deleting MN affects coverage; label collisions affect readability. Printed measurement text is not parsed as a mathematical requirement.

## Use and scope

```powershell
python -m evaluation.run --target target.tex --output output.tex --preview preview.html
```

The optional preview contains both renders, scores and TikZ sources. It is also saved on a measurement error with completed scores and the diagnostic; the CLI then exits with status 1. Supported evaluations print the same four-score JSON object as before. Set `COMPILER_URL` for the shared compiler; default: `http://127.0.0.1:18080`.

For the Colab notebook, export all validation/test predictions as JSONL, then run the batch adapter in the existing evaluation Python environment:

```powershell
..\mathmath\.venv\Scripts\python.exe -B -m evaluation.batch --predictions predictions-test.jsonl --results scores-test.jsonl
```

Each input row contains `task` (`reconstruct`, `generate`, or `edit`), exact `target_tikz` and `output_tikz` strings; `id`, `split` and `row_index` are retained in results. Repeated IDs remain separate rows. The notebook also records the dataset revision. The evaluator accepts source comments and leading declarations of libraries already provided by the shared wrapper; compilation preserves their original source. Document wrappers, surrounding prose and unsafe TeX are still rejected.

The batch writes one result per processed row and a sibling `*.summary.json` with overall and per-task means. Output compile failures contribute zero. Measurement errors retain partial score dictionaries; invalid input records have no scores. Each metric's mean uses its own `scored_by_metric` denominator, including available results from partial rows. `scored` counts rows with all four completed metrics. Error counts remain explicit. Compiler infrastructure errors stop processing and leave a partial report; pending rows are counted. Existing results are not overwritten. Exit status is 1 for errors or incomplete evaluation. Use validation for iteration and reserve test for the final checkpoint; token validation loss is separate from these diagram metrics.

Supported observations: labeled points, straight solid/dashed segments, full circles, circular arcs with named endpoints, corner marks and segment-equality ticks with resolved carriers. Gxx labels do not select scoring logic. General conics/curves, filled regions, custom relation symbols and unmarked metric givens are outside the implemented mathematical checks. An unrecognized curve does not itself withhold readability credit: its measured painted support still participates in clearance checks. **100% means all supported extracted checks passed**, not that unstated problem requirements were proved.

Before model comparisons, validate a reference by evaluating it against itself, then calibrate it with valid reconstructions and deliberate violations. The semicircle regression allows changing M/P while preserving intersections, tangency and arc order; negative controls move a point off the arc, swap its order, choose the opposite half, remove the arc or alter its radius. Existing controls retain uniform-scale/rotation/reflection invariance, projected prism dependencies, the CM/CN radius distinction, missing connections and label collisions. Fixed lengths or angles known only from the original instruction remain an independent target-curation requirement; this evaluator does not recover them from arbitrary coordinate constants.

Implementation: [evaluator](../evaluation/evaluator.py), [PGF observer](../evaluation/tikz_pgf.py), [trusted hooks](../evaluation/pgf_trace.tex), [geometry](../evaluation/tikz_geometry.py), [relation marks](../evaluation/tikz_marks.py), [coverage](../evaluation/tikz_coverage.py), [readability](../evaluation/tikz_readability.py). Regression tests cover valid transformations/reconstructions, missing content, broken relations and label collisions under [tests/evaluation](../tests/evaluation/).

[Research report and evaluation derivations](report.tex).
