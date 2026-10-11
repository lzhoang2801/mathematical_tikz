# Synthetic geometry data: Generate and Edit

Contract version: `synthetic-tikz:v2`.

These conventions cover source selection, mathematical instructions and target preparation. The local skill is [synthetic-tikz](../.agents/skills/synthetic-tikz/SKILL.md).

## Resumable production through CPA

Use [tools/run_synthetic_dataset.py](../tools/run_synthetic_dataset.py) for the complete candidate-production loop. It selects context, calls [generate_instruction.py](../tools/generate_instruction.py), draws through the existing [drawing runner](../tools/draw_instruction.py), checkpoints each stage and stops at explicit quotas or budgets. No new agent framework, renderer or evaluator is involved. The instruction model receives the versioned [system prompt](../tools/instruction_prompt.md) with twelve-output Generate and Edit few-shots drawn from the supplied Onn problems and spatial geometry and a batch of `{source, source_text}` or `{source, givens}` inputs. It returns several instructions per input in one call. Audit metadata, hashes, taxonomy and lineage stay local; no rationale or review verdict is requested. Structured calls use the existing [LangChain interface](https://docs.langchain.com/oss/python/langchain/models#structured-output).

The source input is [audit_givens/selection.jsonl](audit_givens/selection.jsonl), consolidated from the grade-specific curation logs. Only `selected` rows enter production. Existing manifest-backed rows must match their manifest and current corpus text. Additional grades 10-12, Onn TeX and PDF rows carry a checked `source_text`, source-file hash and line/page locator. Text sources also preserve `raw_source_text` verbatim; OCR corrections and their evidence stay in the audit ledger. Unresolved mathematical symbols/branches remain `needs_review` and never enter author context. The source loader keeps full problem statements/subparts and the audit's givens, auxiliary origins, branch notes and family. It does not re-extract the corpus or load historical dated batches. Source IDs, provenance and family joins belong to application code.

All synthetic outputs use one directory: `dataset/synthetic/`. Generate/Edit snapshots and checkpoints live at its root; Geo3K Reconstruct outputs live in `reconstruct/`. `dataset/audit_givens/` contains source inputs and `dataset/geo3k-tikz/` is the unchanged upstream data, not extra synthetic runs.

From the 1,128 Generate / 981 Edit checkpoint, add 500 candidates per task and cover every selected source record:

```powershell
python -B tools/run_synthetic_dataset.py --resume --generate 1628 --edit 1481 --base-count 300 --batch-size 30 --contexts-per-call 10 --max-author-calls 160 --max-draw-attempts 3000 --workers 8 --cover-all-sources
```

`--cover-all-sources` keeps the entire selected pool active. It prioritizes records with the fewest completed native bases, then records with the fewest completed Edits. Author attempts break ties but never count as target coverage. Generate continues beyond the base-count minimum when selected records still lack usable bases. Inputs remain only source plus source text or givens; coverage statistics stay local. Export caps retain one representative per parent source record before filling other slots. Source IDs sharing a family rotate across calls and retain that shared lineage; a duplicate instruction alone does not establish coverage of another source.

Coverage mode persists on resume. Completion requires both sample quotas and every selected source ID in each task export; each quota must be at least the number of selected records. `report.json.source_coverage` records per-task covered counts and missing IDs. Provider failures and cumulative call/drawing budgets can still stop a run short; the report must then retain the missing records. The same resume command continues from checkpoints after recovery or a deliberate budget increase.

Earlier pilot command (250 Generate / 250 Edit):

```powershell
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
& ../mathmath/.venv/Scripts/python.exe -B tools/run_synthetic_dataset.py --resume --generate 250 --edit 250 --base-count 100 --batch-size 30 --contexts-per-call 10 --max-author-calls 40 --max-draw-attempts 600 --workers 8
```

For a larger run, set the target quotas and explicit budgets:

```powershell
& ../mathmath/.venv/Scripts/python.exe -B tools/run_synthetic_dataset.py --resume --generate 1500 --edit 1500 --base-count 600 --batch-size 30 --contexts-per-call 10 --max-author-calls 200 --max-draw-attempts 3000 --workers 4
```

The larger-run settings start from 600 native Generate bases and reuse Edit targets for the remaining Generate quota. This reduces the average Edit load per base to 2.5; it is a workload setting, not a guarantee of semantic diversity. `--contexts-per-call 10` supplies up to ten different problems or bases per author call, while `--batch-size 30` requests up to thirty instructions. Use `--contexts-per-call 5` for smaller contexts. Sampling is seeded, shuffled and least-used-first across the full selected pool, with one source group per call so duplicate presentations do not crowd the context; each response retains one exact source/base ID.

Reconstruct continues in the same folder without model calls:

```powershell
& ../mathmath/.venv/Scripts/python.exe -B tools/prepare_geo3k_reconstruct.py --resume --limit 1500
```

Quotas count compiled candidates. The call and drawing budgets bound the run; reaching a budget before the quota returns a partial checkpoint and exit code 2.

Repeat the same command with `--resume` after interruption. Completed author responses and drawings are reused. A failed drawing has at most two outer attempts, each using the existing native drawing call bound (default four model calls). Call reservations are saved before execution, so interrupted work cannot evade the declared run budgets. Resume allows newly audited sources and a larger base count in this same folder. It rejects changes/removal of previously selected source snapshots, changes to the drawing harness/model or seed, and a decreased base count. Pending author calls retain their saved source snapshot. Prompt edits apply to future author calls; completed calls retain their original prompt and responses, and prompt hashes are recorded in state.json. A larger quota/budget may be explicitly requested for the same pinned run. Use one process per output directory. A failed author call stops with `author_failed` and preserves the pending context; after restoring the provider, the same resume command retries it. Short Windows locks on JSON checkpoints and JSONL/Parquet snapshots are retried for up to four replace attempts; persistent locks stop safely without overwriting the previous file in place. Completed per-row checkpoints are reused on resume.

The loop bootstraps actual Generate bases, then proposes auxiliary additions against their allowlisted IDs. For each Edit, the model also authors a complete resulting Generate instruction; application code can pair it with the exact same completed target and verified render without drawing again. The two tasks retain the same original parents/source family. Exact repeated inputs are deduplicated; mathematical diversity is specified by the system prompt.

Unattended production may use a successfully compiled candidate base to create candidate Edit descendants. This is an explicit candidate-to-candidate lineage, not independent mathematical approval. Held/rejected diagrams cannot seed new edits. Every returned diagram and each task pairing still require the readiness checks below before training export. The loop's `candidate_quota_met` means completed candidate quotas, never ready quotas; it records independently reviewed counts separately. No target-versus-itself evaluation or model verdict promotes readiness.

Outputs are `generate.jsonl`, `edit.jsonl`, their candidate Parquet snapshots, `review.html` with before/after renders, `failures.jsonl`, and `report.json`. Raw author responses, source contexts, traces and each drawing attempt remain under `rounds/` and `drawings/`. Split assignments remain null until deliberately assigned across source families. The drawing `--export` gate checks review evidence and exact image/code bindings. Rows without an assigned split export to `data.parquet`; known split assignments must remain consistent across related samples.

Optional `supervision.json` records `rows` with an existing `id`, `decision` (`usable_instruction` or `needs_revision`) and concrete `reason`. On snapshot/resume, marked `needs_revision` cases and their exact duplicates stay in the proposal archive but are excluded from caller inputs. An unreviewed instruction remains a candidate; an instruction review never approves a missing target or Edit starting diagram.

For the current Auxiliary Line batch, Edit is a purposeful auxiliary addition to existing geometry. Numeric/relation replacements, removals, labels and colour edits are excluded. Generate may retain original source measurements, but changing measurements alone is not a new case. The system prompt requests distinct mathematical constructions rather than renaming or numeric variants. The runner performs exact deduplication; it does not judge semantic equivalence with wording heuristics.

After recording review, use the same `--output` with `--review-only` to refresh caller inputs without any model call. This uses the saved source snapshot and retains all raw batches.

The low-level instruction CLI remains available for instruction-only work with `--sources`, `--task`, `--calls`, `--rows-per-call`, `--contexts-per-call`, `--bases`, `--existing`, `--prepare-only`, `--resume` and `--review-only`. An Edit returns the supplied base ID in `source`; application code validates its parents and copies the exact `target_tikz` into `current_tikz`. Original base givens, the base code hash and `complete_instruction` remain offline provenance. Free-text matching of `starting_givens` is retired. Targets, renders and rubrics never enter instruction-author context; drawing receives only the explicit instruction and actual current TikZ.

## 1. Source selection

The supplied `Onn_generate/` statements are retained as reference examples, including their tangency/metric problems. Keep duplicate presentations under shared lineage; do not discard a useful reference because it asks for a length or radius. Their geometric constructions and solution auxiliaries also inform the system few-shots. Audit reasons, family labels and auxiliary notes are optional offline metadata.

The grade 10-12 expansion is specifically **spatial/solid geometry**: points, lines and planes in space, polyhedra, sections, projections, cones, cylinders, spheres and tangencies. Exclude planar-only additions and real-world application scenes from this expansion.

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

## 4. Shared evaluation and target review

Use `evaluate(target_tikz, output_tikz)` and the four scores in [docs/evaluation.md](../docs/evaluation.md). Relations come from the observed target; instruction, taxonomy and rubric fields are not scoring inputs.

Review the target against its instruction, source givens and required notation before marking it ready. Compilation and target-versus-itself scores do not establish source fidelity. Record independent evidence for requirements outside the implemented checks.

## 5. JSONL records and output paths

After the instruction stage, write complete target/rubric examples to `dataset/<batch-id>/generate.jsonl` and `dataset/<batch-id>/edit.jsonl`. These are later training/evaluation artifacts, not the instruction-stage deliverable. Use UTF-8 without a BOM, one JSON object per physical line, a final newline, and standard JSON serialization with `ensure_ascii=False` and `allow_nan=False`. Serialize TikZ newlines/backslashes correctly; do not hand-escape or store Markdown fences.

Each row has these fields. Required nullable fields stay present as `null`; omitted optional source metadata must not be guessed.

| Field | Contract |
| --- | --- |
| `schema_version` | Exact string `synthetic-tikz:v2` for new records. Preserve historical records as their original schema. |
| `id` | Unique, persistent string identifying this task instance/revision. Never reuse an ID for changed inputs or target. |
| `task` | `Generate`, `Edit`, or imported `Reconstruct`, matching the containing file. |
| `instruction` | Nonempty mathematical-givens instruction for Generate/Edit. Optional/null for image-only Reconstruct. |
| `current_tikz` | `null` for Generate/Reconstruct; a nonempty complete starting picture for Edit. |
| `target_tikz` | Nonempty complete target under section 3. Incomplete generation attempts are not example rows. |
| `image` | Required for Reconstruct: source-image `{path, sha256}`. Export embeds its verified bytes separately from the target preview `tikz_image`. Absent/null for Generate/Edit. |

Metadata fields are optional:

| Field | Contract |
| --- | --- |
| `grade` | Optional; integer 6-12 when known, otherwise `null`. Do not infer missing metadata merely to populate this field. |
| `diagram_types` | Optional taxonomy labels when known, otherwise `null`. Missing classification does not invalidate an input/target pair. |
| `source_group` | Optional known problem-family ID. Preserve existing lineage; do not invent missing provenance. |
| `split` | `null` until assigned; then `train`, `validation` or `test`. A source group has exactly one assignment across all batches. Do not invent split proportions. |

Keep a source-decision log in `dataset/<batch-id>/selection.jsonl`, with `{source_group, source_path, source_sha256, locator, decision, reason}`. `decision` is `selected`, `skipped` or `needs_review`; an unassigned source group may be `null`. This log is an audit artifact, never a training file. Record a specific reason such as basic recognition, incomplete givens, duplicate source or conflicting evidence.

Training inputs are `instruction` for Generate, `current_tikz` plus `instruction` for Edit, and `image` with an optional instruction for Reconstruct. `target_tikz` is the desired response. Metadata and rubrics are optional offline context, not mandatory model inputs. Preserve known lineage and split assignments without blocking valid pairs on missing metadata.

## Final Parquet export for Hugging Face

Export the completed reviewed dataset to Parquet for Hugging Face after target verification and deduplication. Preserve source-family split assignments when present. Preserve the actual task inputs, target TikZ and provenance; keep rubrics/evaluation metadata outside generation inputs. PyArrow is required for drawing snapshots and export, and is pinned in [requirements.txt](../requirements.txt).

The [drawing runner](../tools/draw_instruction.py) consumes explicit Generate/Edit caller JSONL, without inferring task or starting state from filenames or IDs. Copy the instruction/source verbatim; assign `task` and `source_group` from audited decisions. Every drawing input has `current_tikz`: null for Generate, complete actual starting TikZ for Edit. The production caller resolves the allowlisted base ID before drawing; the drawing harness never receives a base reference instead of code. Imported Reconstruct pairs use the common review/Parquet export path, not this Generate/Edit drawing entry point. Failed attempts remain run artifacts, not completed dataset rows.

Drawing may preserve a structurally valid supplied `target_tikz` without approving it. `--resume` reuses the latest completed target only for matching task, instruction, actual `current_tikz`, source and family. A failed or incomplete drawing is retried even if it returned partial TikZ. `--retry-id` explicitly redraws a selected completed target after a mathematical/visual defect is found. Each command makes at most one bounded drawing attempt per pending row; `--limit` counts pending rows. Completed targets require no model/compiler calls during reuse. This is drawing completion, not mathematical readiness.

Each row's latest outcome is saved through an atomic checkpoint before returning, and `candidates.jsonl` is rebuilt as one latest row per ID. Resuming a subset preserves other saved rows. Retry attempts and each invocation's input/profile snapshots stay in separate directories. Use one process per run directory. A retry starts from the original explicit instruction/current TikZ, keeps prior attempts offline, and never promotes a failed output to Edit input automatically.

Drawing supports 1–32 workers; default 4. Measure matched batches at higher concurrency using elapsed time, successful new drawings per minute and failures. Each result passes through one snapshot writer. The production loop stops at declared candidate quotas/budgets; independent review establishes ready counts separately. Throughput replicas never increase unique counts.

The shared compiler currently admits two operations, returning HTTP 503 when busy. Drawing therefore queues compiler operations locally with `--compiler-concurrency` (1–2, default 2) while model workers remain independent. The gate precedes native HTTPX streaming because the existing compiler SDK overrides its pool timeout to three seconds. No new compiler or model-regeneration loop is introduced. Preserve the native error/checkpoint if other clients saturate the shared service; do not call a transport failure a mathematical failure. Render artifacts use a short UUID directory outside the longer case-checkpoint paths to avoid Windows path-length failures; prior attempt paths remain unchanged.

The runner also atomically replaces `candidates.parquet` after every completed result, including failures. It contains one latest row per ID; retries replace that row and subset resumes retain other saved results. Per-row JSON checkpoints remain the recovery source if snapshot writing is interrupted. The single writer runs outside the drawing workers. A closed Parquet snapshot requires rewriting its accumulated rows; this is appropriate for the planned roughly 1,500 rows per task, while substantially larger runs should use fragments.

`tikz_image` embeds the target PNG as `{bytes, path}` with Hugging Face Image feature metadata, following [HF's PyArrow image format](https://huggingface.co/docs/hub/datasets-pyarrow#embed-images-inside-parquet) and its [feature reader](https://github.com/huggingface/datasets/blob/main/src/datasets/features/features.py). It uses the source/PNG pair returned by the native render, with both hashes retained, or exact-target evidence from the shared compile helper. Parquet metadata also carries `target_tikz_sha256` and `tikz_image_sha256` for the embedded pair, preserving original attempt evidence separately. A changed target, changed PNG, missing file or absent binding yields a null image unless valid exact-target compile evidence is available. Final reviewed exports require a matching, valid PNG and embed its bytes; they do not depend on local image paths. Supplied unrendered targets stay candidates with null images until compiled through the shared helper. Candidate snapshots are not approval or split assignment.

For this runner's final export, actual review is recorded in `verification.status: ready`, `reviewed_by`, and `reviewed_input_sha256`, computed with its `review_digest` after task, instruction, current/target TikZ, target PNG, rubric and source-family provenance are final. The digest includes the verified PNG's actual bytes hash; changing the image also invalidates the recorded review. These fields attest the recorded review; computing a digest does not perform that review. `--export` validates them and the supplied rows' family/split consistency without a model or compiler call. It also rejects an original parent occurring in different splits across tasks, even under different family names. Cross-batch family/duplicate review remains required. Final Parquet uses ordinary input/target columns and lossless JSON strings for heterogeneous offline rubric/metadata; only populated task/split files are written.

The versioned system prompt and complete Generate/Edit few-shot examples teach mathematical scope and instruction style. Authoring uses one API call per context. Code validates nonempty inputs, structured fields, source scope and exact base linkage; it does not enforce instruction quality with wording blocklists. Review checks source fidelity, useful auxiliaries, semantic uniqueness and target alignment.

## Local candidate review

Run `../mathmath/.venv/Scripts/python.exe -B tools/review_synthetic_dataset.py` and open <http://127.0.0.1:8765>. The local page filters Generate/Edit by task or source/instruction text, shows the exact target preview and matching Edit starting preview, and exposes both TikZ inputs. Select unwanted rows and use **Delete selected**.

Deletion removes exactly the selected task IDs from the current JSONL and Parquet snapshots and refreshes the report/static review. It does not backfill the current snapshots or delete related task rows. Full removed records are retained in `dataset/synthetic/excluded.jsonl`; drawing checkpoints and render files remain available for recovery. Keep this archive with the dataset. Production resume respects its IDs and excludes deleted native Generate bases from new Edit authoring. A later production run can fill its quota with different rows.

Stop drawing production before reviewing; use one reviewer process per output directory. The server binds only to loopback and serves known record previews, with no general filesystem endpoint. It uses Python's [standard HTTP server](https://docs.python.org/3/library/http.server.html) for local curation only. Native [checkboxes](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/checkbox) provide row selection. A stale dataset revision is rejected before deletion; restarting replays saved exclusions if an export was interrupted.

Instruction-only continuation is saved separately from completed drawing pairs. The frozen absent-source run lives in `dataset/synthetic/absent-instructions/`: `contexts.json` and `payloads.json` identify its bounded inputs; `instructions.jsonl` retains all authored candidates; `generate-inputs.jsonl` contains caller inputs after supervision. These are candidates until mathematical review; new Edit inputs require actual starting TikZ.

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
5. Source-group lineage and duplicate checks are consistent. Unknown splits remain null; existing assignments stay consistent across related samples.

This readiness means a reviewed training pair. It does not turn unsupported automatic checks into passes or establish calibrated model-evaluation accuracy. Model self-reported success and target-versus-itself agreement do not establish source fidelity. Report automatic preparation, repairs and curation separately.

Use the existing compiler, drawing harness and evaluation entry points with explicit task inputs. The local skill's [compile helper](../.agents/skills/synthetic-tikz/scripts/compile.py) provides compilation and artifact capture for separately authored or repaired JSONL targets. It snapshots the actual harness profile, preserves inputs and source metadata, and emits candidate copies with evidence paths; it does not select sources, generate targets, certify the complete record schema or automatically approve/export training data. Its report hashes task, instruction, current/target TikZ, rubric and profile separately from later review metadata. Recompile after changing any of those bound values; review notes/readiness updates alone do not change that evidence. Instruction generation does not invoke the compiler or drawing harness.

The older `tools/prepare_tikz_candidates.py` and `tools/evaluate_tikz_candidates.py` are bounded historical experiments; their old per-dimension prose rubric or compiler imports do not define this contract.
