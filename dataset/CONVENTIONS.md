# Synthetic geometry data: Generate and Edit

Contract version: `synthetic-tikz:v1`.

This is the operational reference for new Generate and Edit batches in this repository. It defines authoring and record conventions; it does not claim that the older preparation scripts already implement them. The local skill is [synthetic-tikz](../.agents/skills/synthetic-tikz/SKILL.md). Existing source files and historical experiments remain unchanged.

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
- Remove proof questions, calculation requests, textbook scaffolding and references such as “the figure above.” Keep the source statement intact in provenance.
- Keep necessary mathematical construction definitions: “`H` is the foot of the altitude from `A` to `BC`” and “`E` is the second intersection of `AD` with `(O)`” are valid givens for drawing.
- Exclude sequential drawing recipes: "place `H` here, then connect these points." This concerns drawing implementation, not mathematical construction definitions or particular verbs: "draw altitude `AH`" and "add segment `AK`" can identify required objects. Do not introduce a coordinate frame, special angle, numerical ratio or orientation merely because the target uses it internally.
- A short visibility clause is allowed when needed to select an auxiliary, segment, measurement, arc or line role. Name the required mathematical objects without prescribing point placement or drawing order. A statement such as "include the circumcircle of `CDE`" defines scope without specifying a drawing algorithm.
- Do not add “draw accurately/beautifully/clearly” boilerplate, TikZ implementation instructions, source IDs, rubric details or evaluation terminology to model inputs.

If the givens leave geometric freedom, keep that freedom. A target is one valid realization. Sample valid free parameters for varied targets and record them as layout choices; do not promote them to source givens. Reference-distance disagreement alone can reject another valid realization, so it must not be treated as proof of instruction failure.

### Generate example

From the initial statement of `Onn_generate/main.tex` Bài 6:

> Đường tròn (O) có đường kính AB. C thuộc (O), C khác A và B, AC < BC. H là trung điểm BC. Tiếp tuyến của (O) tại B cắt tia OH tại D.

This describes a geometric configuration. It does not instruct the model to place points or connect a prescribed sequence. It does not assume the later claim that `DC` is tangent.

If the selected scope includes the next construction, extend the givens with:

> Đường thẳng AD cắt (O) tại E khác A; M là trung điểm AE.

Do not append the proof conclusion that `D,B,M,C` are concyclic as an assumed constraint.

### Edit example

When the actual `current_tikz` contains `ABC`, altitude `AH` and their labels:

> Thêm I là trung điểm AH, K là trung điểm HB cùng các đoạn IK, AK, CI. Giữ nguyên tam giác ABC và đường cao AH.

The input is that instruction plus the complete starting TikZ. The output is the complete updated TikZ. An edit must change the geometry/content requested, preserve unaffected objects and recompute dependencies affected by a changed given. Keep the existing frame unless changing it is part of the request. A mathematical repair may start from compiling but incorrect geometry; record the introduced error and requested correction.

Prefer varied meaningful edits: add/remove a coherent construction, change a stated parameter, replace a defining relation, or correct a specific mathematical defect. Do not fill a batch with no-op edits, label renaming, colour changes or the same “add a midpoint” operation.

## 3. Target TikZ has one authority

Read the actual [TikZ harness prompt](../../mathmath/src/agent/prompts/tikz.py) at batch start. Pin its `TIKZ_PROMPT_VERSION` and SHA-256, together with the applicable [task prompt](../../mathmath/src/agent/prompts/problem_tikz.py) and [validator/wrapper](../../mathmath/src/agent/latex/tikz.py). Do not use `new_instruction.md` or copied historical prompt text as a second authority. A source-profile change starts a new batch/profile revision.

Follow the prompt's full source contract. The essential envelope is one ordinary `tikzpicture`, without Markdown, preamble, document wrapper or comments. Its four source groups are independent parameters, dependent constructions/helpers, visible strokes/annotations, then point markers/labels. Keep constrained points expressed through named dependencies; keep undrawn helpers out of the bounding box; use the prompt's point/mark batching and geometric label placement.

Preserve ratios. Numerical givens do not force physical centimetres on the canvas. Follow the prompt's shared reference-length normalization, with its explicit exceptions for coordinate systems, physical-size requests and existing edit frames. Source givens and dimensionless ratios remain unchanged.

Use only the existing wrapper's supported commands/libraries. Supplied `.tex` files and `mathmath.sty` are source documents, not extra dependencies to ship with a target. Convert useful constructions to the shared target format and record repairs. A supplied diagram is not an approved target until it matches the chosen instruction and has been validated and inspected.

Apply the entire `Relation marks` section of the prompt when producing the target: matching ticks for equal-segment classes, matching arc counts for equal-angle classes including angle-bisector halves, corners for perpendicularity/right angles, and requested angle text attached to its angle pic. Required relations must hold geometrically and carry the prescribed visible marks. Use the canonical prompt for carrier selection, equality-class patterns, intended angle sectors and implementation. Do not turn every property of a named shape or an unproved conclusion into a compulsory mark. Add numerical measurements only when requested. These are shared drawing conventions; instructions need not repeat symbol-placement commands for their mathematical givens.

Inspect the actual render for every applicable mark: presence, correct carrier/vertex and angle sector, consistent patterns within an equality class and distinct patterns for unrelated classes, attached angle text when requested, and readability. Compilation or correct coordinates alone do not satisfy these requirements. Missing, misplaced or inconsistent required marks keep the target a candidate until corrected; record the review with the existing verification evidence.

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
| `between` | `[P,A,B]`: `P` is strictly inside segment `AB`. |
| `same_ray` | `[P,O,A]`: `P` lies on ray `OA` and differs from `O`. |
| `on_circle`, `outside_circle` | `[P,O,A]`: circle centre `O`, radius `|OA|`; for membership use an independent radius witness, not `P=A`. |
| `minor_arc` | `[P,O,A,B]`: `P` lies strictly inside minor arc `AB` of the circle centred at `O`; the minor arc must be defined. |
| `concyclic` | `[A,B,C,D]`: four distinct concyclic points. |
| `tangent` | `[O,R,A,B]`: line `AB` tangent to the circle centred at `O`, radius `|OR|`; this does not specify the contact point by itself. |
| `tangent_circumcircle` | `[A,B,C,D,E]`: line `AB` tangent to the circumcircle through noncollinear `C,D,E`. |

Checks use actual visible mathematical point labels, including their true primes/subscripts where supported by extraction, rather than TikZ helper variable names. Do not add visible helper labels only to satisfy a predicate. Never substitute a tautological check for a missing check.

Record only conditions required by the instruction or its defining constructions, not all theorems true of the target. Shared evaluator tolerances apply; do not tune per-row tolerances after observing a failure. An empty entire list is allowed only when there is no additional pair-specific mathematical requirement, with the reason recorded in verification notes; it is not a way to omit unsupported givens.

For an unsupported mathematical requirement, retain an entry with its real `requirement` and `checks: []`, and record independent review evidence. Do not invent an operator or represent unknown as pass. Point predicates alone do not verify a painted circle, numeric-label attachment, a general angle constraint or a 3D relation. Inspect the target and record the evidence needed for those properties. Screen-space checks must not be used to certify spatial perpendicularity.

The current evaluator reports unsupported entries as unknown. Manual review can establish that a training target satisfies them, but does not make the automatic evaluator support them. Likewise, prose about allowed alternative shapes does not configure the current reference comparator. Keep these limits in the verification record.

## 5. JSONL records and output paths

Write complete examples to `dataset/<batch-id>/generate.jsonl` and `dataset/<batch-id>/edit.jsonl`. Use UTF-8 without a BOM, one JSON object per physical line, a final newline, and standard JSON serialization with `ensure_ascii=False` and `allow_nan=False`. Serialize TikZ newlines/backslashes correctly; do not hand-escape or store Markdown fences.

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
| `source_group` | Persistent ID for the original problem family, shared by all copies, tasks and descendants. |
| `split` | `null` until assigned; then `train`, `validation` or `test`. A source group has exactly one assignment across all batches. Do not invent split proportions. |
| `evaluation_rubric` | Array of entries defined in section 4. Never included in drawing-worker input. |
| `provenance` | Source and production record defined below. |
| `augmentation` | Parentage and controlled changes defined below. |
| `verification` | Readiness and evidence record defined below. |

`provenance` contains:

- `sources`: nonempty array of `{kind, path, sha256, locator, source_text, metadata}`. `kind` is `curriculum`, `tex` or `pdf`. Preserve the original complete problem text, including its questions, before rewriting. Hash source file bytes. Repository paths are relative; external curriculum paths are absolute. For curriculum records, `path` identifies the manifest, `locator` has `record_id` and one-based `jsonl_line`, and `metadata` preserves the original record's remaining fields plus the verified corpus file path/hash. For TeX, use one-based `start_line`, `end_line` and `problem_label`; for PDF, use one-based `page_start`, `page_end`, the printed page label and section/problem label. Preserve every known duplicate-source locator and any evidence used to recover a figure-dependent fact.
- `selection_reason`: one concrete explanation of the interacting geometry that makes the source suitable.
- `run_id`: the batch/run identifier; `preparation_route`: `automatic`, `deterministic_repair`, `model_assisted_repair` or `assistant_curation`, reflecting the actual production route.
- `model` and `langsmith_trace_id`: actual model/trace identifiers for real provider calls, or `null` when not applicable. `run_id` resolves to saved attempts, call settings and repairs under `runs/<batch-id>/`. Never invent a trace or call something automatic after unrecorded curation.
- `harness_profile`: actual `tikz_prompt_version`, plus `files`, an array of `{path, sha256}` for the common prompt, task prompt and validator/wrapper. Preserve the corresponding snapshots in run artifacts so a mutable working tree cannot change the profile retrospectively.

`augmentation` contains `parent_ids` (array), `operations` (ordered array), `seed` (integer or `null` when no randomized sampler was used), and `parameters` (object containing the actual changed/free values and symbol mapping). Use empty parent IDs when deriving directly from the recorded source. Empty operations mean its givens and construction scope are unchanged apart from ordinary instruction cleanup. A selected subconfiguration still records `subset`, even without an earlier dataset parent. Each operation has `type` and a concrete `change`; section 6 defines the types. Record affected mathematical facts, not just “augmented.”

`verification` contains `status` (`candidate` or `ready`), `report_path` (saved evidence path or `null` before checking), `reviewed_by` (actual reviewer identity or `null`), and `notes` (array of unresolved issues, manual checks and scope/equivalence decisions). A verification report must bind the exact instruction, current TikZ, target TikZ, rubric and harness profile by hashes and retain compilation/render evidence. Missing evidence keeps a row a candidate. Do not put secrets in records or artifacts.

Keep a source-decision log in `dataset/<batch-id>/selection.jsonl`, with `{source_group, source_path, source_sha256, locator, decision, reason}`. `decision` is `selected`, `skipped` or `needs_review`; an unassigned source group may be `null`. This log is an audit artifact, never a training file. Record a specific reason such as basic recognition, incomplete givens, duplicate source or conflicting evidence.

Training export uses only `instruction` and, for Edit, `current_tikz` as model inputs, with `target_tikz` as the desired response. Keep provenance, rubrics and verification available offline. Export only ready rows with assigned splits; never include a target/rubric as generation context.

## 6. Controlled augmentation and split integrity

Preserve the original source text. Build additional variants through explicit operations:

| Type | What may change | What must be checked |
| --- | --- | --- |
| `subset` | Active construction/givens subset. | Retain all defining dependencies and a substantial drawing; remove unsupported downstream objects together. |
| `rephrase` | Wording or a consistent symbol mapping. | Preserve mathematical meaning, branch/order, measurements and scope. |
| `construct` | Add a mathematically defined auxiliary. | State its definition, existence/branch conditions and visible role; identify it as synthetic. |
| `change_instance` | Stated quantities, conditions, branches or object relationships. | Record replaced/added/removed givens and revalidate the whole dependent configuration. |
| `derive` | A consequence of active premises. | Record the rule/derivation and verify its hypotheses. One numerical realization is not proof. Do not smuggle proof goals into the original givens. |
| `render_variant` | Valid free parameters or allowed presentation. | Preserve the active givens and target source profile. Distinguish mathematical parameter changes from layout freedom. |

There is no per-source ceiling on valid variants. Each actual production run still has a declared scope and bounded call budget. Revalidate each new instance; a descendant does not inherit target approval merely from its parent.

Variation should come from source families, construction subsets, branch-valid parameter choices, combinations of relations and Edit operations. Mix these according to the real selected pool; avoid a fixed sentence template or cycling a single construction throughout the batch. Record seeds and actual sampled values. Renaming points or swapping two numbers alone does not establish a diverse mathematical dataset.

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

Use the existing compiler, drawing harness and evaluation entry points. The local skill's [compile command](../.agents/skills/synthetic-tikz/SKILL.md#compile-inspect-and-finish) provides executable compilation and artifact capture for authored JSONL. It snapshots the actual harness profile, preserves inputs and source metadata, and emits candidate copies with evidence paths; it does not select sources, generate targets, certify the complete record schema or automatically approve/export training data. Its report hashes task, instruction, current/target TikZ, rubric and profile separately from later review metadata. Recompile after changing any of those bound values; review notes/readiness updates alone do not change that evidence.

The older `tools/prepare_tikz_candidates.py` and `tools/evaluate_tikz_candidates.py` are bounded historical experiments; their old per-dimension prose rubric or compiler imports do not define this contract.
