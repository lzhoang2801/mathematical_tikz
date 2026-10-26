# Dataset work in this repository

Use English for agent responses and repository documentation. Preserve source-language mathematical statements verbatim.

## Study artifacts

- Put durable configs/manifests/source pins/inputs/results under `runs/<study>/<version>/`; put disposable downloads/previews/scratch work under `tmp/<purpose>/`. `runs/` and `tmp/` are Git-ignored: preserve them explicitly when transferring the workspace.
- Keep reusable implementation and tests in their existing source directories; keep one-off study scripts and generated artifacts out of the repository root.

## TikZ improvement work

- Use `docs/K-12 Mathematical Diagrams with TikZ.md` as the task contract and `docs/evaluation.md` as the implemented evaluation methodology.
- MathPaper at `C:/Users/Onn/Documents/Git/mathmath/src/agent` is a read-only reference for the current research and evaluation-design work; the user has prohibited modifying it. Read `mathmath/AGENTS.md` when inspecting it and preserve its existing changes. Current entry points are `workflows/problem_tikz.py`, `workflows/geometry_tikz.py`, `workflows/tikz.py`, and `evaluation/problem_tikz.py` (the older `problem/_tikz.py` paths no longer exist).
- Reuse the existing drawing harness, compiler, wrapper, prompts and evaluation boundaries. Keep reference targets outside worker/reviewer inputs.
- Keep native drawing in `src/agent` and its shared compiler client in `src/latex_compiler`; pin copied MathPaper files in `src/upstream.json`. Spec First implementation, tests and experimental tools belong in `src/spec_first`, `tests/spec_first` and `tools/spec_first`. Native imports must not depend on Spec First.
- For Ollama, use `langchain-openai`'s `ChatOpenAI` with its OpenAI-compatible `/v1` endpoint and inject it into the existing harness. Do not add an Ollama adapter, provider framework, or second drawing loop.
- Delegate bounded source audits, curation, execution of existing tests and visual inspection to subagents. The primary agent owns implementation and test edits; do not delegate code changes.
- Do not run formatter checks or automatic formatting. The user handles formatting when committing. Functional tests, linting and `git diff --check` remain appropriate.
- CPA/model calls and LangSmith tracing are authorized within a user-requested bounded production run. Preserve explicit input scope, call/drawing budgets and the pinned run configuration. Do not restart quota-stopped production while doing documentation, review or export work. Draft outputs are not approved targets.

## Scope and sources

- Work only with grades 6–12. Do not inspect, edit, or copy grades 1–5.
- Use the processed local corpus at `C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums` as the source of truth for dataset content. Web research is allowed for papers and official implementation documentation, as requested for the TikZ improvement work; do not use it to replace curriculum sources.
- For grades 6–9, follow the corpus `README.md`/`delivery.json` and each book's `book.final.md`, `layout.final.json`, `toc.final.json`, and `images/` folder. For grades 10–12, use `full.md`, `layout.json`, and the adjacent `images/` folder.
- Treat corpus files as user-maintained inputs. Do not restore deleted crops or change corpus images/layout/ToC/Markdown unless explicitly asked. Reflect deleted images downstream by refreshing manifests; a missing file is removed from the dataset list, not changed to `needs_review`.
- When visual inspection of large images is needed, delegate that inspection to a subagent, per the user's preference.

## Dataset semantics

- For new Generate/Edit synthetic batches, [dataset conventions](dataset/CONVENTIONS.md) own the production contract and [instruction_prompt.md](tools/instruction_prompt.md) owns the versioned authoring system instruction and few-shots. The repository-local [synthetic-tikz skill](.agents/skills/synthetic-tikz/SKILL.md) is an optional authoring reference; do not send the skill or operational documentation to the model.

- Task inputs and system/user message boundaries are defined once in the [canonical task contract](<docs/K-12 Mathematical Diagrams with TikZ.md#task-inputs>). Follow that definition in dataset preparation, message builders and training.
- For Generate/Edit, `problem_tikz` is stateless and instruction-driven: require a self-contained `instruction`, optionally pass `current_tikz`, and do not inject `ProblemCandidate` or prior conversations. Put any necessary source facts into the explicit instruction at the caller/dataset boundary.
- Dataset candidates need only their task inputs, target, ID and a source reference. Resolve that reference through the source ledger to recover the original problem and keep related samples in one split. Source locators and duplicate-source links belong to that ledger; execution and review evidence belong to process checkpoints. Do not require grade, classification or duplicated source metadata on samples. Distinguish selected sources, compiled candidates and reviewed pairs in counts.
- Evaluation for every task compares produced TikZ with `target_tikz` using the shared criteria in the project docs. Generation stays direct TikZ. DiagramIR is authorized as a verification representation after generation: extract observed structure, then apply executable checks. Do not replace those checks with a second LLM's rubric verdict or assume an IR pass establishes instruction/source fidelity. Reuse the same verification criteria across tasks.
- Treat selection of diagram information as a research problem: distinguish candidate facts, geometric construction constraints and information the reader needs to see. See [mathematical content selection](docs/geometry-k12-vn.md#mathematical-content). Drawing conventions are not an exhaustive annotation checklist or a list of shape-specific exceptions; keep author, reviewer and evaluator expectations consistent.

## Instruction, target and evaluation preparation

- Separate automatic preparation success, deterministic repair, model-assisted repair and assistant curation in reports; do not present manually corrected rows as fully automatic successes.
- The agent owns evaluation construction from the supplied problem and sample TikZ. Existing harness rubrics, evaluator verdicts and accepted states are not oracles. Build and calibrate executable checks against valid variants and deliberate failures; model judgments do not turn unverified conditions into passes.
- For user-supplied Generate/Edit examples, prepare a self-contained `instruction` and an aligned `target_tikz`, then review their mathematical requirements. Preserve supplied sources and provenance.
- Define the Generate/Edit drawing scope in the instruction, including necessary mathematical facts and requested auxiliary constructions. Check the sample TikZ against that instruction when establishing the target; identify errors or mismatches rather than assuming the supplied TikZ is already an approved target.
- Each task-specific input + `target_tikz` pair is a dataset candidate. Review and validate candidates before treating them as ready samples. For fine-tuning, the task input conditions the target TikZ response; retain the task-specific inputs defined above for Reconstruct and Edit.
- Offline evaluation accepts only `target_tikz` and `output_tikz` and returns compile, mathematical correctness, content coverage and visual readability scores. Follow `docs/evaluation.md`; legacy rubrics are review/export metadata, not scoring inputs.
- Review and freeze task inputs and targets before model comparisons. Calibrate supported checks against valid variants and deliberate failures.
- Keep target TikZ and review metadata out of generation-worker and runtime-reviewer inputs. Training targets are desired outputs, not additional generation context.
- Keep held-out evaluation/test samples out of fine-tuning data. Group variants of the same source problem or diagram in the same split to prevent leakage.
- New Generate/Edit targets follow the pinned shared TikZ prompt under [dataset conventions](dataset/CONVENTIONS.md). Review source fidelity and requirements outside the supported evaluator independently.

## Production and training entry points

| Work | Owning files |
| --- | --- |
| Source selection and synthetic production | [dataset conventions](dataset/CONVENTIONS.md), [selection.jsonl](dataset/audit_givens/selection.jsonl), [production runner](tools/run_synthetic_dataset.py) |
| Instruction authoring | [system prompt and few-shots](tools/instruction_prompt.md), [instruction CLI](tools/generate_instruction.py) |
| Curation and Hugging Face export | [local reviewer](tools/review_synthetic_dataset.py), [Parquet exporter](tools/export_hf_dataset.py) |
| GPU notebook workflows | [training README](train/README.md); each notebook's current configuration owns its recipe |
| Offline diagram scoring | [evaluation methodology](docs/evaluation.md), [pair CLI](evaluation/run.py), [prediction JSONL batch CLI](evaluation/batch.py) |

- Author context is a batch of `{source, givens}` or `{source, source_text}` records; choose one text representation per source. Do not add `available`, diagram types, audit reasons, coverage counters or other offline metadata. Use system instructions and multi-output few-shots for authoring behavior. Instruction-author admission checks cover nonempty structured fields, source/base identity and exact linkage; mathematical review stays outside this author call.
- For grades 10-12 source expansion, select spatial/solid geometry constructions and exclude real-world application scenes. Supplied Onn problems remain useful authoring references; preserve shared lineage for duplicate presentations.
- Keep all synthetic outputs under `dataset/synthetic/`. Read `state.json`, `report.json`, `source-pool.json` and per-row drawing checkpoints for current progress; do not copy historical chat totals into reports. Preserve `excluded.jsonl` and moved Reconstruct pairs so resume does not resurrect curated-out rows.
- Production `--generate` and `--edit` values are total destination quotas; author/drawing budgets are cumulative. `--resume` keeps the pinned seed/model/harness and original source snapshots. Coverage mode must keep the full selected pool active; use reported missing source IDs instead of restricting new work to previously covered sources.
- Current default Reconstruct export uses reviewed pairs under `dataset/synthetic/reconstruct/`; raw Geo3K is an explicit legacy `--geo3k` import. Preserve exact image/code bytes and frozen family split assignments. An image-hash ID can repeat; retain separate rows and use task/split/row index for prediction identity.
- Training runs on the user's Colab/Kaggle GPU runtime. Prepare inputs and notebooks locally; do not start local fine-tuning. Preserve each notebook's length checks and masking behavior rather than copying a different notebook's defaults.
- Published Hugging Face snapshots and current local exports can differ. Read the selected revision or local `export_report.json` and `split_assignments.json` before comparing them. Exporting Parquet does not upload or replace a published dataset.
- For inference, targets are evaluator references only. Preserve exact predictions, report output compile failures as model outcomes, retain available per-metric scores on evaluation errors, and leave unavailable metrics `null`; follow the current evaluation documentation.

## Source records and assets

- [geometry-k12-vn.md](docs/geometry-k12-vn.md) owns the mathematical geometry scope and source-selection principles.
- [selection.jsonl](dataset/audit_givens/selection.jsonl) is the authoring source ledger. Keep original problem locators and duplicate-source links there. The exporter freezes source-linked split assignments separately from training rows.
- `docs/dataset-selection/` preserves curriculum source manifests; `docs/dataset-selection.json` is their source inventory. `assets/` contains copied selected source crops. Copy selected crops only and verify their source paths and SHA-256 hashes.

## Refresh and verification

After the curriculum corpus has been updated from its final layouts and Markdown, refresh this repository's downstream records:

```powershell
.\.venv\Scripts\python.exe -B tools\refresh_dataset_selection.py --corpus C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums --write
.\.venv\Scripts\python.exe -B tools\prepare_dataset_selection.py --corpus C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums
```

If selected crops need copying, run `tools/dataset_assets.py copy` with the same `--corpus` path.

Before reporting totals, run the selection validator and use its actual output. Check that every referenced source image exists and that each problem's source text and image links match the current Markdown. Use `git diff --check` after edits. Keep docs focused on dataset contents and useful totals, not unrelated survey counts.
