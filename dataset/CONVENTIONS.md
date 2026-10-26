# Synthetic geometry data

[Geometry scope](../docs/geometry-k12-vn.md) defines the source content. The [task contract](<../docs/K-12 Mathematical Diagrams with TikZ.md#task-inputs>) defines Generate, Edit and Reconstruct inputs. All synthetic outputs live under `dataset/synthetic/`.

## Source preparation

The authoring source ledger is [audit_givens/selection.jsonl](audit_givens/selection.jsonl). Each selected entry identifies an original problem and stores its checked text, file/line/page locator and any links to duplicate presentations. Curriculum sources are complete examples, practice problems and exercises in grades 6–12. Supplied Onn TeX/PDF problems also serve as authoring references. Corpus folders determine the permitted source scope.

For grades 10–12, select spatial and solid geometry: points, lines and planes in space, polyhedra, sections, projections, cones, cylinders, spheres and tangencies. Use mathematical configurations rather than real-world application scenes.

Read source text against its actual file. Preserve verbatim text in the audit ledger; keep checked OCR corrections there. A file hash detects stale audits. Resolve ambiguous mathematical symbols or intersection branches before using that source. These checks happen once at source preparation, rather than becoming additional annotations for every synthetic sample.

A candidate keeps a `source` reference to its original problem. Resolve its text and locator through the ledger. Duplicate presentations of one problem share a split; composed cases retain all original references in the preparation record.

## Instruction authoring

[generate_instruction.py](../tools/generate_instruction.py) uses the versioned [system instruction and few-shots](../tools/instruction_prompt.md). Each call receives multiple contexts and returns multiple instructions in an `InstructionBatch`.

| Task | Context sent to the author |
| --- | --- |
| Generate | `source` and `source_text` when available (otherwise checked `givens`), plus checked `givens` and `auxiliaries` when available |
| Edit | The checked base ID as `source`, its `givens`, and exact `current_tikz` |

The system instruction owns mathematical behavior and the requested task/count. Generate contexts retain the full source statement alongside any checked givens and auxiliaries; when full source text is unavailable, checked givens provide the source text. Application code supplies source/base IDs and resolves Edit inputs; the model does not invent links. Audit decisions, file hashes, split bookkeeping, traces and future targets remain outside the author context.

Instruction supervision records a decision and reason for each reviewed candidate. `usable_instruction` candidates may proceed to caller inputs; `needs_revision` records a concrete correctable defect, while `needs_review` records a necessary fact that cannot be established. Both are reviewed holds outside the caller queue. IDs without a decision remain pending, and a negative decision for any exact-input duplicate holds that case from the queue.

An Edit response includes its new mathematical instruction and `complete_instruction` describing the resulting configuration. Application code can reuse its completed target for a Generate pair. That complete description and the base link are authoring-process data, not extra training inputs.

Write concise Vietnamese mathematical statements with standard notation:

- Define named objects, dependencies, carriers and intersection branches. Preserve order, inequalities, nondegeneracy and necessary measurements.
- Separate original givens, new construction definitions and conclusions to be proved.
- State purposeful auxiliary geometry through mathematical definitions. Altitudes, medians, parallels, projections, sections and tangent radii should expose a useful relationship.
- Keep proof questions, calculation requests, drawing recipes, source IDs and generic drawing boilerplate out of the instruction.
- Preserve geometric freedom. Coordinates chosen to realize a diagram do not become source givens.
- Edit states the change against the actual starting picture. Preservation of unaffected objects and relationships is shared task behavior.

Use the system instruction's multi-output examples for style. Instruction variety comes from different configurations and constructions. Point renaming, paraphrases and uniform rescaling do not establish new mathematical cases. Code checks structured fields and exact source/base linkage; mathematical review is a separate preparation step.

## Bounded production and recovery

[run_synthetic_dataset.py](../tools/run_synthetic_dataset.py) selects contexts, calls the author, draws through the existing harness and checkpoints each stage.

```powershell
python -B tools/run_synthetic_dataset.py --resume --generate 1500 --edit 1500 --base-count 600 --batch-size 30 --contexts-per-call 10 --max-author-calls 200 --max-draw-attempts 3000 --workers 8 --cover-all-sources
```

`--generate` and `--edit` are total destination quotas. Author and drawing budgets are cumulative. `--batch-size` is the instruction count per call; `--contexts-per-call` is the number of source problems or checked bases. Seeded sampling rotates the full selected pool and avoids repeating duplicate presentations within a call.

`--cover-all-sources` prioritizes original sources with the fewest completed bases and Edits. Author attempts do not count as target coverage. Completion requires the quotas and coverage of every selected source. `report.json.source_coverage` lists missing references when a failure or budget stops the run.

Resume reuses checked source snapshots, completed author responses and drawings. Keep `state.json`, source snapshots and per-case checkpoints together. Failed drawings have bounded attempts through the existing harness. Call reservations are saved before execution. Resume retains the pinned seed/model/harness and existing split assignments; new source text requires a new checked snapshot.

The low-level author CLI also supports instruction-only work with `--sources`, `--task`, `--calls`, `--rows-per-call`, `--contexts-per-call`, `--bases`, `--existing`, `--prepare-only`, `--resume` and `--review-only`.

## Drawing and compilation

[draw_instruction.py](../tools/draw_instruction.py) receives only the explicit instruction and actual starting TikZ. It reuses MathPaper's `problem_tikz`, drawing agent, wrapper and compiler.

Pin the actual [TikZ harness prompt](../../mathmath/src/agent/prompts/tikz.py), [task prompt](../../mathmath/src/agent/prompts/problem_tikz.py) and [validator/wrapper](../../mathmath/src/agent/latex/tikz.py) for a run. The target is one ordinary `tikzpicture` without Markdown, preamble, document wrapper or comments. Follow the shared prompt's organization, dependency constructions, scaling, label placement and supported commands.

Given metric relations must hold geometrically. Apply the shared relation-mark rules for requested equal-segment/equal-angle classes, perpendicularity and numerical angle text. Check the actual render for the intended carriers, vertices, sectors and readability. Coordinates and compilation alone do not establish that the required visible content is present.

Drawing supports bounded model concurrency with a separate compiler gate. The shared compiler admits two operations; `--compiler-concurrency` is 1–2. Each outcome is checkpointed immediately. Aggregate snapshots are coalesced while drawing continues and replaced atomically with retries for short Windows reader locks. Use one process per output directory.

`--resume` reuses completed targets for matching task inputs and source. Failed or incomplete outputs remain pending. `--retry-id` explicitly redraws a completed case. The runner does not infer an Edit base from a filename or promote failed code to a starting picture.

## Dataset records

A completed candidate contains its `id`, task-specific input, `target_tikz` and `source`. The task and split can be represented by the containing file. Shared storage uses `current_tikz: null` for Generate and Reconstruct, and `instruction: null` for Reconstruct.

| Task | Sample input |
| --- | --- |
| Generate | `instruction` |
| Edit | `instruction`, `current_tikz` |
| Reconstruct | Exactly one diagram `image` |

Write UTF-8 JSONL with one object per physical line, a final newline and ordinary JSON serialization. Preserve exact code and image bytes.

Process records have their own purposes: author checkpoints retain responses and base links; drawing checkpoints retain attempts, traces and exact render bindings; review records retain decisions tied to the checked inputs and target. Their internal fields are not additional dataset annotations. Source locators belong to the source ledger; split assignments belong to the frozen split file.

## Review and Reconstruct preparation

Review the input/target pair for source fidelity, mathematical relations, visible content and readability. Edit review also checks the actual change and preservation of unaffected geometry. Keep decisions bound to exact inputs, target code and render bytes. Compilation and a model's own success status do not certify the pair.

[review_synthetic_dataset.py](../tools/review_synthetic_dataset.py) opens a local review page at <http://127.0.0.1:8765>. Stop production before reviewing. Deleting selected rows records them in `excluded.jsonl`; resume respects that archive. Moving a usable diagram to Reconstruct preserves its verified image/target pair and clears `instruction` and `current_tikz`. Original task records remain in the recovery archive. Reconstruct user content contains only the image; its behavior is supplied by the system instruction.

Moved pairs live in `reconstruct/candidates.*` with images in `reconstruct/images/`. Deduplication retains original source and row links in preparation history. Raw Geo3K import is explicit through `--geo3k`; it uses `rendered_image` and `code`, with an image-hash ID and upstream split assignments.

## Splits and Parquet export

Group every descendant of an original problem before assigning splits. Join duplicate source presentations, linked Generate/Edit rows, and matching image/code pairs. Composed cases join all parents; a generic shared premise alone does not make two problems duplicates.

[export_hf_dataset.py](../tools/export_hf_dataset.py) freezes these links in `hf/split_assignments.json`. Re-export preserves saved assignments and Geo3K's upstream splits. Keep held-out sources out of authoring demonstrations and training-generation context. Use validation for iteration and test for the final checkpoint.

The final Hugging Face configurations contain only:

| Configuration | Columns |
| --- | --- |
| Reconstruct | `id`, `image`, `target_tikz` |
| Generate/Edit | `id`, `instruction`, `current_tikz`, `target_tikz` |

Source references are consumed during split preparation; they are not model input. Review and split evidence remain in preparation records. PyArrow is pinned in [requirements.txt](../requirements.txt); exports embed image bytes and check exact Parquet round trips.

## Evaluation and training

Offline evaluation accepts `target_tikz` and `output_tikz` and reports compilation, mathematical correctness, content coverage and visual readability. Follow [evaluation.md](../docs/evaluation.md). Source/input alignment is established during target preparation.

Prepare training inputs locally and run fine-tuning on the user's Colab/Kaggle runtime. The [training README](../train/README.md) documents the notebook entry points and their input bundles. Keep production completion, deterministic repairs, model-assisted repairs and human curation distinct in reports.
