# Spec First experiments

This package owns the experimental construction, specification, constraint solving
and presentation code. Native drawing and the shared compiler client remain in
the sibling `agent/` and `latex_compiler/` packages; their source pins are recorded
in [`../upstream.json`](../upstream.json).

Tests are under `tests/spec_first`; experimental runners and case definitions are
under `tools/spec_first`. The two legacy worked-example scripts still require
their absent `docs/examples/spec-first-*` source assets. Their mathematical unit
tests use independent fixtures; they do not reconstruct missing source provenance.

`construction_agent.build_construction_agent(model)` uses `render_construction`
in the existing bounded experimental model/tool loop.
It executes six typed planar operations, checks degeneracy and asserted marks,
and emits ordinary TikZ with named PGF dependencies before using the same renderer.
The model still chooses the construction, diagram content and labels.
The experimental method prompt describes this interface. This is not a general
constraint solver or a replacement production workflow.

The pilot runner prepends `src` and asserts local import paths. Native production
tools also use the local native copy. The shared
installed Python dependencies can be used without modifying their environment:

```powershell
..\mathmath\.venv\Scripts\python.exe -B tools\spec_first\run_construction_pilot.py prepare
..\mathmath\.venv\Scripts\python.exe -B tools\spec_first\run_construction_pilot.py calibrate
..\mathmath\.venv\Scripts\python.exe -B tools\spec_first\run_construction_pilot.py draw
..\mathmath\.venv\Scripts\python.exe -B tools\spec_first\run_construction_pilot.py evaluate
..\mathmath\.venv\Scripts\python.exe -B tools\spec_first\run_construction_pilot.py report
```

`draw` makes live CPA calls and traces them to the configured LangSmith project.
It refuses changed code/configuration, incomplete calibration and provider-stopped
runs; attempted invocations are never silently repeated. Use a fresh output
folder for a separately authorized experiment. Current bounds per suite are three fixed
Generate cases, two repetitions, four model calls and four compiler requests per
drawing, zero provider retries. Targets never enter drawing messages.

Protocol, raw model/tool events, compiler requests and timing, native outputs,
independent original-PDF checks and four-metric scores are saved under `runs/`.
Calibration and evaluation compiles are separate from generation cost. Visual
review and source-contract review remain separate from model self-acceptance and
executable checks. No outputs are promoted to the dataset by this runner.

The fixed cases/checks are in `tools/spec_first/construction_pilot_cases.py`; they reuse the
existing evaluation requirements and observed PDF geometry. The bisector arc
check accepts different valid arc radii. The planar suite covers only small planar constructions. The spatial extension
below is a separate frozen comparison; neither establishes performance for Edit,
Reconstruct, arbitrary constraints or unsupported construction branches.


## Spatial pilot extension

`spatial=True` selects `render_spatial_construction` inside the bounded
construction loop. The model supplies named XYZ dependencies and cyclic solid faces.
The forward executor supports free points, affine interpolation, translation and
actual 3D line intersection. It validates one closed convex polyhedron, chooses
one orthographic view from 24 fixed candidates using projected clearance, then
classifies boundary and contained segments by front-face membership. It never
uses auxiliary status or a reflected point name as a reason for dashes.

Both spatial arms receive the same explicit closed-solid visibility convention.
The native arm still emits ordinary TikZ. The construction arm emits named PGF
dependencies and a local projection/visibility witness bound to the final TikZ
hash; the witness is not an evaluator input. Free-point selection and instruction
interpretation remain model responsibilities. The label heuristic considers
incident directions and still needs visual review.

Use `--suite spatial --output runs/spatial-pilot-20261019` with the phases above.
The three frozen grade-11/12 cases are defined in `tools/spec_first/spatial_pilot_cases.py`.
Independent checks fit one affine projection from four fixed PDF-observed anchors
and hold every other point out of the fit. They check one global depth hypothesis,
required/optional line coverage, opposite-style overlays, extra strokes and
readability using actual painted dash intervals. Vector and glyph equality ticks
are admitted on equal terms. These checks establish affine realizability for
these particular cases; they do not recover general 3D metric geometry.

The pilot has no support for open/transparent or nonconvex solids, external
segments, curved surfaces or changes of visibility within a carrier. An unfilled
wireframe convention is required; paint-order occlusion remains a visual-review
boundary. Neither a self-accepted drawing nor a numerical check is an approved
training target.

## Spec First pilot

`spec_first.workflow.draw_spec_first` makes one instruction-to-specification
model call. The specification contains names, mathematical relations, branch
conditions and visible content, but no coordinates, camera, dash flags or TikZ.
The deterministic compiler in `spec_first.spec` lowers supported constraints to
named operations, solves remaining planar and spatial parameters and searches views, validates the supplied
relations and decides strokes before the existing renderer compiles once.
There is no model image-review or repair turn. The native baseline uses the
separately pinned copy under `src/agent/`.

The current CPA endpoint can return a schema-shaped response as complete JSON text
instead of a tool call. The workflow admits complete JSON, optionally in one exact
JSON fence, through the same Pydantic validation. It does not extract JSON from
prose, repair partial JSON or call the model again. The transport format is saved.

Select this arm with `prepare --method spec_first --suite planar` or `--suite spatial`
and a new output directory, then use the existing calibration/draw/evaluate/report
phases. See `docs/construction-pilot.md` for the frozen experiment and results.
Hand-authored specs in tests are calibration only. Source requirements, reference
TikZ and independent checkers are outside the worker's input. Consistency of the
extracted spec does not prove that it captured every requirement of the instruction.
Unsupported specifications and exhausted configuration search remain explicit
failed attempts; neither is silently replaced by direct TikZ generation.

The runner rechecks the pinned compiler before each drawing and stops the run on
infrastructure loss. Such a run requires a fresh explicit revision; no paid job
is silently retried. Unavailable evaluation evidence remains null. Completed
Spec First pilot measurements and limits are recorded in `docs/construction-pilot.md`.

The planar backend now retains the exact construction DAG and jointly optimizes
only its free root coordinates and locus parameters with bounded SciPy least
squares. Analytic line-circle roots initialize both branches, including external
intersections. Every supplied constraint and branch is checked before annotation
and again against the emission executor's coordinates. A converged optimizer is
not a certificate, and exhausted local search is not a proof of inconsistency.
Defaults remain 32 planar candidates and at most 80 optimizer evaluations per
candidate; actual residual calls, including numerical Jacobians, are recorded.
The emitted coordinates and solved coefficients certify one static configuration.
Changing its roots can require re-solving; the named DAG does not establish
symbolic preservation of every constraint or general Edit support.
Install `src/spec_first/requirements.txt` into the worker environment for this
optional path. The reference MathPaper environment must remain unchanged.

Circle-incidence equalities do not imply radius ticks. Other implicit equality
marks require painted carriers; explicit marks still fail if their carriers are
missing. Source interpretation remains the model's responsibility, with no new
prompt or model repair loop. Rendered Spec First results remain
`usable_with_issues` until instruction coverage receives independent review.
The saved-spec regression
replay starts under `runs/spec-first-improvement/v1/`; the completed recovery,
independent checks and gallery are under `runs/spec-first-improvement/v2/`.
It is not new held-out evidence. Source mathematics, automatic PDF extraction
and visual readability are reported separately; none promotes a dataset target.

## Instruction quantities and admission

`spec_first.instruction_constraints` independently reads a bounded subset of explicit
notation from the original instruction: numeric segment assignments, numeric or
segment radius declarations, scalar segment ratios, complete numeric fraction
chains such as `SE/SA=SF/SB=1/3`, and strict length comparisons. Fraction chains
preserve every ratio; unsupported operator prefixes, partial numeric expressions
and decimal-comma continuations are rejected rather than silently truncated.
The admitted specification adds those obligations to a copy of the model output.
Conflicting model quantities, unknown endpoints and unbound label requests stop
execution. The raw extraction remains in `specification.json`; the merged form
and exact source spans are saved separately. Source quotes alone never establish
metric coverage.

`length`, `length_ratio` and `shorter` constraints reach both numerical solving
and the separate realized-coordinate checks. All physical lengths share one unit
conversion and one uniform diagram scale; source centimeters are not physical
paper centimeters. The witness records that scale. Requested numeric labels are
bound to endpoint pairs and checked against length constraints and drawn carriers.
Label values and units are typed data, not arbitrary TeX. Unsupported annotation
expressions are rejected in full rather than reduced to embedded digits.

Before extraction, explicit sphere/cylinder/cone requests are rejected because
the current renderer lacks curved spatial surfaces. A model cannot evade this
by returning `dimension=2`. Explicit spatial instructions also require a spatial
specification, and any model-declared `unsupported` excerpts prevent rendering.
This prevents a planar substitute; it does not implement sphere rendering.

This notation reader is deliberately incomplete. Independent symbolic parameters,
proof-goal quantities, ambiguous implicit units and unsupported label expressions
stop the bounded path. Other natural-language omissions can
still pass this gate, so results retain `instruction_coverage_verified=false` and
require independent source review. The focused replay is under
`runs/spec-first-instruction-contract/v1/`; it is neither a new held-out result
nor evidence of an end-to-end speed advantage.

## Spatial constraint solving

The spatial path now reuses bounded root/locus optimization before camera search.
Supported perpendicularity, parallelism, equal-edge and section relations constrain
the world coordinates. Face planarity, area and volume margins guide the search;
the independent solid validator still rejects nonplanar, degenerate or nonconvex
results. A numerical closest-line intersection is only a search intermediate:
the emitted construction must have an actual intersection, and every supplied
relation is checked again against the emission executor's world coordinates.

The existing twelve-candidate budget and eighty optimizer-evaluation limit remain.
Search can stop after three valid spatial configurations; actual candidate and
residual-call counts are recorded separately from their budgets. No model or TeX
call occurs inside this search. The prompt, native drawing loop and extraction
budget are unchanged.

This improves realization of supported specifications, not completeness of source
interpretation. Prisms/frusta, independent dimensional parameters,
curved surfaces and spatial projection/annotation operations still exceed parts
of the current representation. Unsupported requests remain explicit failures.
The fresh broad comparison is in `runs/spec-first-e2e/v1/`; the separately frozen
post-selected regression experiment is in `runs/spec-first-e2e/v2/`. Diagnostic
saved-spec replays are never counted as fresh model successes.

## Symbolic quantities and fixed angles

`metric_expression.py` parses constants and homogeneous lengths with one shared
positive parameter: for example `a`, `2a`, `a√2`, and `a/(2√3)`. It uses no Python
or TeX evaluation and emits only its own bounded TeX vocabulary. Input length,
token count, nesting and coefficient magnitude are bounded. Propagated rounding
uncertainty rejects unresolved cancellation rather than admitting a spurious
nonzero scale. Multiple independent parameters, products of lengths, and sums
with incompatible dimensions remain unsupported.

The instruction reader preserves complete chains such as `AB=AC=a` and explicit
fixed-degree angles, then merges them into the extracted spec. Arithmetic prefixes
and truncated suffixes cannot silently become a length or angle assignment.
The model can also express symbolic lengths from prose using `expression`, or
fixed angles using `angle`; source quotes are provenance, not coverage evidence.
All bound lengths share one scale in either 2D or 3D. Both the optimizer and the
separate emission check enforce those ratios and world angles. Requested length
labels must match a constraint and a drawn carrier. Page size stays independent
of physical units.

The semantic extraction still uses one model call, followed by bounded solving,
camera/stroke selection and one compile. The versioned prompt describes the new
schema capabilities; it adds no repair loop. Spatial angle sectors use their
actual world rays and the same projection as the solid. Prose such as "all edges" still depends on extraction and
independent source review; the notation reader does not certify that coverage.
Fresh symbolic experiments and the common diagram-compatibility protocol live
under `runs/spec-first-symbolic/v1/`, separate from world certification.

## Plane relations and normal sections

The experimental schema distinguishes `perpendicular_planes`, the acute
unoriented `plane_angle`, and `dihedral_angle [A,B,C,D]`, whose named half-planes
through A and D share hinge BC. A dihedral can be obtuse; taking the absolute
dot product would change its meaning. Both solving and independent checks
enforce these predicates in world coordinates. Unknown sectors do not receive
computed answer labels.

`plane_sections.py` constructs a normal section at the actual plane intersection:
one common hinge point and two perpendicular rays in the requested planes or
half-planes. It reuses valid named carriers, permits hinge endpoints and bounded
supporting-plane extensions, and computes geometric visibility of auxiliary
segments. It does not dispatch on problem IDs or named solid templates.
Spatial feet are computed before projection, not on the screen image.

The notation reader separates conjunction-delimited mathematical assignments.
Prose annotation requests remain explicitly unverified rather than being parsed
as malformed numbers. This is still a bounded notation reader, not a proof that
all natural-language requirements were extracted.

The four unused-source comparisons are preserved in
`runs/spec-first-planes/v1/`. Two subsequent parser-repair attempts are separately
labeled in `v2/`; they do not replace the original failures. Correct normal-section
geometry does not establish readable glyph attribution: the synthetic plane-angle
controls retain documented presentation failures. See `docs/construction-pilot.md`.
