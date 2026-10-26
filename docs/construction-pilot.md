# Construction pilot: real Generate tasks

The pilot tests whether a construction representation reduces expensive drawing
correction cycles while preserving mathematical facts, line roles and source
quality. All implementation changes are in `problem_tikz/src`; MathPaper is a
read-only upstream reference. No output is promoted to the training dataset.

## Experimental boundary

Two bounded methods use the copied native loop, fixed TikZ wrapper, the same
compiler service and CPA model (`gemini-3.8-flash-high`): native complete TikZ,
and a typed construction program emitted deterministically as complete TikZ.
There are two repetitions per case, interleaved with the arm order reversed.
Each drawing permits at most four model calls and four compiler HTTP requests;
provider retries are disabled. The model still sees the rendered image before
completion in both arms. This experiment does not remove that second-call floor.

The actual source is frozen under each run's `source_snapshot/`; protocol files
pin dependencies, source hashes, instructions, toolchain and configuration.
Targets, source checks and review records are never drawing inputs. All model
calls, tool failures, compiler requests and delivered outputs are retained.
Compiler counts include failed HTTP attempts, but exclude precompile validation
rejections. Calibration, offline scoring and assistant review are separate costs.

These measurements precede a common deterministic post-agent finalizer. No label
repair was run in either arm. The raw full-review counts therefore do not measure
the intended comparison after that cleanup, and label collisions alone cannot
establish that the construction method fails to preserve quality. A fair follow-up
must apply the same finalization policy to both arms, record its time and any extra
compiles separately, and assess the remaining mathematical and content failures.
No hypothetical repaired output is counted as a pass here.

The compiler was an isolated localhost instance of the already installed image.
The checked-out client schema differed from that image's digest schema; the exact
running schema was copied locally, with its hash recorded in `src/upstream.json`.
No MathPaper source or production container was modified.

## Planar result

Three real `dataset/synthetic_new/generate.jsonl` cases cover isosceles geometry,
two tangencies, and reflection/intersection (six drawings per arm).

| Measurement | Native TikZ | Planar construction |
| --- | ---: | ---: |
| Generation compiler requests | 11 | 6 |
| Actual model calls | 18 | 13 |
| Mean drawing time | 61.86 s | 35.33 s |
| Median drawing time | 63.07 s | 35.50 s |
| Mean model time per drawing | 50.23 s | 28.31 s |
| Mean compiler time per drawing | 11.46 s | 6.94 s |
| Current numerical relations pass | 6/6 | 6/6 |
| Independent visual/scope pass | 5/6 | 3/6 |
| Named-dependency contract pass | 5/6 | 0/6 |
| Raw full independent review pass | 5/6 | 0/6 |
| Drawing seconds per raw reviewed pass | 74.23 s | Unavailable: no passes |

Construction reduced compiler requests by 45.5% and mean drawing time by 42.9%.
All six construction outputs satisfy the checked numerical relations, but their
free-point operation lets the model replace required construction dependencies
with convenient coordinates. This fails the pinned source-encoding contract;
it is not evidence of six mathematically false diagrams. It does show that the
representation does not enforce the intended dependencies when free parameters
change. Parameter robustness was not tested in this run.

Separate content failures remain: one construction tangency omits both ray
arrowheads, and three reflection outputs across both methods introduce unjustified
dashes. Line d does not occlude anything in a planar reflection. One construction
reflection also has a label collision, recorded as downstream layout evidence.

The native isosceles repair introduced named dependencies that its first render
lacked. Its extra compile therefore partly purchased a required source correction.
Other native repairs removed duplicate strokes or adjusted marks/labels. A
construction-only compile reduction cannot be assumed to remove redundant work.
One construction invocation used an extra model call to repair a schema-rejected
prime in an internal identifier; one native invocation repaired forbidden source
comments. Neither rejection called the compiler.

The frozen executable checker reported 4/6 passes for each arm. Independent
review found two false negatives from requiring a right-angle mark in one
particular sector, and false positives from incomplete arrow/style checking.
The original scores are preserved; `independent-review.json` records the stricter
review and the user's line-role correction. One native tangency adds a dashed OM
auxiliary beyond the explicit scope; that addition is documented separately.
An existing reflection target also hardcodes M on d, so target acceptance alone
is not evidence of compliance with the newer named-dependency contract.

A compiler request itself was not faster: means were 6.25 s native and 6.94 s
construction (medians 4.76 s and 5.25 s), with substantial outliers. Model time
remains the dominant component. These are small, selected cases with two repeats,
not a general speed or quality estimate.

Planar evidence: `runs/construction-pilot-20261019/reviewed-summary.json`,
`protocol.json`, `calibration.json`, original per-drawing records and blind review.

## Spatial extension

Three additional real cases are frozen separately: tetrahedron thirds and two
parallel sections (`571c8b35-b2f8-5053-807a-5c8e1007f559`), a parallelogram-base
pyramid midpoint section (`5a39fb6d-a416-5713-a16f-c937952828db`), and a
parallelepiped centroid (`473b7bef-1a21-5627-9470-92259bb9199e`). Source audits
verified the current grade-11/12 corpus and target/image binding. The tetrahedron
target had prior deterministic fill removal; the pyramid instruction had prior
curation. These are curated examples, not untouched automatic successes.

The spatial tool realizes affine XYZ operations, validates cyclic faces of one
closed convex solid, selects a parallel camera from 24 candidates, and computes
segment visibility. A contained segment is visible when its relative interior
lies on a front face; a strictly interior segment is hidden under the shared
closed-solid convention. Auxiliary/derived status never decides its style.
Both arms receive exactly the same visibility convention. The native arm remains
free to express its diagram in ordinary 2D TikZ. Valid all-visible tetrahedra and
both consistent depth directions are accepted; dashes are never mandatory merely
because the problem is spatial.

The independent checker does not consume the tool's XYZ/camera witness. It fits
one affine map from four fixed PDF-observed anchors, tests all remaining vertices
and auxiliary points without refitting them, then tests both global depth
hypotheses against the source's face topology. It checks opposite-style overlays,
extra carriers, endpoint extents, missing edges and actual painted dash gaps for
label readability. Valid vector ticks and glyph ticks are both admitted.

Twenty-one calibration cases include real targets, valid transforms, an all-visible
view, vector ticks, wrong affine relations, inconsistent visibility, extra dashes,
missing segments and an intentionally crowded view. A separate clear-label
version of that crowded view passes. An inherited target warning was traced to
the shared evaluator buffering dashed paths as continuous lines; actual PDF paint
shows no collision. The pilot-specific readability check expands dash intervals.
Original shared four-metric scores remain separate and may retain this limitation.

| Measurement | Native TikZ | Spatial construction |
| --- | ---: | ---: |
| Generation compiler requests | 12 | 6 |
| Actual model calls | 22 | 12 |
| Mean drawing time | 79.94 s | 52.18 s |
| Median drawing time | 82.29 s | 44.14 s |
| Mean model time per drawing | 72.53 s | 48.20 s |
| Mean compiler time per drawing | 7.30 s | 3.84 s |
| Independent affine-mathematics review pass | 6/6 | 6/6 |
| Independent visibility review pass | 6/6 | 6/6 |
| Named-dependency contract pass | 6/6 | 6/6 |
| Independent readability pass | 3/6 | 0/6 |
| Raw full independent review pass | 3/6 | 0/6 |
| Drawing seconds per raw reviewed pass | 159.87 s | Unavailable: no passes |

Construction halved compiler requests and reduced mean drawing time by 34.7%.
All six construction outputs pass the independent affine-mathematics and
visibility review, including the measurement audit described below. Their raw
full-review count is 0/6 because all have label/stroke contacts; both construction
tetrahedra also omit the equality annotations required by the frozen pilot's
trisection coverage check. Those omissions do not make the numerical trisections
false. They concern the selected visible content, not a universal requirement to
mark every given relation.

The label contacts are real: the blind reviewer inspected painted strokes, not
continuous buffers across dash gaps. Five construction plans selected label
positions before the chosen view; the other used an insufficient incident-direction
heuristic. These are finalization defects, and should be handled deterministically
after the agent as the user specified. They do not justify making label placement
the research contribution or concluding that the construction method has no
quality-preserving speedup. Post-finalization quality and latency remain unmeasured.
The model self-accepted all six outputs, including the two with missing equality
annotations, so self-review did not enforce the frozen visible-content requirement.

The three reviewed native passes are the first tetrahedron and both
parallelepipeds. The second parallelepiped reached the four-call limit and was
returned as `usable_with_issues`, although its retained TikZ passed independent
review. Native had five precompile comment-policy rejections and one failed TeX
build; all are retained, and the failed compile is included in the count. Thus
not all model-call savings can be attributed to better mathematical construction.
Both arms still used the existing image-feedback loop.

Per-request compiler means were 3.65 s native and 3.84 s construction (medians
3.35 s and 4.09 s). Of the 27.75 s mean drawing-time difference, 3.46 s was compiler
time and 24.33 s was model time. No compiler-engine speedup was implemented.
The one 115.69 s construction pyramid run also shows why a one-compile result
is not necessarily a low-latency result.

The frozen checker still has a bounded optional-tick limitation: some justified
parallelepiped vector equality classes outside its whitelist can be rejected,
while equivalent glyph ticks can pass. No delivered parallelepiped in this run
contains equality ticks, so that gap does not change these results. Required
trisection vector/glyph ticks were calibrated. General optional-mark equivalence
needs further calibration before expanding the benchmark.

The shared target/output scores expose a separate evaluation limitation. For the
first parallelepiped outputs, mathematics is 12/13 = 92.31% because the target's
near-collinearity of B, D-prime and G becomes an inferred relation, although the
source does not require it and BD-prime is undrawn. The normalized target residual
is 0.003093 against a 0.005 tolerance; both valid output views exceed that tolerance.
The construction coverage is 19/27 = 70.37% because eight connections correctly
change visible/hidden style in its different camera. No geometric connection is
missing in that case. `shared-score-audit.json` records the exact units and styles.
These raw scores are retained; they do not replace source-affine and visibility
checks. Readability is a separate raw-output measurement.

The frozen source checker reports mathematical/visibility passes for 6/6 native
and 5/6 construction outputs. In the remaining construction tetrahedron, the
observer attaches both C and C1 to C's node because their label boxes overlap.
An independent audit of the executed C1 dot/label records fixes only that
measurement in memory: its affine residual drops from 19.18803 to 0.000292 PDF pt,
with the same fitted projection and all other observations unchanged. This is an
assisted measurement audit, recorded in `binding-audit.json`; the original failed
scores remain unchanged, and the output remains rejected for labels and missing
equality marks. The review rows above must not be read as 6/6 automatic checks.

Offline evaluation added 24 compiler requests and 645.91 s across the twelve
outputs, separate from 792.71 s of total generation. Calibration and assistant
review are additional. These costs rule out an end-to-end preparation speed claim.

Spatial evidence: `runs/spatial-pilot-20261019/protocol.json`, the immutable
per-drawing records, `independent-review.json`, and `reviewed-summary.json`.
Drawing time per raw reviewed pass counts all attempted drawing time, including
rejections; it excludes finalization, calibration, offline evaluation and assistant
review. It is not the total cost of preparing an approved training pair, or a
comparison of acceptable throughput after deterministic cleanup.

## Interpretation and limits

The central weakness is what remains under unchecked model control. The planar
schema accepts free coordinates for constrained points, arbitrary dashed flags,
segments with missing ray arrows, and omitted annotations. The executor checks
references, degeneracy and the truth of supplied marks; it does not know the
instruction and cannot reject a requirement the model never represented. Moving
these decisions from TikZ into typed JSON does not resolve instruction fidelity.
The extra image-feedback turn did not reliably detect the observed omissions.

The spatial executor moves more work into deterministic code: it validates a
closed convex boundary, applies a common projection, and derives visibility from
faces. That behavior succeeded in these three affine cases after the documented
measurement audit. The pilot has not established general mathematical reasoning,
reliable selection of free configurations, or faithful extraction of the required
objects and relations. No false spatial mathematics was demonstrated by this run.

The next research hypothesis is to make the instruction's objects, constraints,
construction dependencies and selected drawing content independently checkable,
then realize and search only the valid free geometry and view choices before
compiling. A self-consistent model plan is insufficient: missing or mistranslated
instruction requirements must still be detected. The experiment should test that
boundary with omitted relations, wrong branches and incorrect line roles, keeping
deterministic label cleanup as a common final step. The Spec First follow-up below implements and tests this intervention on the
same selected cases; it does not establish general instruction fidelity.

For synthetic preparation, a construction program can remain internal while the
training response stays complete TikZ. A speed claim must measure time and compile
requests per independently accepted pair after the same finalization, distinguish
automatic, model-assisted and manual repairs, and include rejected outputs. This
pilot made no post-hoc repairs to measured outputs. Its raw generation savings are
real; quality-preserving savings after finalization remain an open measurement.

The spatial checker establishes affine realizability only for these cases. It
does not recover 3D metric truth from an image or support nonconvex/open/transparent
solids, external segments, curved surfaces or arbitrary occlusion. Labels and
source fidelity still receive independent review. No Edit/Reconstruct performance
or training improvement has been established.

## Spec First follow-up: execution contract

The user authorized a new implementation and paired pilot on the same six real
instructions. The model's only responsibility in this arm is instruction-to-spec
extraction. One structured call returns named objects, premises/definitions, branch
conditions and requested drawing scope. There is no model coordinate choice,
TikZ writing, camera choice, dash selection, rendered-image review or repair turn.
Schema or realization failures remain failed attempts, without an implicit retry.

`src/spec_first/spec.py` lowers supported relation patterns into the existing
named construction operations. Equal-distance loci become perpendicular-bisector
or internal-angle-bisector constructions; parallel sections become dependent
parallel-line/intersection constructions. It checks every supplied relation and
branch, searches 32 planar free configurations or 12 spatial configurations with
24 candidate views each, and selects projected point/carrier clearance before
compilation. Segment/ray/line objects determine extents and arrows. Closed-solid
faces determine spatial visibility; planar strokes are solid in this bounded
interface. Unsupported specifications and exhausted search are distinct from a
proof of mathematical inconsistency. No case ID selects a solution template.

The same native renderer, TikZ wrapper and compiler execute the selected source.
The baseline remains the current native image-feedback harness. This comparison
therefore measures the complete change in responsibilities, including removing
image-review model calls; it does not isolate an output-schema-only effect.
The model and compiler settings are pinned for both arms. The planned comparison had six cases, two repeats
and two arms (24 attempts), capped at 60 model calls and 60 generation
compiler requests in total, including abandoned/interrupted revisions: native at most four of each per attempt, Spec First
one extraction and at most one compile. Provider failures stop that run.

Primary acceptance checks source mathematics, drawing content/roles, and point/view
separation. Label placement remains a separate raw measurement; no hypothetical
label repair is counted. Visible equality and projection annotations retain the
pilot's disclosed presentation policy, not a requirement to mark every fact.
An independent spec/output audit must detect missing or mistranslated instruction
requirements: a self-consistent extracted spec alone is not a source-fidelity pass.
Hand-authored specification controls are calibration only and never worker inputs.
Targets, previous solutions and case-specific checks remain outside extraction.
These selected development cases do not establish held-out generalization.

Implementation follows the existing geometric executors and [PGF coordinate
calculations](https://tikz.dev/tikz-coordinates#sec-13.5). The extraction boundary
uses [LangChain structured model output](https://docs.langchain.com/oss/python/langchain/models#structured-output)
with Pydantic validation and retained raw responses; installed `langchain-openai`
1.6.3 supports `method="function_calling", include_raw=True`. The remainder is a
normal deterministic function, with a Runnable boundary only for the existing
tracing/callback recorder. No new agent graph or solver dependency was added.

## Spec First follow-up: measured results

The completed comparison contains six planar pairs (three instructions, two
repeats) and one pair for each of the three spatial instructions. All use the
same pinned CPA model configuration. No generated output was manually repaired,
model-repaired, or passed through a label finalizer in the Spec First arm.

| Completed pairs | Model calls, native / Spec First | Generation compiles, native / Spec First | Drawing seconds, native / Spec First |
| --- | ---: | ---: | ---: |
| Planar, 6 pairs | 18 / 6 | 11 / 6 | **70.70 / 20.62 mean** |
| Tetrahedron, 1 pair | 3 / 1 | 2 / 1 | **83.51 / 17.60** |
| Pyramid, 1 pair | 2 / 1 | 1 / 1 | **57.08 / 27.70** |
| Parallelepiped, 1 fresh pair | 4 / 1 | 3 / 1 | **121.86 / 19.14** |

The planar drawing mean fell 70.8%, with 45.5% fewer compiler requests. Most of
the time difference is model time: 57.12 versus 14.43 s per drawing; compiler
HTTP time was 13.39 versus 5.88 s per drawing. Precompile deterministic
realization averaged 0.217 s for planar outputs and took 1.80, 2.91 and 1.94 s
for the three paired spatial outputs. These are generation savings, including
removal of image-review calls. No LaTeX engine speedup was implemented.

Independent source/specification and original-PNG audits accepted mathematical
content and stroke roles in **6/6 planar Spec First outputs versus 5/6 native**,
and **3/3 paired spatial outputs in each arm**. The native planar rejection is
a required MB-prime segment drawn dashed without an occluder. All evaluated
planar outputs pass the numerical mathematical checks; stroke roles are a
separate acceptance condition. Planar drawing seconds per independently
reviewed mathematics/content pass, including the rejected drawing's cost, are
84.84 native and 20.62 Spec First. This is not time per fully approved training
pair: offline evaluation, calibration, review and any common finalization are
additional costs.

The source audit checks definitions independently of numerical truth. The native
tetrahedron repeats section fractions instead of deriving the other section
points from A1/A2; native reflection outputs use a literal point on a horizontal
carrier. Those are dependency-contract defects, not demonstrated false current
mathematics. Spec First preserves the dependencies: section points come from
parallel-line intersections, I is MP intersect NQ without assuming it is the
midpoint of SO, and the box centroid comes from a median construction. Source
organization and duplicate-painting defects are recorded separately.

Full readability is not solved. The Spec First tetrahedron has an equality tick
crossing another stroke, and the pyramid has glyph/stroke interference; both
retain valid mathematical geometry and visibility. The frozen numerical
readability checks miss the tetrahedron's visual issue. The fresh box pair is
visually clear in both arms. These outputs were not promoted to training targets.

### Interrupted runs and compiler cohorts

An initial integration revision spent 10 model calls and 5 compiler requests.
Two Spec First responses contained valid complete JSON but no structured tool
call; they were rejected at the transport boundary. The revision was stopped,
retaining those failures and an interrupted native attempt. The only extraction
change was a strict complete-JSON transport decoder with the same Pydantic
schema; it does not extract JSON from prose, repair incomplete responses or
make another model call. The new paired revision started from fresh attempts.

During the spatial revision the pinned Docker worker image disappeared. The
compiler then returned HTTP 503. That revision contains five delivered outputs,
three undelivered infrastructure failures and one interrupted attempt, with
three planned jobs unstarted. Its two healthy complete pairs are the tetrahedron
and pyramid. The earlier native box output remains as an unpaired result.
Undelivered attempts have no mathematical verdict; old raw records containing
`mathematics_pass: false` alongside `status: unavailable` are retained but must
not be interpreted as mathematical failures.

The fresh box pair used a replacement worker after all six box calibration
controls passed on it. Its paired timings are valid within that cohort, but it
is not pooled as if the entire spatial suite used one compiler. The generation
worker hashes are `44fc6e80...` for planar/tetrahedron/pyramid and `c485d8e4...`
for the fresh box pair. The incomplete second spatial repetitions were not
silently filled in. Total expenditure across all four revisions is **55 model
calls and 36 generation compiler requests**, including the abandoned and failed
work, within the aggregate 60/60 caps.

### Independent checks, raw scores and measurement limits

The frozen planar executable primary checker reports 6/6 Spec First and 4/6
native passes. Independent review identifies one additional valid native output:
the original-PDF Stealth arrowheads use an implicit closing edge that the frozen
arrow detector misses. A saved-PDF replay verifies both heads without changing
the output. This is an assisted measurement audit, not a fifth automatic pass.
The checker was fixed after the run with explicit/implicit-closure controls;
original observations and scores remain unchanged.

All six outputs in the three healthy spatial pairs pass the executable affine
mathematics/content/visibility checks. Raw all-check acceptance, including glyph
placement, is 2/3 Spec First and 1/3 native; visual review still finds the separate
tetrahedron tick issue noted above.

Shared target/output scores remain available alongside these source checks:

- Four isosceles outputs retain null shared mathematics and coverage because the
  frozen reference has arc endpoints that the shared observer cannot bind.
  Compile and readability scores remain available.
- Reflection Spec First coverage is 75% because optional reference content is
  absent, while required source content passes.
- The Spec First pyramid's 67.86% coverage includes seven correct changes of
  visible/hidden style for its different view and omission of two optional base
  diagonals. No required connection is missing.
- The fresh Spec First box scores 12/13 (92.31%) shared mathematics because an
  accidental target-screen near-collinearity B, D-prime, G is inferred as a
  requirement. The normalized residual is 0.003093 in the target and 0.119852
  in the output against a 0.005 threshold; this is not a source relation.

Offline evaluation recompiles exact delivered TikZ on the replacement worker;
original generation PNGs were used for the separate visual review. Evaluation
added **38 compiler requests** across 19 delivered outputs and **790.62 s of
summed evaluation durations**, with two offline processes overlapping. This is
not serial wall time. Calibration and assistant audit time are additional and
were not included in a total preparation-throughput claim.

All 23 attempted revision-r2/r3 LangSmith roots are readable (12 planar, 9
interrupted-spatial, 2 fresh-box); the interrupted attempt is not relabeled
complete. After the run, the runner was hardened to stop before another model
call if compiler readiness or its pinned image changes, preserve unavailable
mathematics as null, and calculate completeness from the frozen job order.
These changes do not rewrite the measured attempts.

Evidence: `runs/spec-first-review-20261019/results.json`, `review-batch-*.json`,
`measurement-audits.json`, and `comparison.html`; each run retains its protocol,
raw responses, specification, construction witness, compiler records, original
output, offline evaluation and trace readback. The 31 frozen valid/mutated
controls and six independently constructed specification controls are calibration,
not successful model samples. The method remains a bounded constraint compiler
for these construction families: it has no general nonlinear solver, no proof
that extraction captured every premise, and no support for open/transparent or
nonconvex solids. That initial study did not test Edit, Reconstruct or held-out
generalization; see the follow-up below.

## Verification and tracing

The initial deterministic construction verification had 65 passing tests. Existing
mark tests passed separately (12). Lint passes with import-order formatting
excluded; `git diff --check` passes. No formatter was run.

The original planar process retained the old LangSmith key and hit its quota.
After explicit authorization, all 12 completed instructions/TikZ/timing/count
records were uploaded with the new key and verified readable. These are recovered
root audit records, not reconstructed child spans. Recovery made no model calls.
Spatial tracing used the new key from process startup; all 12 original graph
traces were verified readable. The recovered planar roots and spatial graph
traces remain distinct records.

The requested provider model was `gemini-3.8-flash-high`; recorded responses
reported `gemini-3.8-flash-n`. Both arms used the same pinned configuration.
The configured `max_tokens=8192` was not an observed total-token ceiling: one
spatial response reported 14,300 output tokens including 13,600 reasoning tokens.
The enforced drawing/model-call/compiler budgets remain recorded separately.


## Held-out and Onn stress follow-up (2026-10-19)

A frozen-worker comparison now covers eight dataset cases held out from the earlier
six-case pilot, including six spatial cases, plus four complex Onn stress cases.
Onn exposure is disclosed separately; one case is an existing native worked example.
The broader run confirms fast correct affine composition but exposes substantial
constraint-extraction and deterministic-construction limits. It does not support
extending the initial success rate to this broader scope.

The full report, per-case outcomes, image comparison, source pins, counterexamples
and verification evidence live under `runs/spec-first-heldout/v1/`, starting with
`report.md`, `results.json` and `comparison.html`. These ignored study artifacts
must be preserved explicitly when transferring the workspace. No worker prompt,
schema or solver was tuned on the new cases, and no generated output was repaired.

## Fresh end-to-end comparison and spatial executor fix (2026-10-19)

The new frozen broad comparison used twelve unused dataset source families
(eight spatial, four planar), with fresh CPA calls in both arms. Native delivered
12/12; Spec First delivered 1/12. Its short average time mainly reflected refusals,
not a useful throughput advantage. Independently reviewed full acceptance was
2/12 native and 0/12 Spec First, with seven native spatial mathematics verdicts
left unknown rather than called incorrect. The full evidence and actual PNGs are
under `runs/spec-first-e2e/v1/`, beginning with `report.md` and `comparison.html`.
Onn families were already exposed in development and were not relabeled held-out.

The investigation found a deterministic executor defect: complete spatial
constraints were tested against sampled roots without solving them. A second
defect misread `SE/SA=SF/SB=1/3` as an assignment starting at its denominator.
The implementation now solves supported spatial root/locus parameters before
camera selection, preserves planar nondegenerate solid geometry, revalidates the
emitted construction, and admits complete numeric fraction chains. Unsupported
arithmetic fragments and decimal-comma continuations are rejected. Prompts,
model configuration, native workflow and compiler were unchanged.

A separately frozen fresh regression comparison then reran three failed families
through both arms, with no hand edits to outputs or extracted specifications:

| Arm | Delivered | Model calls | Generation compiles | Mean generation seconds |
| --- | ---: | ---: | ---: | ---: |
| Native | 3/3 | 12 | 8 | 138.87 |
| Revised Spec First | 3/3 | 3 | 3 | 21.85 |

All three Spec First outputs pass independent source-math, emitted-coordinate,
visibility and actual-PNG review. All three native drawings also pass supported
affine compatibility, content/strokes and readability. Native full world truth
remains unknown under the frozen certificate requirement; this evidence asymmetry
does not establish a quality advantage. The roughly 6.35x latency difference is
for this post-selected three-case cohort, not held-out generalization or time per
approved training pair. Offline evaluation and independent review are excluded.

The complete follow-up is under `runs/spec-first-e2e/v2/`: `report.md`,
`comparison.html`, `results.json`, frozen inputs/source pins, exact-output audits
and `review/measurement-limits.json`. Zero-model/zero-compile unchanged-spec
diagnostics are stored separately and are not fresh model successes. All 30
v1/v2 LangSmith roots were verified readable. Actual production-code verification
passed 141 construction tests; the affected spatial file passed nine tests after
equivalent test-literal cleanup. Scoped lint and diff checks pass; no formatter
ran. No output was promoted to an approved dataset target.

The next experiment needs a predeclared shared diagram-compatibility endpoint
and separate 3D certification reporting, followed by bounded symbolic dimensional
expressions and their independent checks. Prisms/frusta, fixed angles and spatial
projection/mark operations remain explicit coverage gaps. The original broad
failure rate must not be replaced by pooled post-selected rerun successes.

## Symbolic constraint compiler (2026-10-19)

The next implementation admits homogeneous lengths with one shared positive
parameter (`a`, `2a`, `a√2`, `a/(2√3)`) and fixed non-reflex angles. A bounded
expression parser preserves dimensions, rejects unsupported or partially read
notation, and refuses cancellation whose rounding uncertainty could distort a
length ratio. Complete explicit source chains and angle assignments are admitted
independently of model extraction. Both the optimizer and the separate final
coordinate checks enforce the resulting constraints in 2D and 3D; requested
metric labels must bind to the same constraints and actual carriers.

This changes the schema/capability prompt, not the number of model turns. The
native workflow, model configuration and compiler engine remain unchanged.
Independent parameters, curved solids, spatial angle marks and some plane
relationships still exceed the representation. Prose-scoped facts such as
“all edges” still depend on semantic extraction and independent source review.

Verification passes 188 construction tests, scoped lint and diff checks. An
independent code audit exercised cancellation and angle-prefix counterexamples.
The frozen study is `runs/spec-first-symbolic/v1/`: one known regression
and three unused spatial source families, including a required-angle-mark case
that the current renderer cannot support. References were analytically curated
from the unchanged instructions, not copied from dataset TikZ.

This study uses the same source-compatible affine projection, content/strokes
and actual-render readability endpoint for both arms. Output-bound 3D truth is
reported separately. Valid projections and deliberate affine violations are
calibrated; counterexamples also demonstrate that hidden metric errors can share
the same compatible diagram. Required unnumbered angle marks remain unverified
by automatic geometry checks and require the independently calibrated assistant
visual review step. That review is not an automatic or blind human benchmark.

The fresh comparison completed all eight jobs without pausing or modifying other
projects. Native delivered four source-compatible drawings; Spec First delivered
two and explicitly refused the mandatory spatial angle mark and the two
perpendicular-plane conditions. Both delivered Spec First drawings have
independently verified, output-bound world geometry. The source-compatible
native drawings retain unknown world certificates rather than mathematical
failures. Full readability acceptance is 3/4 native and 2/4 Spec First; the
remaining native failure is an independently corroborated label/stroke collision.

| Arm | Source-compatible delivered | Compatible and readable | Model calls | Generation compiles | Mean seconds, all attempts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native | 4/4 | 3/4 | 16 | 11 | 113.10 |
| Symbolic Spec First | 2/4 | 2/4 | 4 | 2 | 29.69 |

The two successful symbolic outputs took 24.51 and 28.10 seconds with one model
call and one compile each. Refusals remain in the table's timing denominator;
this is not a coverage or general quality win. The complete report and exact
images are in `runs/spec-first-symbolic/v1/report.md` and `comparison.html`.
All eight LangSmith traces were verified readable, all frozen hashes match, and
there were no provider errors or generation compiler HTTP errors. Sixteen
offline preparation and twelve evaluation compile requests are reported
separately. Generation compile latency had median 5.31 seconds and mean 6.94
seconds, including a 22.18-second outlier; it was not optimized in this change.

The next representation work is typed plane-perpendicular constraints and
world-space angle marks with verified projection and carrier binding. Prose
coverage remains a separate extraction/evaluation limitation. No output was
manually repaired or promoted to a dataset target, and this purposeful four-case
cohort must not replace the earlier broad failure-rate measurement.

## Drawing policy: agreed implementation and comparison

The next change replaces clearance-only spatial view selection with a deterministic
policy that uses the existing solid's base and requested carriers. The model-facing
specification, prompts, mathematical constraints, solver and occlusion convention
remain unchanged. The base is renderer metadata derived from the existing solid
declaration; an arbitrary convex construction without a declared base must not be
assigned a semantic base by guessing from face order.

The policy constructs a base-relative orthonormal camera frame, searches a bounded
set of views, and balances sufficient point/carrier clearance, foreshortening,
requested-carrier retention and separation above the base. It preserves all world
coordinates and dependency expressions when replaying one solved construction.
One common projection controls every point and stroke; visibility is recomputed
from the unchanged faces. Uniform page scale is separate from mathematical scale.
Projected line intersections must remain well-conditioned before emitting TikZ.
The implementation retains the existing XYZ basis mechanism described by the
[PGF/TikZ coordinate manual](https://tikz.dev/tikz-coordinates#sec-13.2.1), rather
than introducing a second rendering engine or changing the world geometry.

The study is `runs/spec-first-drawing-policy/v1/`. Existing successful constructions
are replayed with exactly the saved world points and dependencies, alongside the
historical native outputs. Unsupported old specifications remain unsupported.
Three unused source families receive fresh native and Spec First calls, with
additional old-policy rendering of the same solved geometry where available.
Historical comparisons, render-only replays and fresh end-to-end measurements are
reported separately. No manual output repairs or model retries are allowed.

Acceptance requires unchanged mathematical validity and content, coherent strokes,
actual-PNG inspection, and a separate review of whether the intended solid and
requested construction can be recognized. The worker's view score is diagnostic,
not its own acceptance oracle. Tests cover rigid-frame/renaming invariance,
dependency preservation, projection conditioning and difficult thin solids.
Presentation preferences are not universal mathematical requirements: valid
rotated or oblique diagrams must remain admissible.

The implementation also closes a separate spatial annotation omission. Existing
incident `perpendicular` relations with `mark=None` now select truthful corner
marks; `False` still suppresses them, and `True` requires a readable mark. World
orthogonality, a genuine shared vertex and drawn positive rays are checked before
projection. Skew lines cannot receive a corner at an apparent image crossing.
The corner is a projected world-space square, so it need not look square on the
page. This annotation-policy change is reported separately from camera selection.
Numeric angle annotation, general plane-perpendicular operators and a complete
selection policy for metric/equality cues are not implemented by this change.

View feasibility includes the caller's clearance threshold, projected intersection
conditioning and required mark size. Readable supplied perpendiculars take
precedence over the remaining view score. That score balances saturated clearance,
carrier retention, requested-carrier retention, mark conditioning, visible base
area and separation above the base. All terms are reported; none is an acceptance
oracle. An optional mark too small to communicate its relation is recorded as
`unreadable_size`, not counted as visibly represented.

The emitted coordinates use a centered uniform page normalization to avoid TeX
dimension overflow for a small translated world. Evidence preserves the original
world points, affine dependency operations, origin, uniform scale and orthonormal
projection. No individual point or edge receives its own distortion. Fixed-world
replay preserves the solved geometry exactly; fresh configuration ranking may
select a different valid world from the unchanged solver's bounded candidates.

### Drawing-policy results and deterministic repair

The frozen three-family fresh run delivered 2/3 native and 3/3 Spec First
outputs. All-gate independent acceptance was 2/3 native versus 1/3 Spec First.
Native used 10 model calls and 6 generation compiles (81.72 seconds mean across
all attempts); Spec First used 3 calls and 3 compiles (20.72 seconds mean).
Native's missing deliverable followed comment-validation errors and budget
exhaustion; its intermediate images were not substituted as final outputs.
All delivered outputs passed source-compatible projection/content checks, and
all three Spec outputs additionally passed independent source-world binding.
Those checks did not excuse presentation failures.

A subsequent generic annotation repair, preserved separately under
`runs/spec-first-drawing-policy/v2/`, moves validated equality ticks along their
original carriers to avoid named dots, crossings and perpendicular glyphs.
It reports crowded placement instead of claiming readable communication.
Page normalization also uses the entire drawn geometry rather than just labelled
points. Three fixed-world replays used no model/solver calls and one compile each.
Their source specs, constraints, coordinates, cameras and visibility were exact
matches to v1. Only the altitude case's tick lines changed; its mathematical
communication now passes, bringing repaired Spec acceptance to 2/3. This is
deterministic post-experiment repair, not a fresh end-to-end success rate.

The box's point-label attribution still fails; native and the old renderer on
that same world are clearer. The translation case passes both renderers. Old
successful replays now show perpendicularity, but still lack numeric angle/metric
or sufficient equality cues; two old unsupported specs remain unsupported.
Thus the policy has a demonstrated narrow benefit, not a general quality win.
Full results, controls, exact outputs and independent reviews are preserved in
the versioned study directories. Assistant review and a purposeful sample of
three new source families do not establish a population-level accuracy estimate.

### Source-led relation presentation

The next intervention owns selection of relation cues in one deterministic stage,
before either emitter. Research is pinned under
`runs/spec-first-relations/v1/research/`: eight planar curriculum figures and
eight spatial figures were inspected with their surrounding source text. The
Grade 11 parallel-projection rules preserve incidence, parallelism, and ratios
on parallel carriers, but not arbitrary angles or lengths. The Grade 7 triangle
and Grade 8 square-recognition examples mark selected premises without announcing
the conclusions being investigated. Grade 12 Fig. 2.26 leaves a regular pyramid's
equal edges unmarked while highlighting the vectors used by the problem. These
are counterexamples to an exhaustive annotation checklist.

The model still extracts mathematical premises and explicit drawing requests.
It does not choose coordinates, a camera, glyph positions or inferred numerical
answers. The harness's default selects stated perpendiculars, quantitative angles,
angle/length equality classes and equal partitions on drawn carriers. Equal
source-bound length expressions and ratio-one constraints join the same length
classes; numerical coincidences in a solved world never authorize a class.
Overlapping classes merge transitively. A quantitative equality class can use
one given value plus matching ticks; independent given quantities receive their
own value when their carriers are drawn. Explicitly requested length labels remain
individually required. Circle incidence may communicate equal radii without ticks.
Parallelism normally remains structural; an explicit request selects matching
arrows. Midpoints and shape definitions do not trigger every derived property.
These defaults are explicit harness choices, not requirements attributed to every
textbook figure. An explicit `mark=False` remains a suppression; admission of a
source constraint must not manufacture that suppression.

Angle scope uses three actual rays/points, with optional unknown-angle labels.
Numeric angles retain their supplied value; unknown angles are not solved and
printed as answers. The same sector cannot silently denote an unoriented line
angle, vector angle and dihedral angle. General plane relations remain unsupported
until they have their own construction semantics and executable checks.

All marks require true world relations and painted carriers. Spatial arcs are
sampled in the angle's local world plane and transformed by the solid's common
projection, rather than drawing a circular screen arc with a fabricated angle.
The camera checks selected sector conditioning and projected size. This follows
the distinction between the actual angle arms and its rendered glyph in the
[PGF angle library](https://tikz.dev/library-angle); the library draws a mark but
does not establish its mathematical truth. Suppressed, implicit, unavailable and
drawn cues are recorded separately. An explicitly requested unreadable cue blocks
delivery rather than disappearing silently.

Verification separates source interpretation, numerical truth, source-bound
visible cues and actual-image communication. Hand-authored curriculum controls
are reported as controls, not automatic extraction successes. Fixed-spec/world
replays are reported separately from fresh end-to-end calls. The prior comparison
and acceptance decisions remain intact; no latency improvement excuses omitted
constraints or grants a general quality win.

The implemented relation-policy study is preserved under
`runs/spec-first-relations/v1/`. All four known symbolic regressions were rerun
with fresh calls in both arms, after freezing the source, inputs and common
presentation criteria. Native delivered 4/4 and passed all five checks on 1/4;
Spec First delivered 3/4 and passed on 2/4. The five checks separately assess
source-compatible geometry, requested content, coherent strokes, mathematical
communication and readability. These are purposeful source-cue criteria, not a
claim that every textbook drawing must mark every given. Separate assistant
reviews inspected exact TikZ and actual PNGs; this was not blinded human review.

All seven delivered outputs were compatible with the source's mathematical
configuration under a parallel projection. All three Spec outputs additionally
passed independent source-world checks bound to their exact emitted TikZ. The
requested unvalued SCA sector and the regular square pyramid passed presentation
review. The 120-degree output correctly conveyed its angle and quantities, but
its fraction masked SM, so it failed readability. The two-perpendicular-plane
trapezoid remained explicitly unsupported and stayed in the denominator. Native
passed the SCA case; missing premise cues held the other cases, with an additional
point-label attribution failure on the regular pyramid. These communication
results do not mean the native projections were mathematically impossible.

Native used 14 model calls, 10 generation compiles and 77.75 seconds per attempt;
Spec used 4 calls, 3 compiles and 19.01 seconds per attempt, including its failed
extraction. Both used configured `gemini-3.8-flash-high`, with response metadata
reporting `gemini-3.8-flash-n`. All eight root traces were readable. Research,
offline evaluation and assistant review are excluded from end-to-end timing.
Four hand-authored curriculum controls passed independently, as did one of two
fixed-world replays; none counts as a fresh extraction success. The failed replay
kept its carrier occlusion and the two older unsupported extractions were not
repaired. The construction suite passed 221 tests and scoped lint/whitespace
checks. No formatter ran.

This is a demonstrated improvement on selected relation-presentation failures,
not a general quality win. General plane-relation semantics, valid perpendicular
cross-sections and their executable source checks remain the next capability gap.
The exact inputs, outputs, failed attempts, source pins, independent reviews and
limits are linked from the study's `comparison.html` and `report.md`.

### Plane perpendicularity and dihedral angles

The plane-relation extension adds mathematical predicates, not shape templates:
`perpendicular_planes` and `plane_angle` each take two noncollinear triples;
`dihedral_angle [A,B,C,D]` names the half-planes through A and D bounded by BC.
The conventional angle between planes uses the absolute normal dot product and
is at most 90 degrees. A named dihedral uses the signed dot product of the two
hinge-normal directions and may be obtuse. Grade 11 textbook 2, lines 1872-1876
and 1983-2023, explicitly distinguishes these definitions and gives 120/135-degree
examples. Zero/straight or coincident-plane sectors have no nondegenerate angle
glyph in this bounded renderer and must fail explicitly.

The solver constrains these relations directly, and the acceptance checker
independently recomputes them. Presentation constructs a normal section
at the actual intersection line, retaining its hinge and two perpendicular rays.
Given angles retain their value; requested unknown angles receive no numerical
answer. A section may require a genuine extension outside the solid to show the
acute plane angle; that extension must use geometric visibility, not an automatic
auxiliary-dashed rule. Source constraints, source point positions and solid faces
remain unchanged by this presentation step. Section construction and failures
are recorded as evidence. No arbitrary pair of face edges substitutes for a
normal section.

The existing single extraction call, bounded solver, camera search, compiler and
native comparison loop remain the owning mechanisms. The affected boundaries are
the relation schema, notation admission, numerical residuals, independent checks,
normal-section presentation, and the versioned capability prompt. Unknown relation
kinds no longer fall through the acceptance checker as zero residual.
Verification includes obtuse/supplementary counterexamples, rigid transforms,
renamed/reordered points, degeneracy, source omission checks, compound-equation
rejection, supporting planes meeting only at a vertex, and valid normal sections
at hinge endpoints. Spatial perpendicular feet use the world metric before
projection. The independent authoring evaluator also distinguishes these plane
predicates from its existing line-plane predicate.

The frozen fresh pilot on four unused source families keeps unsupported and
failed cases in the denominator, with geometry, visible communication and
readability reviewed independently. Source-derived analytic witnesses are
evaluator-only; dataset TikZ is not a reference oracle. Emitted coordinates are
checked against source requirements and bound to executed PDF point positions.
The three synthetic 120/60/90-degree controls passed geometry checks but failed
presentation review: overprinted corners obscure which ray pairs are normal,
and opaque angle labels mask carriers. These are recorded failures, not accepted
diagrams. Research and execution evidence belong in
`runs/spec-first-planes/v1/`; closed convex solids remain the rendering scope.

The fresh four-source run accepted 2/4 diagrams in each arm. Native delivered
all four (16 model calls, 13 generation compiles); Spec First delivered two
(2 calls, 2 compiles). Its other two jobs failed admission before a model call:
conjoined assignments were merged into one equation, and annotation prose was
misread as a numeric list. Its 19.12-second all-job mean therefore includes two
near-zero failures; its delivered-output mean was 38.19 seconds. Native's mean
was 116.93 seconds. This is not a four-case successful-generation speedup.

The general clause-parser repair preserves complete equation spans, retains
prose annotation requests as unverified, and still rejects malformed explicit
quantities. It passed 254 functional tests plus scoped lint and diff checks.
The two unchanged failed inputs were retried under `runs/spec-first-planes/v2/`,
with no changes to prompts or source givens and no manual specification repairs. They are
post-failure regression checks. The original and repair phases together are
limited to 20 model calls and 20 generation compiles; offline verification is
counted separately. The original accepted Spec First examples used existing
flat-angle primitives, so they do not demonstrate use of the new plane operators.

Both retries delivered in one model call and one generation compile (30.95 and
24.54 seconds), but neither passed independent presentation review. Direct
checks of their exact emitted 3D coordinates preserve the rhombus metrics and
four named dihedral branches, and the square pyramid's perpendicular faces and
true normal section. The frozen automatic world checker remains unavailable
for the rhombus's projected intersection syntax; a separate reviewer verified
the exact intersection and metric calculations without changing that result.
Its AC annotation masks O and its central relation marks lose clear attribution.
The square pyramid's 90-degree annotation masks SB/SH, and overlapping corners
obscure the normal-section pairings. Valid mathematical constructions therefore
remain insufficient for accepted diagrams.

The square retry exercises the new `perpendicular_planes` operator and generated
normal section. The rhombus uses existing flat-angle constructions and a world
perpendicular foot; it does not exercise the new typed `dihedral_angle` operator.
That operator has synthetic semantic controls, not fresh end-to-end operator
coverage in this pilot. The original and repair phases used 20 model calls and
17 generation compiles, with 16 offline evaluation compiles and three control
compiles recorded separately. All ten root traces were readable. This study
does not establish a diagram-quality improvement over native; source semantics,
emitted geometry and visual communication remain separate acceptance conditions.
