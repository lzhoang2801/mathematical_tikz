# Givens, TikZ targets and evaluation evidence

Proposed contract v0.1, 2 October 2026. This document makes the three decisions requested before synthetic generation concrete and reviewable. Existing project invariants remain binding; new conventions below are a specification to freeze, not a claim that validators already implement them or that existing candidates satisfy them. No synthetic batch or target approval is implied by this document.

Research status: this project does not yet have an established, validated evaluation protocol. The evidence-record design below is an engineering proposal, not evidence of evaluator validity. The [published evaluation protocols and proposed validation study](tikz-dataset-evaluation-strategy.md#how-published-work-evaluates-diagrams) must determine which evaluators are justified before implementing acceptance rules.

Use the [task contract](K-12%20Mathematical%20Diagrams%20with%20TikZ.md), [information-selection distinctions](diagram-information-selection.md), and [research strategy](tikz-dataset-evaluation-strategy.md) together. The drawing model continues to generate ordinary TikZ directly. The structured annotations below belong to dataset preparation and offline evaluation, not an extra representation the drawing worker must generate.

## 1. What counts as a given

Keep an immutable source snapshot and a separate task instance. A source is a complete selected problem or selected crop, with its original provenance. A task instance declares which source facts it retains, which constructions it requests, and what must be visible. Never overwrite source text with an augmented instruction.

The word `subgivens` must not serve as an untyped field. Record the actual operation:

| Operation | Exact meaning | Acceptance condition |
| --- | --- | --- |
| `subset` | Retain a subset of original facts and constructions for a smaller drawing scope | Every retained object and constraint has all its defining dependencies. Remove goals and visible objects that no longer have support. The resulting instruction is self-contained. |
| `rephrase` | Change wording or consistently rename symbols without changing mathematics or scope | Preserve quantities, domains, strictness, directions, incidence, branches and object identities. Record the symbol mapping. |
| `derive` | State a consequence of active premises | Record premise IDs, a named rule with its conditions or a checked derivation, and verification evidence. A successful numerical drawing is not a proof that the consequence follows. |
| `construct` | Request an additional object, such as a midpoint or perpendicular projection | Define the object from existing objects, establish existence and any uniqueness/branch condition, and explicitly request its visibility if needed. Mark it as synthetic, not present in the original source. |
| `change_instance` | Change a number, relation, domain, topology or branch | Create a new mathematical instance; record removed/replaced/added facts. Revalidate consistency, construction dependencies and applicable conclusions. Keep the original ancestry and split. |
| `render_variant` | Change allowed presentation while retaining the mathematical instance and requested information | Preserve the pinned source profile and all task-specific orientation, coordinate, source-view and Edit constraints. |

An ordered list of these operations describes a composite augmentation. Changing a right triangle into an oblique triangle is `change_instance`, never a paraphrase. Changing a free display parameter is `render_variant`; changing a stated measurement is `change_instance`.

### Fact annotation unit

Each fact has a local `fact_id`, a proposition, referenced object IDs, origin, role and provenance. Use one predicate per fact when its operands and truth condition are separable. Keep a named definition such as “square ABCD” as a source fact; expand only the defining predicates needed for construction or evaluation, each pointing back to that fact and a versioned definition rule. Do not enumerate arbitrary theorem closure or count the definition and its expansion as independent source facts.

Use these independent fields:

- `origin`: `source_text`, `source_image`, `definition`, `derived`, `synthetic_added`, or `synthetic_changed`.
- `role`: `given`, `construction`, or `goal`. A source proof goal retains `role=goal`; it cannot enter the active premises merely because it is true in one drawing.
- `depends_on`: fact/object IDs needed to interpret or construct it. This graph must be acyclic for a constructive recipe; an implicit constraint system instead needs a documented solver/consistency result.
- `source_ref`: original record ID, snapshot hash and exact supporting text span or image region. Text offsets refer to Unicode code points in the archived source text using a half-open interval. Store original path and line/page information for navigation; a line number alone is not identity. Image regions specify pixel coordinates and image dimensions against the hashed crop.
- `derivation_ref`: required for `definition` or `derived`; identify the rule/derivation and checked prerequisites. It is absent for original givens, not fabricated.

The task instance separately stores `active_fact_ids`, `requested_constructions`, `visible_requirements`, `forbidden_additions`, and `allowed_variations`. Visible requirements bind to objects or facts and specify the information to convey, including permitted alternatives. They do not automatically demand a separate symbol for every mathematical relation. Drawing a square does not automatically require four corner marks. A shown mark must still agree with the mathematics.

Existence, uniqueness and display freedom are different. A triangle with free side ratios admits multiple valid drawings: record those freedoms. An intersection with two branches needs either a selected branch or explicit acceptance of both. If the choice changes requested mathematics or visible content and cannot be resolved from the input, quarantine the candidate as `ambiguous_scope` or `ambiguous_branch`; the generator cannot silently choose a convenient interpretation.

### A source-grounded example

The original `bai-01` in [the preserved source records](dataset-selection/candidate-flow-8.sources.jsonl) specifies ABC right at A, AB < AC, altitude AH, reflection D of B about H, and DE parallel to AB with E on AC. HA = HE and the tangency of HE to the circumcircle of CDE are proof goals.

- A smaller drawing of ABC and AH can retain the triangle conditions and the definition of H, dropping D, E, the circle and their goals together. It remains descended from `bai-01`.
- Adding “M is the midpoint of BC; draw AM” is an explicit synthetic construction. It must not be attributed to the original text.
- Constructing E by enforcing the desired tangency would use a goal as a premise. E must instead follow its stated intersection construction.
- The choice AB/AC = 1/sqrt(3) in the current harness example is free layout data satisfying AB < AC. It is not a numerical given from the problem and must not become an instruction requirement.

These examples explain the contract; they are not newly generated or approved dataset rows. The existing eight candidates remain development material and need review under this contract.

### Inputs for the three tasks

| Task | Worker input | Preparation responsibility |
| --- | --- | --- |
| Generate | Self-contained `instruction` | Start from a complete selected example/practice/exercise. Resolve references such as “the figure” into supported explicit facts. Include the chosen constructions and drawing scope. Keep solutions and target-only coordinate choices out of the input. |
| Reconstruct | Hashed image crop and `instruction` | Preserve the visible configuration, labels, extents, marks and view. Do not infer exact equal lengths or perpendicularity solely from approximate pixels. Use visible marks/text or explicit input for those exact claims. Unreadable or contradictory evidence needs review. |
| Edit | Actual `current_tikz` and self-contained `instruction` | State the requested change and the facts needed to interpret it. Offline annotation defines both the change set and the unaffected preservation set. Correct targets must be complete TikZ, not patches. |

All three may share the same givens. They need not share an identical target: a crop can contain detail outside a Generate scope, and an Edit can request a changed instance. Task input must independently support its target. A synthetic crop records the parent render and transformation; it never masquerades as a textbook crop.

## 2. Lineage and split invariants

Retain existing source metadata and use `source_group` as the leakage-group ID. Add parent variant IDs and root source IDs; do not create a different group per task or augmentation. One group has exactly one split: train, development or test.

Before assigning splits, join records connected by original problem/crop identity, textbook/teacher-book duplication, derived instructions, parameter variants, edits, translations and synthetic renders. Also check semantic duplicates from different roots. Canonical comparison ignores symbol renaming, equivalent unit notation and surface wording, but preserves numerical constraints, domains and construction semantics. Hash equality is evidence of exact duplication; unequal hashes do not establish semantic novelty.

An exact duplicate of the active givens/constructions cannot cross splits even when sourced from different books or requested in different tasks. Sharing one generic premise, such as “ABC is a triangle,” does not by itself equate two richer instances. If subset augmentation reduces both to the same complete active fact set, that duplicate must be grouped or excluded from cross-split export. Record uncertain duplicate candidates for review; do not claim a general mathematical-equivalence detector already exists.

Every descendant inherits its group's split. A multi-parent augmentation must retain every root; it is forbidden when parents belong to different splits. Do not use held-out rows as generator examples, retrieval material, repair demonstrations or diversity feedback. If a duplicate connection is discovered after freezing a release, invalidate/quarantine affected exports and version the split repair. Do not quietly move evaluated test cases into training and keep the old benchmark claim.

Export assertions are concrete: every row has known roots; every ancestry edge stays within its group/split; no group appears in multiple splits; no unresolved cross-split duplicate candidate remains; target/rubric/reference fields are absent from worker inputs.

## 3. Synchronizing TikZ with the drawing harness

Yes: new training targets should use a pinned version of the shared [TikZ prompt](../../mathmath/src/agent/prompts/tikz.py), together with its [validator and wrapper](../../mathmath/src/agent/latex/tikz.py). Pin the actual file hashes as well as version strings. Do not follow a mutable `latest` prompt midway through a dataset release.

Read-only snapshot on 2 October 2026:

| Reference | Version | SHA-256 of file bytes |
| --- | --- | --- |
| `src/agent/prompts/tikz.py` | `tikz-harness:v4.11` | `b9c4c0c773176c6023337beb5ff7dcdbefbd355ed34e011f26ef75b5ca454bf1` |
| `src/agent/prompts/problem_tikz.py` | `problem_tikz:v0.93` | `82f5fd94844bdd087a30107b802ef8d85149da7fa733e64ab05ed8970dc9d0aa` |
| `src/agent/prompts/geometry_tikz.py` | `geometry_tikz:v0.9` | `ff0b6fd9820169c59d76182a2de64f0e88cd2aa50c4386a6aaedc2c46d88cb58` |
| `src/agent/latex/tikz.py` | Validator/wrapper snapshot | `ae6990d1be9b27c17728abefe9bed3aba2ae3aead5fc79c49b608ec791ebc686` |

These are current working-tree hashes, not commit identities. One `target_profile_id` in the release manifest resolves to the common prompt, applicable task prompt, and validator/wrapper snapshots.

The proposed target profile adopts the prompt's complete source contract:

1. Exactly one ordinary, comment-free `tikzpicture`; no Markdown, preamble or document wrapper. Use the shared libraries/packages. Respect the existing prohibited TeX operations; ordinary parameter macros and conditionals remain permitted.
2. Four consecutive groups separated by blank lines: independent frame/free parameters; dependent coordinates/helpers; visible strokes/annotations; point markers/labels. Shared appearance belongs at picture level. Preserve named dependencies rather than replacing constrained points with computed decimal coordinates. Batch repeated markers, labels and relation marks as specified.
3. Keep computational helpers undrawn and their construction inside `pgfinterruptboundingbox`; visible objects remain outside. Use the prompt's geometric label-placement procedure, with local overrides justified by observed collisions. Preserve physical units for text/stroke/marker sizes.
4. Apply the prompt's orientation and six-unit reference defaults only to free posture/display size. Stated directions, coordinate-system values, source view, requested physical size and unaffected Edit geometry take precedence. For spatial diagrams construct in a common metric frame before projection.
5. Select relation marks from the instruction's information requirements. Marks never establish a relation or justify assuming a proof goal. Preserve segment/ray/line/arc extents and prescribed line roles.

The validator currently enforces only part of this profile, including the envelope, comments and prohibited literal TeX. Compilation does not certify the four groups, construction dependencies, geometric label selection or profile exceptions. Those need explicit source inspection or a calibrated supported checker. Record `source_profile_status` separately from mathematical results; a geometrically valid output can still fail the deployed source contract.

Profile compliance is an export/task-success gate, not a replacement for the four shared dimensions. Publish pure compile rate separately so style failures do not get reported as TeX failures. Accept mathematically equivalent code within the profile; do not grade string equality against the reference.

Keep original supplied TikZ unchanged in provenance. Migrating a target to this profile creates a new target revision, with old/new hashes, render and semantic checks and renewed rubric review. An upstream prompt change starts a new profile revision and compatibility review; it does not retroactively invalidate a frozen historical experiment.

The native `problem_tikz` protocol renders a complete source, observes the returned image in a later turn, and returns structured completion; the delivered code is the last rendered source. Final-code SFT targets are just TikZ. Tool-use trajectories, if later trained, must separately match the native message/tool schema and retain render evidence. A completion message alone is not a successful render.

The current `geometry_region_to_tikz` entry point takes an image and supplies a generic reconstruction instruction; it does not pass a dataset row's own instruction. A future three-task runner must resolve this input mismatch while reusing the shared drawing harness. The dataset contract is not evidence that this routing already exists.

## 4. Where evidence and limitations come from

The four dimensions organize requirements. Compiler/parser metrics describe particular stages. Neither supplies a universal correctness verdict. For every sample-specific criterion, define this chain before evaluating an output:

`source/input obligation -> observed output artifact -> bound object/measurement -> executable check or adjudicated observation -> criterion result`

The source supports **what is required**; the produced code and render support **what was produced**. The target is a reviewed witness of an acceptable output, not evidence that the new output contains the same objects. A reference-shape mismatch is a fidelity result, not an automatic task failure: accept valid alternatives that satisfy the frozen instruction, rubric, and visible-content requirements. Never compute an ideal diagram from the instruction and call that an observation of the output.

| Required claim | Evidence producer and saved artifact | What it can establish | What it cannot establish |
| --- | --- | --- | --- |
| Output is admissible and compiles | Shared validator, wrapper, compiler response/log, exact submitted TikZ/TeX and returned PDF/render hashes | Accepted source subset; successful build/render in the recorded environment | Nonblank required content, mathematical correctness, full prompt compliance or readability |
| Named planar coordinates satisfy a relation | Semantic-label binding plus PGF coordinate probe, measurement file, predicate result | The specified incidence, ratio, angle/order condition on observed bound coordinates within calibrated tolerance | That carriers/labels/circles are drawn; that labels identify those coordinates; general 3D metric or other non-projection-invariant claims from screen coordinates alone. Projected incidence, affine, and construction-dependency checks are valid only in a declared `affine_projection` frame and when the relation is preserved by that projection. |
| Required straight carrier is painted | Bound endpoints plus PDF drawing extraction and interval-coverage check | Supported straight path coverage, including unions of adjacent segments and excluding detected zero-opacity strokes | Arbitrary curves, actual final visibility under all clipping/overpainting, label semantics or readability |
| Required circle/arc, region or curve exists | A supported painted-primitive extractor with center/radius/domain/extent/fill evidence; otherwise adjudicated render inspection | Only the supported observed primitive and its binding/extent | A circle inferred from three point coordinates is not evidence of a full painted circle; finite graph samples do not prove equality everywhere |
| Required labels/marks identify the right objects | Text/glyph or render evidence with object association and adjudication | Observed label/mark content and binding within the checked scope | Token presence in source or OCR text alone does not establish association, visibility or absence of overlap |
| Spatial or algebraic requirement holds | Appropriate construction-space or function/domain evidence and supported executable predicate | The explicitly checked 3D relation, endpoint inclusion, domain, branch, sign or shaded-side property | Screen lengths and angles alone do not establish general 3D metric claims. Record the declared `affine_projection` frame for projected incidence, affine, or dependency predicates; unsupported functions and unobserved regions remain unresolved. |
| Diagram is readable | Original render at recorded display scale; criterion-specific adjudicated inspection; supported collision measurements where available | The inspected readability condition | A bounding-box or global image-similarity score cannot certify all label associations and ambiguities |
| Edit preserves unaffected content | Before/after code/renders, semantic bindings, change/preservation sets and allowed transforms | Requested change and preservation, checked separately | A small code diff or similar image is not proof of correct editing |
| Extracted IR is usable | Exact code/IR hashes, extractor identity, schema validation, unsupported-feature list and independent fidelity evidence | Well-formed, attributable observations within verified extraction scope | Hashes and schema validity do not prove extraction truth or instruction fidelity |

### Required evidence record

For each atomic check, store `criterion_id`, `check_id`, `dimension`, `requirement_ref`, `subject_tikz_sha256`, `artifact_refs` with hashes and locators, `producer` with version/code hash, `bindings`, `observation`, `predicate`, `tolerance`, `status`, and `limitation_refs`. `requirement_ref` identifies an instruction span or explicit requirement; target-only incidental styling cannot create a requirement.

Bindings identify the actual observed object and their basis. If the required semantic label is M but the code uses an internal name P7, failure to resolve that mapping is `unknown`, not a mathematical failure. Instrumented measurements retain original and instrumented code hashes, instrumentation version and correspondence evidence. The instrumented render is not substituted for the delivered render when judging readability or coverage.

Numerical checks record units/frame, normalization, residual, tolerance, uncertainty treatment and calibration reference. Exact discrete checks mark numerical tolerance as not applicable with a reason. Do not silently use the old experiment's ratio/angle constants as global policy. Where a measurement uncertainty interval straddles the decision boundary, return `unknown`; strict inequalities need an explicitly calibrated margin. Missing tolerance/calibration for a numerical acceptance rule blocks that rule from automatic acceptance.

Use `pass`, `fail`, or `unknown` for applicable checks; `not_applicable` requires a reason fixed by the rubric. A check has `pass` only when its entire claim is supported, `fail` only with a supported counterexample, and `unknown` for missing, ambiguous, stale, unsupported or failed evidence collection. Distinguish infrastructure failures from an actual invalid output. Contradictory evidence requires adjudication, not averaging.

A criterion passes only when all required subclaims pass. One supported failure fails it; any remaining unknown prevents a pass. A definite task failure can coexist with unresolved checks. Strict task success requires all required criteria and the output profile to pass. Publish automatic verification and human-adjudicated results separately. A generic `accepted` flag, model verdict or empty list of checks is never sufficient.

### Limitations are recorded at three levels

1. **Declared capability limit:** the checker's versioned supported primitives, assumptions, units, transforms, bindings and exclusions. Cite implementation locations and calibration artifacts. For example, the current stroke tool declares straight-stroke scope and excludes curves/occlusion/readability.
2. **Per-run evidence gap:** the actual missing label binding, unsupported primitive, stale hash, compile failure, extractor failure or ambiguous branch. Attach it to affected criterion IDs and evidence artifacts.
3. **Empirical limit:** a saved valid variant rejected, an invalid variant accepted, or a source family absent from calibration. Record the counterexample and the capability revision it invalidates. Absence of observed failures is not a universal guarantee.

Use stable reason codes such as `missing_binding`, `unsupported_primitive`, `unverified_extraction`, `stale_artifact`, `collector_unavailable`, `uncertain_measurement`, `visibility_unchecked`, `ambiguous_source`, and `uncalibrated_family`, with concrete details. Limitations come from these records, not a model composing a reassuring paragraph after scoring.

The existing development experiment supplies two concrete warnings: removing a required OC stroke left coordinate checks passing; drawing only half a circle escaped straight-segment coverage checks. A third calibration control should consistently rename internal coordinates without changing the diagram: unresolved binding must not become a false geometry failure. These controls test the complete extraction-to-decision path.

### Current capability gaps and TypeSafe

The local [candidate evaluator](../tools/evaluate_tikz_candidates.py) and [painted-segment checker](../tools/verify_painted_segments.py) import the removed `agent.latex.compiler` module. [Target compilation in the IR tool](../tools/verify_diagram_ir.py) also uses that old API. Their historical results do not establish a working current end-to-end pipeline. Route them through the existing compiler boundary and rerun calibration before production; do not add another drawing loop or modify the read-only MathPaper reference.

The candidate evaluator's present aggregation can fall back to model grades, including for criteria without executable checks. Its report labels these scores diagnostic. Those scores must not be promoted into this contract's verified passes. The shared validator also does not enforce the entire source profile. Full painted-circle/arc verification, general label association and complete readability are not established current automatic capabilities.

There is another source-audited prototype defect: `evaluate()` consumes measured point coordinates without requiring `measure_points()["success"]`. Partial logs from failed measurement compilation can therefore reach predicates. A future evaluator must require successful measurement compilation and matching source identity before using those observations; otherwise affected checks are unknown. The prototype's compile score also has no nonblank-content check. Neither defect was exercised in a live compilation run during this review.

TypeSafe Jev can be studied as a semantic evaluator and an assistant to IR assembly, as proposed in the [research review](tikz-dataset-evaluation-strategy.md#using-typesafe-jev). It can select observed object/evidence IDs, bind requirements, and predict coverage or edit preservation. Save the exact question/state, candidate bindings, model version, answer distribution and calibration revision. These learned criterion predictions are legitimate research scores to validate against humans; they remain distinct from this contract's verified mathematical passes and approval of training targets. Confidence cannot supply a missing observation or override a known failed check. A second model agreeing with the first does not fill an evidence gap.

## 5. Controlled diversity and traceability

Unlimited possible descendants are compatible with finite, resumable batches. A batch manifest must fix source groups/split revision, allowed operators and parameter domains, task/type mix, root/template contribution caps, target item count, total model-call/retry/time/token or cost limits, concurrency, stop conditions, prompt/profile/checker versions and random seed. Missing values block execution; “as many as possible” is not a batch budget.

Vary semantics before surface wording: supported source families, dependency depth, requested construction subsets, legal branches, numeric regimes and edit intents. Then vary faithful instruction phrasing, symbol naming, permitted layout and image acquisition transformations. Orientation randomization cannot override the pinned free-posture defaults unless an explicit, valid task condition gives it that freedom. Never introduce erroneous geometry or omit required content merely to improve diversity.

Use independent recorded random streams for source sampling, mathematical operators, language and rendering. For example, derive per-row stage seeds from SHA-256 of a canonical tuple containing batch seed, stable variant ID and stage name; record the tuple encoding, PRNG and operator versions. Store the actual sampled values and model requests/responses. Seeds reproduce deterministic sampling, not guaranteed identical remote model outputs.

Measure proposed and accepted distributions separately: source-group concentration, task/type/operator/dependency-depth coverage, parameter bins, instruction-template concentration, canonical-instance duplicates, code duplicates and render near-duplicates. Report counts and the largest root/template share; entropy can supplement these, but random noise or paraphrases do not demonstrate mathematical diversity. Set numeric batch caps and deduplication thresholds before execution and retain rejected attempts. The profile intentionally keeps code conventions stable; diversity does not require inconsistent source style.

Retain one provenance record per root, one candidate record per variant, and an append-only attempt/event log. Large logs/renders can be referenced by path and hash instead of copied into every row. Required trace contents are:

| Level | Required contents |
| --- | --- |
| Source | Original record IDs, snapshot hashes, source locations/crop hashes, grade/book/role, source kind and taxonomy; unresolved provenance is explicit |
| Variant | Row ID, root IDs, source_group/split revision, parents, ordered operations/versions/seeds/parameters, active facts and scope, task-specific input hashes |
| Preparation | Instruction revision, target/rubric/profile hashes, automatic/repair/curation route, author or reviewer identity and decisions, superseded revision links |
| Attempt | Batch/run/attempt/parent trace IDs, stage, request hash, provider/model/settings, prompt version/hash, start/end/status, provider retries, token/call/cost accounting and error code |
| Evidence | Compiler environment and wrapper identity, artifacts/hashes, criterion results, capability/calibration versions, limitations and adjudications |
| Export | Frozen instruction-target-rubric revision, lineage/duplicate/profile/evidence gate results, approval basis, dataset/split revision |

Record a durable attempt ID before dispatch. Resume from completed verified artifacts only when input, profile and checker versions match. An uncertain in-flight request is not silently retried as a new success. Retries receive separate linked events; failed and rejected attempts remain in cost/yield denominators. Use the existing LangSmith trace boundary where applicable and local durable manifests for reproducibility; a trace URL alone is not the dataset record. Log necessary payload artifacts under controlled access and never credentials.

Manual corrections create new revisions and retain the original output and correction route. Report automatic preparation, deterministic repair, model repair and assistant/human curation separately. Successful synthetic volume is accepted rows and distinct source groups, not attempted calls or paraphrase count.

## 6. Gate before generation and export

Before any new production batch, freeze the input/target/evidence contract revision, resolve current source-anchor validation and compiler compatibility, and demonstrate the needed checkers on valid equivalents and deliberate failures. Each unsupported criterion must have an explicit adjudication route; it cannot silently become a pass. Batch-specific tolerances, diversity limits and budgets must be populated before dispatch.

Prepare in this order: source and scope annotation; self-contained task input; aligned target; instruction-specific rubric; target evidence and review; frozen triple; model comparison or approved SFT export. Freeze the rubric before evaluating candidate model outputs. Changing an instruction, target or rubric creates a new triple and invalidates its old evaluation evidence. No test-group material enters fine-tuning.

The authorized **Synthetic data generator** chat has completed a read-only contract audit. Its next generation assignment must name this contract revision, exact selected roots, finite batch budget and required output/evidence fields. It must return candidates and rejection records, never self-approved gold. No synthetic generation, model experiment or training was started in this contract pass.
