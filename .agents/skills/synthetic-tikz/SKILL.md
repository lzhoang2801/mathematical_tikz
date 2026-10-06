---
name: synthetic-tikz
description: Prepare source-grounded Vietnamese geometry data for Generate and Edit tasks in problem_tikz. Use when selecting substantial geometry problems, authoring mathematical-givens instructions and TikZ targets, or augmenting and validating JSONL batches under dataset/.
---

# Synthetic TikZ data

Create Generate and Edit examples from complete geometry problems in grades 6-12, including complete TikZ targets and their rendered verification. Source selection and instruction writing alone do not complete a dataset row. The user wants substantial geometric configurations and concise mathematical givens. A large number of labels, a long statement, or a difficult calculation alone does not make a useful drawing example.

## Read the common contract

Use [dataset/CONVENTIONS.md](../../../dataset/CONVENTIONS.md) as the shared source-selection, instruction, JSONL, augmentation and verification contract. Read it before preparing a batch. Paths in that contract are relative to the repository root unless explicitly absolute.

Read the current `C:/Users/Onn/Documents/Git/mathmath/src/agent/prompts/tikz.py` and the applicable MathPaper `AGENTS.md` instructions. Pin the prompt version and file hash for the batch. Use its target format and existing drawing/compiler harness. Keep MathPaper and all source files read-only.

## Select sources

Use the source pools explicitly requested for the batch, defaulting to:

- `docs/dataset-selection/grade-*.problems.jsonl`, restricted to grades 6–12; verify each selected record against its referenced curriculum source.
- Complete problems in `Onn_generate/*.tex`.
- Problems in `[L9CB]_2025_10_10.pdf` with verified page and exercise locators.

Apply the selection rules in the common contract to every pool. Skip basic recognition, a standard shape with a few measurements, and repeated elementary midpoint/length exercises. A manifest's `prepared` decision establishes neither the requested complexity nor target quality.

Inspect complete statements, including construction facts introduced in subparts. Keep solutions, proof goals and embedded diagrams available as offline evidence; do not turn them into assumed givens. Review supplied TikZ against the statement before reusing it.

Deduplicate source problems before splitting. The current source audit identifies duplicates between `main.tex` and `test.tex`, and between `0410.tex` and the supplied PDF. Their precise locators and other extraction hazards are in the common contract. Cross-source copies and all descendants share one `source_group`.

## Prepare each pair

1. Preserve the source and assign its source group. Select a coherent drawing scope with all defining dependencies.
2. Write `instruction` as Vietnamese mathematical givens: objects, incidence, ratios, inequalities, order and intersection branches. Natural mathematical prose and necessary construction definitions are allowed. Exclude step-by-step drawing recipes about placing points and connecting them; state the required configuration and visible objects instead.
3. For Generate, use `current_tikz: null`. For Edit, supply the actual complete starting TikZ and state a meaningful mathematical change plus the required preservation. Recompute affected dependent constructions in the target.
4. Produce one complete `target_tikz` following the pinned harness prompt, including its `Relation marks` section. Preserve named construction dependencies and mathematical proportions; include the required visible relation marks. Record repairs to supplied code.
5. Add only the pair-specific mathematical requirements to `evaluation_rubric`, using the common predicate convention. Compile, target-relative content and collision checks are shared. Preserve unsupported requirements explicitly and record how they were reviewed.
6. Run the compile command below and inspect the returned render; verify the givens, branches, visible scope, relation marks and labels. A correct geometric relation does not excuse a missing required symbol: verify its presence and attachment in the render. Check Edit preservation against the actual starting diagram. Store the evidence and mark the row ready only under the contract's readiness rule.
7. Serialize complete rows as UTF-8 JSONL under `dataset/<batch-id>/generate.jsonl` and `edit.jsonl`. Keep selection decisions in that batch's `selection.jsonl`; keep execution artifacts under `runs/<batch-id>/`.

Follow the source-selection and instruction examples in the contract as decision examples, not a sentence template to repeat. Vary the mathematical configurations, active construction subsets, valid parameters and edit operations. Record each change and its seed/parameters; do not count label shuffling as mathematical diversity.

## Compile, inspect and finish

The agent authors the source-grounded instruction and target. [scripts/compile.py](scripts/compile.py) handles TikZ validation, the shared wrapper, the compiler request, PDF/PNG/log persistence, hashes and prompt snapshots. It uses the sibling MathPaper environment and running compiler service; it does not call a model or need API keys. No local TeX installation is needed. Run from the repository root:

```powershell
..\mathmath\.venv\Scripts\python.exe -B .agents\skills\synthetic-tikz\scripts\compile.py dataset\<batch-id>\generate.jsonl --output runs\<batch-id>\compile-01
```

Use `edit.jsonl` for Edit; both `current_tikz` and `target_tikz` are compiled. Add `--id <record-id>` to check a single row, or repeat `--id` for a subset. The compiler URL comes from `--compiler-url`, then the process's `COMPILER_URL`, then `http://127.0.0.1:18080`. Every invocation requires a fresh output directory, preserving earlier attempts. Inputs remain unchanged.

1. Write candidate JSONL following the common contract. During drafting the helper only requires `id`, `task`, `instruction`, `current_tikz` and `target_tikz`; retain the source/lineage fields as soon as selected. It preserves additional fields but does not certify the full dataset schema. The helper fills `provenance.harness_profile` from the actual prompt/wrapper and saves their snapshots. If an existing profile differs, review the target against the changed prompt before starting a new profile revision.
2. Run the command. Read `report.json` for each row's `report_path`; that report contains `target` and, for Edit, `current`. Their `artifacts` map gives exact PDF, PNG and log paths, completeness and SHA-256. The source, request options, stage outcomes, toolchain identity and input hashes are retained. Identical TikZ within one invocation reuses the same compiler result.
3. Open each successful `page-1.png` using the image-viewing tool. Review the actual source, instruction, geometry, full relation-mark convention, labels and Edit preservation. Do not infer visual correctness from compiler success. If correction is needed, revise the TikZ, give the revised pair a new ID with its parent/source lineage, and compile into a fresh attempt directory. Use the batch's bounded repair budget; default to at most two source repairs before retaining the unresolved candidate.
4. The helper writes `candidates.jsonl` with the actual profile and verification report paths, always with `verification.status: candidate` and `reviewed_by: null`. After completing the common readiness checks, record the actual reviewer and concrete findings in `verification.notes`, and set `ready` only for accepted rows. Save those complete records to the task's JSONL under `dataset/<batch-id>/`; preserve unresolved records as candidates and export only ready records with assigned splits. The compile report binds task, instruction, current/target TikZ, rubric and profile; metadata-only review updates do not require another compile.

Exit `0` means every selected picture compiled and rendered, with status `needs_review`; it does not mean target approval. Exit `1` means at least one picture needs attention; other rows and available artifacts are retained. Exit `2` means invalid input/configuration or an existing output directory.

| Report status | Next action |
| --- | --- |
| `validation_failed` | Correct the rejected TikZ envelope/subset; no compiler request was sent. |
| `compile_failed` | Read the saved compiler diagnostic and `result.log`; correct the source when the error belongs to it. |
| `render_failed` | Inspect the raster outcome; retain the successful PDF. Use the shared compiler's `render_pdf` with that PDF for raster-only recovery, following its linked contract below. Do not regenerate geometry to fix raster infrastructure. |
| `unavailable` | Transport, response validation, compiler timeout or unknown outcome; preserve the attempt and retry the same source once after the service is available. Do not classify this as incorrect geometry. |

Compiler lifecycle and raster recovery follow the existing [compiler contract](../../../../mathmath/docs/latex-compilation-design.md). Keep infrastructure recovery bounded; do not install another compiler, replace the wrapper or repeatedly submit unchanged failures. Model-based authoring, when used, still goes through the existing drawing harness and its tracing/call limits.

## Execution and completion

For real model batches, establish a bounded source/call scope and use the already authorized provider and configured LangSmith tracing. Reuse existing credentials and harness limits; never print secrets or create a second drawing loop. Keep the target and rubric outside the drawing worker's inputs.

Do not turn this skill into permission to send source material to additional providers or message other chats. Existing user authorization remains applicable within its stated scope.

Before export, check the common JSONL fields, evidence hashes, source-group splits, duplicate inputs, and target completeness. Do not claim that a schema check or compilation proves mathematical correctness. Report actual selected/skipped source counts, candidate/ready counts by task, unique source groups, and preparation routes. State unresolved requirements without counting them as successes.
