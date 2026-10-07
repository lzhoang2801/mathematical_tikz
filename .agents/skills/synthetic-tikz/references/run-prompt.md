# Strategy: prepare synthetic Generate/Edit instructions

Execute this strategy through `tools/generate_instruction.py` and the configured CPA model. The runner loads `SKILL.md` and this strategy into the model context, supplies the audited mathematical sources, and receives typed instruction proposals. Mathematical judgment concerns the actual cases; do not produce another plan or browse files through an agent loop.

## Scope and delivery goal

- Read MathPaper only as a reference. For an instruction-only request stop before drawing. For the user's dataset-orchestration request, continue through drawing/review/export using the existing runners; do not stop at instruction counts.
- Use `dataset/synthetic-givens-20261007`, adding a revision suffix if it already exists. Sampling seed: `20261007`.
- Prepare approximately 1,875 distinct mathematical instruction candidates for Generate and 1,875 for Edit, toward the later goal of about 1,500 accepted targets per task. The 80% retention allowance is a planning assumption.
- Use roughly 150–200 substantial source configurations if the pool supports them. Give richer configurations more meaningful descendants; there is no per-source ceiling. Report a shortfall rather than padding counts.

## 1. Read and select from the audited pool

The runner loads all eight inventories verbatim; it does not regex-extract their incompatible layouts:

- `dataset/l9cb-2025-10-10-generate-edit/givens-grade6-sgk1.md`
- `dataset/l9cb-2025-10-10-generate-edit/givens-grade6-sgk2.md`
- `dataset/l9cb-2025-10-10-generate-edit/givens-grade7-sgk1.md`
- `dataset/l9cb-2025-10-10-generate-edit/givens-grade7-sgk2.md`
- `dataset/l9cb-2025-10-10-generate-edit/givens-grade8-sgk1.md`
- `dataset/l9cb-2025-10-10-generate-edit/givens-grade8-sgk2.md`
- `dataset/l9cb-2025-10-10-generate-edit/givens-grade9-sgk1.md`
- `dataset/l9cb-2025-10-10-generate-edit/givens-grade9-sgk2.md`

Original statements come from `grades-6-7.problems.jsonl`, `grade-8.problems.jsonl` and `grade-9.problems.jsonl`, restricted to the exact IDs in `source-batches.jsonl`, excluding its review-held IDs. The runner checks their current corpus slices. Onn complete problem/subpart ranges come from its existing selection locators and verified `.tex` hashes; skipped duplicates retain their existing family aliases. Style files and orphaned fragments are not source units. Each CPA call receives one bounded source cohort and its relevant full audit inventory.

Reuse the audits. Separate source premises, resolved figure facts, later-subpart definitions, solution auxiliaries and proof goals. Consult original text/figures only to resolve necessary missing or conflicting facts; generated drafts and source TikZ are not authorities. The model must report unresolved figure facts or elementary sources and skip them; batch membership alone is not suitability. Exclude unresolved configurations and basic recognition/length-reading exercises. Keep interacting constructions, not bare shapes rescued with arbitrary extra points.

Keep source hashes, original locators, coverage and selection decisions in the existing source notes/provenance. Merge duplicate original problems before making descendants.

## 2. Form the mathematical cases

For each selected source, identify its base configuration, dependent definitions and admissible branches. Group compatible configurations using the families in the skill. These mathematical families guide augmentation; they do not merge unrelated sources into one split group.

Generate cases by applying the following operations where their prerequisites hold. Write actual cases as they are validated, rather than producing another list of possible ideas.

| Generate operation | Case to author |
| --- | --- |
| Source scope | Use the complete original givens and selected construction definitions; remove proof/calculation questions and their conclusions. |
| Subset | Keep a substantial subset of constructions together with every defining dependency. Remove unused dependents with their parents. |
| Combination | Combine compatible constructions from audited sources, consistently mapping shared objects and checking the joint constraints. Retain every parent. |
| Auxiliary addition | Add a defined construction that serves an active relationship: altitude/projection, median/midsegment, parallel, bisector, reflection, contact radius, diameter, chord midpoint or circumcircle, as applicable. |

An auxiliary must have a purpose in the actual configuration, defined parents and a valid branch. Prefer explicit later-subpart constructions, then verified solution auxiliaries, then deliberate synthetic additions. Do not attach the same auxiliary everywhere. A consequence used in a proof is not an original premise; do not insert proof conclusions to simplify generation.

For Edit, choose a concrete starting mathematical configuration and the requested resulting configuration. Keep both clear in the authoring notes. Select an applicable operation:

| Edit operation | Change to author |
| --- | --- |
| Addition | State the new construction's mathematical definitions directly. |

An Edit adds a purposeful auxiliary to its actual starting diagram. Write definitions directly, such as `E, F là hình chiếu của H lên AB, AC.`, without “Bổ sung/Thêm” prefixes or “Giữ nguyên ...” lists. Preserve existing givens/frame. Do not replace lengths, radii, angles, ratios or defining relations, remove constructions, recolour or rename objects to create Edit rows. New cases in either task must differ in mathematical auxiliary scope/construction, not only measurements or wording.

A planned starting configuration is enough for drafting its instruction; only complete actual starting TikZ can make it a caller input. Do not infer a starting diagram from the row ID, invent a reference field, or repeat a premise that the Edit replaces. No-op, colour and label-only edits do not count.

## 3. Validate each case before wording it

Check complete definitions, joint consistency, positive parameters, triangle inequalities/angle sums where applicable, nondegeneracy, intersection existence and the intended segment/ray/line or inside/outside branch. For Edit, check both the starting and resulting configurations and every affected dependency.

Intersection instructions must explicitly name their line/ray/segment carriers. Segment intersections require membership on both segments; if the intersection falls beyond an endpoint, define the supporting lines or intended rays instead. Do not hide an extension in bare endpoint notation. Check geometric roles in offline augmentation notes too; a new altitude foot does not replace an already defined orthocenter.

A coordinate witness can check one instance or expose a contradiction; it does not prove a general relation. Preserve genuine geometric freedom and ratios. Do not add coordinates, special angles or numerical constraints just because they make TikZ easier. Reject an invalid combination or change rather than silently repairing it into a different problem.

## 4. Sample cases, then write concise instructions

Use the recorded seed for actual case selection and list shuffles. Interleave source families and eligible operations instead of exhausting one source or cycling fixed templates. Sample meaningful subsets, combinations, auxiliaries and admissible parameter/branch changes; give richer sources more cases without a forced allocation per source or operation.

After choosing a mathematical case, write one concise Vietnamese instruction:

- State the necessary objects and defining relations. Define purposeful auxiliaries mathematically.
- Use an actual construction role to specify an auxiliary carrier: a median defines its midpoint endpoint and segment; a radius names its center and circle point; an altitude defines its foot and support. Verify the role in the source configuration. A bare list of segment names is not a definition, and a proof conclusion is not a construction role.
- Exclude proof questions, textbook scaffolding, drawing recipes, point-placement directions, TikZ implementation details and repeated quality boilerplate.
- Do not append “Các đoạn ... thuộc hình”, “Hình gồm ...” or another stock visibility sentence. Do not give an arbitrary connection an unsupported mathematical role.
- Vary short clause grouping, direct versus defining statements and equivalent symbolic definitions. Reorder only independent clauses after their prerequisites. Preserve correspondence lists, angle vertices/direction, ratio operand order, units, inequalities and branches.
- Keep ordinary mathematical terminology. Do not add redundant equalities, unusual synonyms or extra prose to manufacture variety.

These are three equivalent presentations of one case, not three dataset rows or templates to cycle:

- `ABC vuông tại A; H là hình chiếu của A lên BC. I là trung điểm AH, K là trung điểm HB.`
- `Trong tam giác ABC vuông tại A, AH là đường cao xuống BC. K, I lần lượt là trung điểm HB, AH.`
- `Tam giác ABC có ∠BAC=90°; H là chân đường cao từ A xuống BC. I thuộc đoạn AH và AI=IH; K thuộc đoạn HB và HK=KB.`

Record actual sampled operations/parameters and parent sources in offline provenance, outside instructions. Wording, point renaming, equivalent definitions and uniform rescaling alone do not supply new mathematical cases.

## 5. Receive and supervise JSONL proposals

Use fixed, explicit CPA call budgets and bounded parallelism. The runner captures raw replies and parsing errors before producing cumulative `instructions.jsonl`. Supervision must:

1. Review each instruction against its validated givens, definitions and intended change/scope.
2. Screen exact duplicates after Unicode/whitespace normalization: instruction for Generate; instruction plus actual/intended starting configuration for Edit.
3. Review semantic duplicates modulo equivalent wording/definitions, consistent point renaming and unit conversion. Generate identity includes complete givens and scope; Edit identity also includes its starting configuration and mathematical change. Repeated short Edit text on genuinely different bases is not automatically duplicate data.
4. Inspect repeated openings, clause sequences and operation concentration across the cumulative batch. Revisit overused choices without forcing unusual phrasing.

The model returns task, instruction, known parent IDs, the actual augmentation, classification and complete `starting_givens` for Edit. Application code validates the response, assigns persistent IDs and exact source references, and records family/provenance metadata. `starting_givens` is offline authoring context, never a second drawing input. Schema-valid results remain candidates pending mathematical review; source checks and model self-description are not approval.

All descendants of an original problem share its `source_group` across both tasks and batches. Combined parents and discovered duplicate sources must resolve to one group before split assignment; do not combine parents already assigned to different splits. Preserve meaningful parameter/branch/scope differences, but never count cosmetic changes toward the quota.

Continue accumulating validated, deduplicated instructions toward 1,875 per task while meaningful cases remain. Report genuine exhaustion or unresolved sources instead of filling counts with weak variants.

## 6. Prepare available caller inputs and finish

The runner writes `generate-inputs.jsonl` directly with `current_tikz:null` and supported source metadata. Review the proposed mathematics before using it for drawing.

The runner writes `edit-inputs.jsonl` only when a caller-supplied checked Generate in `--bases` has the exact applicable starting instruction. It copies that row's actual `target_tikz` into `current_tikz`. Remaining Edit drafts stay in `instructions.jsonl` with their complete offline starting givens and are reported as awaiting diagrams. Do not fabricate code, use a placeholder/null as Edit caller input, or infer a diagram from a row ID.

Report actual source coverage, families used, deduplicated Generate/Edit counts, available caller-input counts, mathematical variation, presentation repetition findings, skipped/unresolved sources and paths. Compare counts with the instruction-stage goal; do not describe them as accepted targets.

Use `--prepare-only` to inspect exact context plans without a call. `--resume` skips completed contexts and attempts failed ones once per invocation, retaining raw attempts and other completed batches. Seeds control source scheduling and requested variation; they do not make model prose deterministic.

Use small cumulative CPA batches with `--existing` working instructions and updated seeds instead of planning all calls before any feedback. Resumed outputs enter the history too. Inspect rejection/variant counts and semantic repetitions after each batch. If a source has exhausted useful auxiliaries, move to another eligible source; do not refill its quota with length changes or paraphrases.

Stop here only for an instruction-only request.

## 7. Orchestrate the requested dataset

The current deliverable is approximately **1,500 independently reviewed Generate pairs and 1,500 independently reviewed Edit pairs**, then final HF-ready Parquet with target images. Instruction and drawing counts are separate progress measures; rejected, duplicate, incomplete and unreviewed rows do not satisfy the final quota. The 1,875-instruction allowance is planning, not permission to pad data.

Use the existing task as the orchestrator. The user forbids subagents for this work. Own its dataset directory; one process writes each drawing run directory. Use the existing runners, not a new agent/service/orchestration framework:

1. Audit existing JSONL against source facts and the auxiliary rules. Supply these cases through `--existing`. Preserve raw attempts and all original parents/locators.
2. Call `generate_instruction.py --task Generate` in declared batches, review the new mathematical cases, record holds in `supervision.json`, then apply `--review-only`.
3. Draw eligible Generate callers with `draw_instruction.py`, the measured worker count, explicit `--limit`/`--max-model-calls`, and `--resume`. Check actual target geometry, scope, all required Relation marks and render collisions; retain compiler-backed previews.
4. Supply checked Generate rows through `--bases` and call `generate_instruction.py --task Edit`. This selects contexts from actual base parents and resolves exact starting givens to their real code. No Edit caller may contain placeholder/null starting code. Add auxiliary carriers/points only.
5. Draw those Edit callers, check the exact starting/ending pair and preserved geometry, and prepare the existing minimal mathematical rubric after the target. Apply supported executable checks; independently review unsupported requirements. Record real target review using the existing `verification`/`review_digest` contract.
6. Count unique reviewed mathematical cases per task across the cumulative data. Vary families and meaningful auxiliary combinations rather than producing many versions of one sentence. If quotas remain, continue the next declared batch; record source exhaustion/provider or review problems without calling them success. Resume incomplete drawings; do not reissue completed calls or redraw reviewed targets unnecessarily.
7. Merge all descendant/combined-parent families before assigning train/validation/test splits; no original parent appears across splits or across task-specific splits. Freeze reviewed instructions, exact starting/target code, rubrics and review digests, then use the drawing runner's final export.

Measure drawing concurrency on identical source-grounded inputs at 4, 8 and 12 workers first. The CLI supports up to 32, but use observed successful drawings per minute and failure rates to select the production setting. Keep all test replicas outside unique-count inflation. Every later invocation remains bounded and traced; checkpoint progress before proceeding.
