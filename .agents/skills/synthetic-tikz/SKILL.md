---
name: synthetic-tikz
description: Read audited geometry givens, form compatible configurations and purposeful auxiliaries, and prepare varied Generate/Edit instructions and reviewed TikZ data through the existing drawing harness.
---

# Synthetic TikZ data

Use this skill as an optional human/assistant authoring guide for source problems → mathematical-givens instructions → Generate/Edit targets. Work in this repository; MathPaper is read-only. [Dataset conventions](../../../dataset/CONVENTIONS.md) own the current production contract. [run_synthetic_dataset.py](../../../tools/run_synthetic_dataset.py) now owns bounded scheduling, drawing, reuse and resume; [instruction_prompt.md](../../../tools/instruction_prompt.md) supplies the concise versioned model policy. Neither this skill nor its operating guide enters model context. Instruction-only requests use [generate_instruction.py](../../../tools/generate_instruction.py) and stop before drawing.

## Read the whole supplied pool

The CPA runner loads the explicit selected-source ledger under `dataset/audit_givens/selection.jsonl` and verifies selected rows against current manifest text, locators and corpus hashes. Each call receives a flat batch containing only a source ID and either source_text or givens. Audit notes, taxonomy and operational metadata stay outside model context. Work only from that context; no autonomous filesystem browsing or new corpus parser is needed. Keep skipped/review-held sources outside calls. Preserve original locators and hashes in provenance and request snapshots.

Reuse the inventories; do not extract the corpus again. Interpret their content as:

| Content | Use |
| --- | --- |
| G / givens | Source premises and explicitly defined objects. |
| F / figure-dependent facts | Use resolved facts only. Consult the cited original when necessary facts remain missing or conflicting. |
| Aux | Candidate constructions: distinguish later-subpart definitions from solution-added or newly proposed auxiliaries. |
| Goal / conclusion | Omit proof/calculation requests and their answers from construction premises. |

Do not trust `prepared` alone, infer missing incidence from names, or treat supplied TikZ as checked. Exclude unresolved configurations. Select interacting constructions rather than bare recognition or elementary length reading; skip weak pools without quotas. A midpoint or right triangle can be useful inside a richer configuration.

## Form meaningful givens groups

Identify the base configuration, actual premises, each dependent object's definition, and the mathematical objects/relations in the visible scope. Use a short mathematical description while reasoning; do not build a generation DSL or send this analysis to the drawing model.

Group by compatible geometry and dependencies, not textbook order, labels or chapter names. Seek these families in the actual pool; this is neither a closed taxonomy nor a mandatory allocation:

| Family | Linked constructions | Preserve |
| --- | --- | --- |
| Triangle, altitude and reflection | Feet, altitude midpoints, reflection about a foot, intersection with a parallel. | Triangle type, inequalities, projection carrier, interior/exterior feet, nonzero segments. |
| Medians and parallel transversals | Selected medians, centroid, midsegments, side ratios, corresponding triangles. | Midpoint carriers, ratios/order, vertex correspondence, intersection existence. |
| Bisectors and equidistance | Internal/external bisector, side intersection, feet to angle arms, incenter/contact radii. | Sector, ray versus line, bisector branch, nondegenerate angle. |
| Quadrilateral and diagonals | Parallelogram/trapezoid, diagonal intersection, diagonal projections, side-cutting transversal. | Vertex order, parallel pair, required convexity, segment versus extension. |
| Circle, secant and tangent | Diameter, chord midpoint, contact radius, second intersection, circumcircle. | Center/radius, inside/on/outside condition, selected intersection, distinctness, ray order. |
| Two circles | Common chord/centers, opposite diameter endpoints, secant through an intersection, contacts. | Intersecting/tangent branch, each intersection's parents, center-distance restrictions. |
| Spatial configuration | Pyramid/prism with a defined altitude, section or face auxiliary. | Actual 3D incidence/metric relations before projection; visible/hidden roles. |

A family supports several scopes; it does not authorize arbitrary merging. Map common objects consistently, keep every parent source, and check joint satisfiability. The same triangle cannot be acute and obtuse; independently fixed side/angle sets cannot simply be pasted together. Restricting a general triangle to a right triangle is a recorded synthetic change. Equality/similarity must preserve vertex correspondence. A combined configuration is not an original source fact.

Before accepting a group, check complete definitions, triangle inequalities/angle sums, positive and consistent parameters, nondegeneracy, intersection existence and branch, and segment/ray order. Recheck the whole configuration after a change. Numerical coordinates can witness one instance or expose a contradiction; they do not prove a general theorem and are not instruction text. Leave genuine geometric freedom free.

## Choose purposeful auxiliaries

Each auxiliary needs a mathematical purpose in this configuration. Prefer an explicit later-subpart construction, then a verified solution/hint construction, then a deliberate synthetic construction related to active givens. Record which kind it is. A solution auxiliary is added scope, not an original premise or permission to assume the proof conclusion.

For each proposal establish:

1. What relationship it exposes or compares: height, distance to a carrier, symmetry, equal radii, midpoint ratio, corresponding triangles, circle contact or intersection.
2. Its defined parents/carriers, existence and intended branch.
3. Its visible role: segment, ray, supporting line, circle/arc, point or contact radius.
4. Distinctness, absence of unintended degeneracy, and an actual contribution beyond a redundant no-op.

Useful choices include a perpendicular foot to a named support, parallel through a specified point to a side, median to a named midpoint, reflection about a point/line, diameter through a circle point, center-to-contact radius, chord midpoint/perpendicular, circumcircle of a noncollinear triple, or segment between defined points serving the selected comparison. Define every new endpoint and justify each auxiliary from the active configuration.

Preserve these branches:

- A projection onto line `BC` can lie outside segment `BC`. Do not impose interior membership without source evidence or a deliberate realizable synthetic restriction.
- Name intersection carriers explicitly as lines, rays or segments. Before using two segments, establish that the intersection lies on both. When it lies on an extension, state the supporting lines or intended rays; an unnamed extension is not an acceptable branch. An altitude foot is not an orthocenter: check its defining role rather than assigning a convenient name.
- A line through a circle point has a distinct second intersection only away from tangency. Name it as distinct from the known intersection. Two tangent contacts from an outside point need a selected branch or explicitly retained symmetric freedom.
- Parallel lines have no finite intersection; a circumcircle needs a noncollinear triple; coincident endpoints cannot provide a right-angle carrier.
- Internal/external bisectors, minor/major arcs, same/opposite half-planes, and segments/rays/lines are different conditions.
- An Edit adds a purposeful auxiliary to the actual starting diagram. Preserve its existing geometry and frame. Do not turn side lengths, radii, angle values, ratios, colour, labels or rescaling into Edit operations.

Do not connect every pair of points, attach arbitrary midpoints to weak sources, or invent special angles/ratios to simplify TikZ.

## Write varied mathematical instructions

Write concise Vietnamese givens with necessary definitions and selected mathematical objects. “H là hình chiếu của A lên đường thẳng BC” is mathematical construction data. Exclude point-placement recipes, coordinates, TikZ syntax, renderer advice and repeated quality boilerplate. Remove textbook scaffolding, proof requests and unverified conclusions. Do not append generic segment inventories such as “Các đoạn ... thuộc hình”, “Hình gồm ...” or “Có các đoạn ...”. Define a purposeful auxiliary mathematically; do not add a stock visibility sentence or rename an arbitrary connection to make it sound meaningful. Apply these checks to assistant revisions as well as model proposals.

For Edit, state only the auxiliary's mathematical definition relative to `current_tikz`, without “Bổ sung/Thêm” prefixes or “Giữ nguyên ...” lists. Its added carriers/points must expose an active geometric relationship. Include existing facts only to disambiguate a construction. Parameter/relation replacement and removal are outside this batch's Edit task.

Define an auxiliary by its actual construction role when that role holds. `HM, HN lần lượt là trung tuyến của các tam giác HAB, HAC` defines the midpoint endpoints and their carriers. `BA′, CA′ là các bán kính tới A′ của hai đường tròn tâm B, C` selects real radius carriers. With AB a diameter centered at O, `MO, NO lần lượt là trung tuyến của các tam giác MAB, NAB` selects those carriers; OM and ON are not radii when M and N are external tangent intersections. These are mathematical definitions, not substitutes for generic segment inventories. Do not invent a role or state the theorem to be proved as a premise. In Edit, check that the requested carriers are actually absent from the starting diagram.

Vary dependency-closed auxiliary subsets and compatible combinations: altitude/projection carriers, medians/midsegments, parallels, bisectors, reflection carriers, radii/contact lines and branch-defined intersections. Every auxiliary must have a purpose, not merely increase point count. Retain original source measurements where relevant. Changing numbers, wording, labels or drawing scale alone supplies no new case in either task. New Generate cases need a different valid mathematical construction/scope; Edit cases need a purposeful auxiliary addition to a genuinely different starting scope.

Shuffle families, subsets, admitted free parameters, Edit operations and natural clause order with a recorded seed. Reordering must preserve unambiguous definitions. Do not impose one sentence template or repeat one auxiliary throughout the batch. No per-source ceiling applies to valid descendants; each executed batch still has a finite row/call budget.

Choose the mathematical case before its presentation. For each accepted case, sample one concise wording: reorder independent fact clauses after their prerequisites, merge/split short clauses, vary direct versus defining statements, or use an equivalent symbolic definition when it is complete and nondegenerate. Keep point-to-carrier correspondence aligned. Preserve angle vertices/direction, ratio operand order, units, inequalities and intersection branches. Do not add redundant facts or unusual synonyms for variety; ordinary mathematical terminology may repeat. The seed records sampling choices, not a guarantee that generated prose is deterministic.

Screen exact input duplicates with Unicode/whitespace normalization: instruction for Generate, instruction plus actual/intended starting configuration for Edit. Then review semantic duplicates modulo wording, equivalent definitions, consistent point renaming and unit conversion. Generate identity concerns the whole givens/scope; Edit identity also concerns the starting configuration and mathematical change, so the same edit text on different actual bases is not automatically duplicate data. Wording, renaming and uniform rescaling alone must not fill the row quota. Report mathematical variation separately from presentation repetition, and inspect repeated openings/clause patterns and operation concentrations across the whole batch. Keep this audit in existing notes/provenance, outside mathematical instructions; no generation DSL.

Examples grounded in the reviewed pool:

- **Generate, source scope:** `Tam giác ABC vuông tại A; H là chân đường cao từ A xuống BC. I, K lần lượt là trung điểm AH, HB.` Grade 8 SGK 1, `L4197`; its proof's perpendicularities remain conclusions.
- **Generate, synthetic combination:** `ABC vuông tại A, H là hình chiếu của A lên BC. I là trung điểm AH, K là trung điểm HB. E, F lần lượt là hình chiếu của H lên AB, AC.` Combines selected constructions from grade 8 `L4197` and `L4874`; verify the selected subsets and retain both parents.
- **Edit, addition:** `E, F là hình chiếu của H lên AB, AC.` Requires an actual base containing that configuration.
- **Edit, parallel auxiliary:** `L là giao điểm của đường thẳng BC với đường thẳng qua I song song AC.` In the right-triangle/altitude-midpoint base above, this gives the corresponding midsegment IL in triangle AHC.
- **Generate, circle family:** `Đường tròn (O) có đường kính AB. C thuộc (O), C khác A, B và AC < BC; H là trung điểm BC. Tiếp tuyến tại B của (O) cắt tia OH tại D.` Base of Onn Bài 6; do not assume its later tangent/concyclicity claims.
- **Edit, circle scope:** `E là giao điểm thứ hai của đường thẳng AD với (O), E khác A; M là trung điểm AE.` Requires that actual circle-family base.

Each Edit takes complete actual starting TikZ in `current_tikz`, from a checked Generate result or checked existing diagram. Add a coherent auxiliary construction with its necessary dependencies. The same auxiliary sentence on bases differing only by lengths or labels is not a new mathematical Edit case.

## Draft, draw, review, export

Call CPA through the instruction runner with a declared call budget, rows per call, seed and at most four workers. It uses one structured model call per context and no automatic refill/reviewer loop. Schema, known-parent, task-scope, boilerplate and exact-duplicate checks are deterministic. Raw replies, parsing errors, usage, model identity and trace IDs stay available for supervision; these checks do not approve mathematical content.

Pass prior working instructions with `--existing`; resumed outputs are also supplied as source-scoped history. Avoid their mathematical cases, not just their exact sentences. The runner additionally screens number/point-name substitutions and reports them separately. This conservative text screen cannot prove semantic uniqueness or mathematical validity: review equivalent definitions/clause reorderings, repetitive auxiliary choices and unsupported branches. Do not repeatedly refill a rejected case with another paraphrase.

The runner writes `instructions.jsonl` with all instruction candidates, `generate-inputs.jsonl` with Generate caller rows, and `edit-inputs.jsonl` only when actual checked starting TikZ is available. Its fields are `id`, `task`, `instruction`, `source`, `source_group`, `current_tikz` and supported classification/provenance. Edit drafts without starting code retain complete `starting_givens` in offline provenance and stay outside Edit caller inputs. IDs, original locators and family joins come from application code, never model invention or filename conventions.

Record instruction review in optional `supervision.json` under the shared conventions. Cases marked `needs_revision` remain in the proposal archive but are excluded from caller inputs, including exact duplicates. Unreviewed proposals remain candidates; reviewing an instruction does not approve its eventual drawing.

Review returned instructions against their source context and preserve them verbatim when drawing. Edit selects an application-issued `starting_record_id` from `available_starts`; application code validates its parents and copies the exact target code into `current_tikz`. IDs are offline linkage, never a replacement for actual TikZ. The unattended loop can derive candidate Edits from native completed/compiled candidate bases, retaining this lineage without claiming independent approval. It stores the complete resulting Generate instruction separately so the exact edited target can be reused. Held/rejected bases are excluded; every final task pairing still requires independent review before ready export.

Use [tools/draw_instruction.py](../../../tools/draw_instruction.py). It reuses the configured model and native MathPaper `problem_tikz`/`build_tikz_agent`, bounds parallel drawing/model calls, and saves candidates, compiler-backed previews, messages and trace IDs. Only `instruction` and actual `current_tikz` enter drawing inputs. The runner draws fully specified records independently; it does not find or generate an Edit's starting picture. Do not submit an Edit until its actual starting TikZ is available. Source audits, targets, rubrics and provenance remain offline; tracing records the execution. Do not build another renderer loop or reviewer model.

Drawing accepts 1–32 workers with one snapshot writer. Compare higher worker settings on identical inputs using successful new drawings per minute and failure rates, then use the measured setting; keep each invocation's row/model-call limits explicit. Throughput replicas share the same input IDs and source lineage and count only once in dataset totals.

Each result updates `candidates.parquet` atomically alongside the recoverable JSON checkpoints. Its `tikz_image` column embeds the PNG tied to that exact target; missing or unverified images are null in candidates. The reviewed export requires matching images and uses the same HF image schema. Retries replace rows by ID; resumed subsets preserve other results.

Run the same input/output with `--resume` after a failure or interruption. Completed targets with matching inputs are skipped; failures and incomplete drawings are retried even when partial TikZ exists. Supplied valid targets are preserved as candidates unless already independently reviewed. Use `--retry-id <ID>` to redraw a completed but defective target. Each invocation attempts pending rows once within its declared budget; no automatic retry loop. Per-row checkpoints recover progress, and separate attempt/session folders preserve traces and source snapshots. Never change the explicit `current_tikz` to a failed output during retry.

Read and pin the current [TikZ prompt](../../../../mathmath/src/agent/prompts/tikz.py) at drawing start. Follow its format and **all applicable Relation marks**: equal-segment classes, equal-angle classes/bisector halves, perpendicular/right-angle corners and requested angle text. Correct geometry with missing required marks is incomplete. Inspect carriers, sectors, class patterns and collisions in the actual render. Do not turn unproved conclusions into mandatory marks.

Inspect each target against the instruction, form its minimal mathematical rubric under the shared conventions, and run supported executable checks. Review Edit's exact starting/ending pair. Reuse the existing evaluator and [compile helper](scripts/compile.py) for authored/repaired targets. Unsupported requirements need concrete independent evidence. Compilation, model completion and target-versus-itself comparison cannot approve source fidelity.

Keep failed/incomplete/unresolved rows outside ready data. Record actual review and bind it to task/instruction/current/target/rubric and source-family provenance using the runner's `review_digest`. Assign family splits consistently across tasks/batches, then use `--export` for final reviewed Parquet. Export makes no model calls and preserves the instruction-stage JSONL. Report software checks separately from diagram quality.
