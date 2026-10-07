# Synthetic geometry data: Generate and Edit

Contract version: `synthetic-tikz:v2`.

These conventions cover source selection, mathematical instructions and target preparation. The local skill is [synthetic-tikz](../.agents/skills/synthetic-tikz/SKILL.md).

## Instruction generation through CPA

Use [tools/generate_instruction.py](../tools/generate_instruction.py) to supply the repository-local skill, its mathematical strategy and audited source context directly to the configured CPA model. Each bounded context produces one structured response; no autonomous browsing, management-format conversion or automatic refill loop is needed. This follows the supported [LangChain structured-output interface](https://docs.langchain.com/oss/python/langchain/models#structured-output), verified against the installed `langchain-openai` source.

The runner writes `instructions.jsonl` for supervised candidates, `generate-inputs.jsonl` for Generate caller rows, and `edit-inputs.jsonl` only for rows with actual checked starting code. It retains full requests, raw replies, parsing/rejection diagnostics, usage, model identity, source hashes and LangSmith trace IDs per batch/attempt. `--prepare-only` exposes the exact contexts before calls. Source IDs are allowlisted; original locators, IDs and family joins are assigned by application code.

From the repository root, a bounded eight-call run is:

```powershell
& ../mathmath/.venv/Scripts/python.exe tools/generate_instruction.py --output dataset/cpa-instructions --calls 8 --rows-per-call 24 --workers 4
```

This requests at most 192 candidates, split evenly between tasks. Add `--prepare-only` to inspect context first; repeat the same command with `--resume` to skip completed calls and retry failed calls once. The system context includes the documented `G01-G17` classification definitions. Mathematical review remains an instruction-stage decision: the two traced pilots in `dataset/cpa-instructions-pilot-20261007*` retained impossible segment intersections despite valid schemas; their `supervision.json` files identify the held drafts. Never treat schema checks or model notes as mathematical acceptance.

Optional `supervision.json` records `rows` with an existing `id`, `decision` (`usable_instruction` or `needs_revision`) and concrete `reason`. On snapshot/resume, marked `needs_revision` cases and their exact duplicates stay in the proposal archive but are excluded from caller inputs. An unreviewed instruction remains a candidate; an instruction review never approves a missing target or Edit starting diagram.

For the current Auxiliary Line batch, Edit is a purposeful auxiliary addition to existing geometry. Numeric/relation replacements, removals, labels and colour edits are excluded. Generate may retain original source measurements, but changing measurements alone is not a new case. The instruction runner screens number/point-name substitutions, reports `number_or_label_variants`, supplies prior source-scoped cases with `--existing`, and rejects repeated screened cases. This conservative text screen does not establish semantic uniqueness or mathematical validity; equivalent phrasing/definitions still need review.

After recording review, use the same `--output` with `--review-only` to refresh caller inputs without any model call. This uses the saved source snapshot and retains all raw batches.

An Edit draft stores its complete `starting_givens` in offline provenance. `--bases` accepts caller-checked Generate records and copies an unambiguously matching actual `target_tikz` into `current_tikz`. Drafts awaiting code remain outside Edit caller inputs. Deterministic schema, scope, source-parent, boilerplate and exact-duplicate checks do not certify mathematical validity. Inspect source facts, branches, purposeful augmentation and semantic duplicates before treating proposals as usable instructions. Keep targets/rubrics out of instruction-model context.

## 1. Source selection

Work only with geometry problems in grades 6–12. Preserve known grade/book metadata; use `null` when a supplied problem's exact grade is not established, after checking that its content fits the permitted school level. Do not infer grade or complexity from filenames alone.

| Source pool | Read and preserve | Selection rule |
| --- | --- | --- |
| `docs/dataset-selection/grade-*.problems.jsonl` | Original record ID and text, manifest line, book/role, source kind, `source_md`, source line range, image paths and classification. Resolve `source_md` against `C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums` and check the actual source. | Begin with `decision: prepared`, then independently select a complete geometry problem with substantial, recoverable givens. Do not assume its existing diagram tags or selection reason establish suitability. |
| `Onn_generate/*.tex` | Complete statement and all its subparts; exact file/line/problem locators. Preserve any supplied TikZ separately as source evidence. | Select by mathematical configuration. Preambles, style files, orphaned solution fragments and isolated figures are not problems. Solutions and supplied TikZ are unverified supporting material. |
| `[L9CB]_2025_10_10.pdf` | File hash, one-based PDF page index, printed page label, section/exercise number and checked transcription. | Select complete geometry problems with recoverable symbols, inequalities and branch conditions. Inspect the page when the text layer is incomplete. |

Select problems whose givens involve interacting geometric dependencies: for example, an altitude followed by midpoint/reflection/intersection constructions; circles with secants, tangents and specified branches; or several dependent objects whose incidence/order matters. Judge the actual configuration, not the number of points, statement length or computational difficulty. There is no numerical minimum of objects or givens.

Skip basic recognition and elementary length-reading configurations, including the user's examples:

- A regular hexagon `ABCDEF` described only by a source figure and `OA = 6 cm; BF = 10.4 cm`.
- A segment `PQ = 12` with `E` its midpoint and `F` the midpoint of `PE`, followed by a length calculation.
- A bare standard triangle/polygon/circle with only its name or measurements and no substantial interaction of constructions.

The same primitive can occur inside a selected complex configuration. Do not reject every midpoint, regular polygon or right triangle by keyword. Do not rescue a trivial source by attaching unrelated constructions merely to pass the filter.

Separate original givens, newly defined objects, proof/calculation goals, and solution facts. Read later subparts because they may introduce legitimate construction data. A proved conclusion must not silently become an assumption. Recover figure-dependent facts only from the actual cited figure or explicit source text; if they cannot be established, record `needs_review` and exclude the source from generation.

Current source examples and hazards, verified during skill preparation:

- `grade-8.problems.jsonl`, record `grade_8_sgk_1-L4197`, describes a right triangle, altitude `AH`, and midpoints `I` of `AH` and `K` of `HB`. The perpendicularities requested in its proof are conclusions, not initial givens. Verify against `8/grade_8_sgk_1/book.final.md`, recorded lines 3978–4003.
- `Onn_generate/main.tex`, Bài 6, statement lines 317–324, duplicates `Onn_generate/test.tex`, Bài 6, lines 12–18. Later parts add the second intersection `E`, midpoints `M,I`, and intersection `F`; select dependency-complete subsets.
- `Onn_generate/0410.tex`, Bài 1–3, duplicates the classroom Bài 1–3 on printed page 2 of the PDF. Retain both locators in one source family.
- The PDF body is largely absent from its searchable text layer. Its homework Bài 3 on printed page 3 contains a second-circle/second-intersection configuration; the branch for `K` needs explicit checking because `B` already lies on the stated line and circle.
- Some embedded Onn TikZ is malformed or mismatched to its statement. For example, `main.tex:343` contains literal escaped newlines, and the circle figure around lines 67–86 does not match the preceding triangle statement. Treat these as inspection examples, not as an exhaustive error list.

Line numbers are navigation aids. Preserve hashes and source text so a later file edit cannot silently change a sample's identity.

## 2. Instructions contain mathematical givens

Use concise Vietnamese mathematical statements and standard notation. State the configuration the drawing must satisfy. Natural sentences are welcome; do not pad them with a narrative about how to draw.

- Define every named object and preserve distinctions between a segment, ray, supporting line, chord, minor/major arc and projected spatial object.
- Preserve inequalities, units, nondegeneracy, order, inside/outside conditions and intersection branches. State a second intersection as distinct from the already known one when that interpretation is verified.
- Remove proof questions, calculation requests, textbook scaffolding and references such as “the figure above.” Keep the source link concise; do not copy the full source statement into each record.
- Keep necessary mathematical construction definitions: “`H` is the foot of the altitude from `A` to `BC`” and “`E` is the second intersection of `AD` with `(O)`” are valid givens for drawing.
- Exclude sequential drawing recipes: "place `H` here, then connect these points." Keep mathematical definitions such as an altitude or the circumcircle of `CDE`, without prescribing point placement or drawing order. Do not introduce a coordinate frame, special angle, numerical ratio or orientation merely because the target uses it internally.
- Do not append generic visibility inventories such as “Các đoạn ... thuộc hình” or “Hình gồm ...”. State purposeful auxiliary objects through their mathematical definitions and roles. Omit redundant visibility prose; do not replace it with another stock sentence or a mathematical role unsupported by the selected givens.
- Do not add “draw accurately/beautifully/clearly” boilerplate, TikZ implementation instructions, source IDs, rubric details or evaluation terminology to model inputs.

If the givens leave geometric freedom, keep that freedom. A target is one valid realization. Sample valid free parameters for varied targets and record them as layout choices; do not promote them to source givens. Reference-distance disagreement alone can reject another valid realization, so it must not be treated as proof of instruction failure.

Presentation can vary after the mathematical case is fixed. Sample one concise phrasing per case, reorder only independent clauses whose prerequisites have been introduced, and vary clause grouping or equivalent natural/symbolic definitions. Preserve correspondence lists, angle vertices/direction, ratio operand order, units, inequalities and branches. Repeated standard terms are acceptable; redundant facts and unusual synonyms are not a diversity strategy. Record sampling seeds/choices outside model inputs. Review exact and semantic duplicates separately from presentation variety; a paraphrase is not a new mathematical case.

### Generate example

From the initial statement of `Onn_generate/main.tex` Bài 6:

> Đường tròn (O) có đường kính AB. C thuộc (O), C khác A và B, AC < BC. H là trung điểm BC. Tiếp tuyến của (O) tại B cắt tia OH tại D.

This describes a geometric configuration. It does not instruct the model to place points or connect a prescribed sequence. It does not assume the later claim that `DC` is tangent.

If the selected scope includes the next construction, extend the givens with:

> Đường thẳng AD cắt (O) tại E khác A; M là trung điểm AE.

Do not append the proof conclusion that `D,B,M,C` are concyclic as an assumed constraint.

### Edit example

When the actual `current_tikz` contains `ABC`, altitude `AH` and their labels:

> I, K là trung điểm AH, HB.

The input is that instruction plus the complete starting TikZ. The output is the complete updated TikZ. Edit instructions state only the mathematical change: additions use direct definitions, without “Bổ sung/Thêm” prefixes or “Giữ nguyên ...” lists. Include existing facts only when needed to disambiguate a replacement/removal. Preserving unaffected objects, recomputing affected dependencies and keeping the existing frame are default behavior. A mathematical repair may start from compiling but incorrect geometry; record the introduced error and requested correction.

Prefer varied purposeful auxiliary additions: projections/heights, medians/midsegments, parallels, bisectors, reflection carriers, radii/contact lines and explicitly branched intersections. Point-only padding, no-op edits, measurement changes, label renaming, colour changes and repeated "add a midpoint" templates do not count.

## 3. Target TikZ has one authority

Read the actual [TikZ harness prompt](../../mathmath/src/agent/prompts/tikz.py) at batch start. Pin its `TIKZ_PROMPT_VERSION` and SHA-256, together with the applicable [task prompt](../../mathmath/src/agent/prompts/problem_tikz.py) and [validator/wrapper](../../mathmath/src/agent/latex/tikz.py). Do not use `new_instruction.md` or copied historical prompt text as a second authority. A source-profile change starts a new batch/profile revision.

Follow the prompt's full source contract. The essential envelope is one ordinary `tikzpicture`, without Markdown, preamble, document wrapper or comments. Its four source groups are independent parameters, dependent constructions/helpers, visible strokes/annotations, then point markers/labels. Keep constrained points expressed through named dependencies; keep undrawn helpers out of the bounding box; follow the prompt's guidance for choosing and inspecting label positions.

Preserve given lengths and ratios. Use the shared prompt's default coordinate units and natural visible bounds, with one uniform picture-level scale when a requested size or readability needs adjustment. Preserve supplied coordinate-system values, measurement labels and existing edit frames.

Use only the existing wrapper's supported commands/libraries. Supplied `.tex` files and `mathmath.sty` are source documents, not extra dependencies to ship with a target. Convert useful constructions to the shared target format and record repairs. A supplied diagram is not an approved target until it matches the chosen instruction and has been validated and inspected.

Apply the entire `Relation marks` section of the prompt when producing the target: matching ticks for equal-segment classes, matching arc counts for equal-angle classes including angle-bisector halves, corners for perpendicularity/right angles, and requested angle text attached to its angle pic. Required relations must hold geometrically and carry the prescribed visible marks. Use the canonical prompt for carrier selection, equality-class patterns, intended angle sectors and implementation. Do not turn every property of a named shape or an unproved conclusion into a compulsory mark. Add numerical measurements only when requested. These are shared drawing conventions; instructions need not repeat symbol-placement commands for their mathematical givens.

Inspect the actual render for every applicable mark: presence, correct carrier/vertex and angle sector, consistent patterns within an equality class and distinct patterns for unrelated classes, attached angle text when requested, and readability. Compilation or correct coordinates alone do not satisfy these requirements. Missing, misplaced or inconsistent required marks keep the target a candidate until corrected; record the review separately.

## 4. Shared evaluation and pair-specific requirements

Use the shared evaluator described in [docs/evaluation.md](../docs/evaluation.md). Compile, target-relative rendered content and output collisions use the common implementation. Do not create repeated prose criteria for those dimensions in every row.

Mathematical predicates such as `perpendicular` and `equal_length` test the relation, not the presence of its symbol. Rendered-content comparison checks marks against the target; it cannot establish that a required mark omitted from both target and output should have been present. Enforce the shared relation-mark convention when reviewing targets rather than treating a mathematical predicate pass as evidence of complete notation.

Retain the existing `evaluation_rubric` field for the small list of pair-specific mathematical requirements. Its entries use the evaluator's current structure:

```json
{
  "id": "altitude_h",
  "dimension": "mathematical_correctness",
  "requirement": "H lies on the supporting line BC and AH is perpendicular to BC.",
  "checks": [
    {"op": "collinear", "points": ["H", "B", "C"]},
    {"op": "perpendicular", "points": ["A", "H", "B", "C"]}
  ]
}
```

This is a convention example, not a dataset row. `requirement` records the meaning; `checks` execute it. All checks in an entry must hold. Criterion IDs are unique within a row. Do not infer strict `between` from an altitude definition when the foot may be on the extension. For Edit, requirements describe the completed diagram and include the mathematical invariants that must be preserved.

Supported predicates and operand order are owned by [evaluation/tikz_geometry.py](../evaluation/tikz_geometry.py):

| Predicate | Ordered points and meaning |
| --- | --- |
| `perpendicular`, `parallel` | `[A,B,C,D]`: compare the lines with directions `AB` and `CD`. |
| `equal_length`, `length_ratio`, `shorter` | `[A,B,C,D]`: compare `|AB|` and `|CD|`; `length_ratio` requires a positive finite `value = |AB|/|CD|`; `shorter` is strict. |
| `collinear` | `[A,B,C]`. |
| `midpoint` | `[M,A,B]`: `M` is the midpoint of `AB`. |
| `distinct` | `[P,Q]`: explicitly require two named points to differ; unrelated coincident points remain allowed. |
| `between` | `[P,A,B]`: `P` is strictly inside segment `AB`. |
| `same_ray` | `[P,O,A]`: `P` lies on ray `OA` and differs from `O`. |
| `on_circle`, `outside_circle` | `[P,O,A]`: circle centre `O`, radius `|OA|`; for membership use an independent radius witness, not `P=A`. |
| `minor_arc` | `[P,O,A,B]`: `P` lies strictly inside minor arc `AB` of the circle centred at `O`; the minor arc must be defined. |
| `concyclic` | `[A,B,C,D]`: four distinct concyclic points. |
| `tangent` | `[O,R,A,B]`: line `AB` tangent to the circle centred at `O`, radius `|OR|`; this does not specify the contact point by itself. |
| `tangent_circumcircle` | `[A,B,C,D,E]`: line `AB` tangent to the circumcircle through noncollinear `C,D,E`. |

Checks use actual visible mathematical point labels, including their true primes/subscripts where supported by extraction, rather than TikZ helper variable names. Do not add visible helper labels only to satisfy a predicate. Never substitute a tautological check for a missing check.

Record only conditions required by the instruction or its defining constructions, not all theorems true of the target. Shared evaluator tolerances apply; do not tune per-row tolerances after observing a failure. An empty entire list is allowed only when there is no additional pair-specific mathematical requirement, with the reason recorded in review notes; it is not a way to omit unsupported givens.

For an unsupported mathematical requirement, retain an entry with its real `requirement` and `checks: []`, and record independent review evidence. Do not invent an operator or represent unknown as pass. Point predicates alone do not verify a painted circle, numeric-label attachment, a general angle constraint or a 3D relation. Inspect the target and record the evidence needed for those properties. Screen-space checks must not be used to certify spatial perpendicularity.

The current evaluator reports unsupported entries as unknown. Manual review can establish that a training target satisfies them, but does not make the automatic evaluator support them. Likewise, prose about allowed alternative shapes does not configure the current reference comparator. Keep these limits in review notes.

## 5. JSONL records and output paths

After the instruction stage, write complete target/rubric examples to `dataset/<batch-id>/generate.jsonl` and `dataset/<batch-id>/edit.jsonl`. These are later training/evaluation artifacts, not the instruction-stage deliverable. Use UTF-8 without a BOM, one JSON object per physical line, a final newline, and standard JSON serialization with `ensure_ascii=False` and `allow_nan=False`. Serialize TikZ newlines/backslashes correctly; do not hand-escape or store Markdown fences.

Each row has these fields. Required nullable fields stay present as `null`; omitted optional source metadata must not be guessed.

| Field | Contract |
| --- | --- |
| `schema_version` | Exact string `synthetic-tikz:v1`. |
| `id` | Unique, persistent string identifying this task instance/revision. Never reuse an ID for changed inputs or target. |
| `task` | `Generate` or `Edit`, matching the containing file. |
| `instruction` | Nonempty mathematical-givens instruction under section 2. |
| `current_tikz` | `null` for Generate; a nonempty complete starting picture for Edit. |
| `target_tikz` | Nonempty complete target under section 3. Incomplete generation attempts are not example rows. |
| `grade` | Integer 6–12 when supported by the source, otherwise `null`; rows known to be outside grades 6–12 are excluded. |
| `diagram_types` | Nonempty array of applicable geometry codes `G01`–`G17` from [the taxonomy](../docs/diagram-k12-vn.md), checked against the actual configuration. |
| `source_group` | ID linking this record to its original problem family. |
| `split` | `null` until assigned; then `train`, `validation` or `test`. A source group has exactly one assignment across all batches. Do not invent split proportions. |
| `evaluation_rubric` | Array of entries defined in section 4. Never included in drawing-worker input. |

Keep a source-decision log in `dataset/<batch-id>/selection.jsonl`, with `{source_group, source_path, source_sha256, locator, decision, reason}`. `decision` is `selected`, `skipped` or `needs_review`; an unassigned source group may be `null`. This log is an audit artifact, never a training file. Record a specific reason such as basic recognition, incomplete givens, duplicate source or conflicting evidence.

Training export uses only `instruction` and, for Edit, `current_tikz` as model inputs, with `target_tikz` as the desired response. Keep rubrics available offline. Export only ready rows with assigned splits; never include a target/rubric as generation context.

## Final Parquet export for Hugging Face

Export the completed reviewed dataset to Parquet for Hugging Face after target verification, deduplication and source-family split assignment. Preserve the actual task inputs, target TikZ and provenance; keep rubrics/evaluation metadata outside generation inputs. PyArrow is required for drawing snapshots and export, and is pinned in [requirements.txt](../requirements.txt).

The [drawing runner](../tools/draw_instruction.py) consumes explicit caller JSONL after instruction authoring, without inferring task or starting state from filenames or IDs. Copy the final instruction/source verbatim; assign `task` and `source_group` from audited decisions. Every input has `current_tikz`: `null` for Generate, complete actual starting TikZ for Edit. The caller obtains it from a checked Generate result or an existing checked diagram and copies the chosen source into the Edit record before invocation. The runner neither selects a starting diagram nor injects its original prompt. Include existing mathematical context only when needed to disambiguate the Edit; do not repeat unchanged givens. Failed attempts remain run artifacts, not completed dataset rows.

Drawing may preserve a structurally valid supplied `target_tikz` without approving it. `--resume` reuses the latest completed target only for matching task, instruction, actual `current_tikz`, source and family. A failed or incomplete drawing is retried even if it returned partial TikZ. `--retry-id` explicitly redraws a selected completed target after a mathematical/visual defect is found. Each command makes at most one bounded drawing attempt per pending row; `--limit` counts pending rows. Completed targets require no model/compiler calls during reuse. This is drawing completion, not mathematical readiness.

Each row's latest outcome is saved through an atomic checkpoint before returning, and `candidates.jsonl` is rebuilt as one latest row per ID. Resuming a subset preserves other saved rows. Retry attempts and each invocation's input/profile snapshots stay in separate directories. Use one process per run directory. A retry starts from the original explicit instruction/current TikZ, keeps prior attempts offline, and never promotes a failed output to Edit input automatically.

Drawing supports 1–32 workers; default 4. Measure matched batches at higher concurrency using the report's elapsed time, successful new drawings per minute and failures. Each result still passes through one snapshot writer. The orchestrator follows the skill's shared strategy until 1,500 reviewed unique pairs per task; candidate completions and throughput replicas never inflate that count.

The shared compiler currently admits two operations, returning HTTP 503 when busy. Drawing therefore queues compiler operations locally with `--compiler-concurrency` (1–2, default 2) while model workers remain independent. The gate precedes native HTTPX streaming because the existing compiler SDK overrides its pool timeout to three seconds. No new compiler or model-regeneration loop is introduced. Preserve the native error/checkpoint if other clients saturate the shared service; do not call a transport failure a mathematical failure. Render artifacts use a short UUID directory outside the longer case-checkpoint paths to avoid Windows path-length failures; prior attempt paths remain unchanged.

The runner also atomically replaces `candidates.parquet` after every completed result, including failures. It contains one latest row per ID; retries replace that row and subset resumes retain other saved results. Per-row JSON checkpoints remain the recovery source if snapshot writing is interrupted. The single writer runs outside the drawing workers. A closed Parquet snapshot requires rewriting its accumulated rows; this is appropriate for the planned roughly 1,500 rows per task, while substantially larger runs should use fragments.

`tikz_image` embeds the target PNG as `{bytes, path}` with Hugging Face Image feature metadata, following [HF's PyArrow image format](https://huggingface.co/docs/hub/datasets-pyarrow#embed-images-inside-parquet) and its [feature reader](https://github.com/huggingface/datasets/blob/main/src/datasets/features/features.py). It uses the source/PNG pair returned by the native render, with both hashes retained, or exact-target evidence from the shared compile helper. Parquet metadata also carries `target_tikz_sha256` and `tikz_image_sha256` for the embedded pair, preserving original attempt evidence separately. A changed target, changed PNG, missing file or absent binding yields a null image unless valid exact-target compile evidence is available. Final reviewed exports require a matching, valid PNG and embed its bytes; they do not depend on local image paths. Supplied unrendered targets stay candidates with null images until compiled through the shared helper. Candidate snapshots are not approval or split assignment.

For this runner's final export, actual review is recorded in `verification.status: ready`, `reviewed_by`, and `reviewed_input_sha256`, computed with its `review_digest` after task, instruction, current/target TikZ, target PNG, rubric and source-family provenance are final. The digest includes the verified PNG's actual bytes hash; changing the image also invalidates the recorded review. These fields attest the recorded review; computing a digest does not perform that review. `--export` validates them and the supplied rows' family/split consistency without a model or compiler call. It also rejects an original parent occurring in different splits across tasks, even under different family names. Cross-batch family/duplicate review remains required. Final Parquet uses ordinary input/target columns and lossless JSON strings for heterogeneous offline rubric/metadata; only populated task/split files are written.

The instruction runner, drawing caller and final export share the same stock-prose check. It rejects known boilerplate and bare carrier-list clauses such as `OM và ON.` or `Các đoạn BA′, CA′.`, including assistant revisions. It allows mathematical predicates such as `AB, AC vuông góc.` This is a syntax screen; it does not verify an auxiliary's role, source fidelity or semantic uniqueness.

## 6. Controlled augmentation and split integrity

Preserve the original source text. Build additional variants through explicit operations:

| Type | What may change | What must be checked |
| --- | --- | --- |
| `subset` | Active construction/givens subset. | Retain all defining dependencies and a substantial drawing; remove unsupported downstream objects together. |
| `rephrase` | Wording or a consistent symbol mapping. | Preserve mathematical meaning, branch/order, measurements and scope. |
| `construct` | Add a mathematically defined auxiliary. | State its definition, existence/branch conditions and visible role; identify it as synthetic. |
| `change_instance` | A genuinely different compatible construction/scope in Generate. | Measurements/renaming alone do not qualify; excluded from this batch's Edit task. |
| `derive` | A consequence of active premises. | Record the rule/derivation and verify its hypotheses. One numerical realization is not proof. Do not smuggle proof goals into the original givens. |
| `render_variant` | Valid free parameters or allowed presentation. | Preserve the active givens and target source profile. Distinguish mathematical parameter changes from layout freedom. |

There is no per-source ceiling on valid variants. Each actual production run still has a declared scope and bounded call budget. Revalidate each new instance; a descendant does not inherit target approval merely from its parent.

Group givens by compatible mathematical configuration and defining dependencies before augmentation. An auxiliary must serve a particular relationship or comparison in that configuration, have defined parents/carriers, exist on the intended branch, and contribute a specified visible mathematical object. Preserve supporting-line versus segment/ray distinctions and revalidate dependents after an Edit. Prefer explicit later-subpart constructions, then verified solution auxiliaries, then deliberate synthetic additions; record their origin separately from premises and proof conclusions. The [skill](../.agents/skills/synthetic-tikz/SKILL.md) provides the full-pool grouping and auxiliary-selection procedure and concrete examples.

Variation should come from source families, construction subsets, branch-valid parameter choices, combinations of relations and Edit operations. Mix these according to the real selected pool; avoid a fixed sentence template or cycling a single construction throughout the batch. Record seeds and actual sampled values. Renaming points or swapping two numbers alone does not establish a diverse mathematical dataset.

For Generate, semantic duplicate review compares complete givens and visible scope modulo equivalent wording/definitions, consistent symbol renaming and unit conversion. For Edit, it also compares the intended starting mathematical configuration, actual change and resulting scope; repeated edit text alone does not establish duplicate input pairs. Preserve meaningful parameter, branch and scope differences. Do not fill counts with wording changes or uniform rescaling. Audit repeated openings, clause patterns and operation concentration separately from counts of mathematical cases.

All variants of an original problem remain in the same `source_group` and split, across both tasks and every batch. Join duplicate sources before assigning splits, including copies across TeX/PDF and curriculum books. Different paths, text hashes, labels or wording do not prove independent givens. Subset augmentation can create a duplicate of another family's complete givens; merge groups or withhold the cross-split duplicate. Sharing a generic premise alone does not make two problems duplicates.

For multiple parents, retain all parent IDs and resolve their families to one group before export. Never combine parents from different assigned splits. Before export, check group assignments against existing batches, exact duplicates of input/target content, and reviewed semantic duplicate candidates. Do not use held-out examples as training-generation prompts or repair demonstrations. Persist assignments; rerunning a batch must not resplit the same family.

## 7. Readiness and evidence

A complete instruction/target pair starts as `candidate`. It becomes `ready` only after:

1. Source identity, substantial givens and chosen scope are checked; synthetic changes and any repaired ambiguity are recorded.
2. The target follows the pinned source profile, compiles with the shared wrapper, and its actual render has been inspected for required objects, ratios, branches, annotations and collisions.
3. Pair-specific mathematical conditions are verified against the target. Any unsupported requirement has concrete independent review evidence; unresolved mandatory conditions keep the row a candidate.
4. For Edit, the actual starting picture and completed target demonstrate the requested change and preservation. Evidence is tied to both exact inputs and the target.
5. Source-group lineage and duplicate checks are consistent. Split assignment is required before training/evaluation export, rather than before drafting.

This readiness means a reviewed training pair. It does not turn unsupported automatic checks into passes or establish calibrated model-evaluation accuracy. Model self-reported success and target-versus-itself agreement do not establish source fidelity. Report automatic preparation, repairs and curation separately.

Use the existing compiler, drawing harness and evaluation entry points with explicit task inputs. The local skill's [compile helper](../.agents/skills/synthetic-tikz/scripts/compile.py) provides compilation and artifact capture for separately authored or repaired JSONL targets. It snapshots the actual harness profile, preserves inputs and source metadata, and emits candidate copies with evidence paths; it does not select sources, generate targets, certify the complete record schema or automatically approve/export training data. Its report hashes task, instruction, current/target TikZ, rubric and profile separately from later review metadata. Recompile after changing any of those bound values; review notes/readiness updates alone do not change that evidence. Instruction generation does not invoke the compiler or drawing harness.

The older `tools/prepare_tikz_candidates.py` and `tools/evaluate_tikz_candidates.py` are bounded historical experiments; their old per-dimension prose rubric or compiler imports do not define this contract.
