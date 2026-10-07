# TikZ improvement: dataset → harness → models

Working plan, 2026-09-22. The output contract remains ordinary TikZ for Generate, Reconstruct and Edit, with the four shared evaluation criteria in [the problem statement](K-12%20Mathematical%20Diagrams%20with%20TikZ.md). Generation stays direct to TikZ; DiagramIR is used after generation for executable verification, as in Concept C of the problem statement.

Priority research question from the user's review: [select which candidate facts need to be communicated by the diagram](diagram-information-selection.md). Separate fact extraction, geometric constraints and visible information; count only under a declared annotation unit and measure contribution with controlled omissions. Do not solve this with an expanding list of shape-specific notation exceptions.

## Research update - 2026-10-02

Implementation location (2026-10-03): new evaluation code, tests, controlled cases and reports belong to `problem_tikz`. MathPaper supplies the shared drawing harness and compiler wrapper. The current deterministic two-TikZ comparator is documented in [the v2 development protocol](tikz-pair-demo.md); its code is under `evaluation/`. It measures reference proportions and emitted content, with orientation and collision evidence reported separately. Its development controls do not establish instruction correctness or held-out evaluator reliability.

Research priority: the project has no established, validated evaluation protocol yet. Start from the [published evaluation protocols](tikz-dataset-evaluation-strategy.md#how-published-work-evaluates-diagrams): human reference judgments, evaluation of candidate metrics against those judgments, explicit failure denominators, and held-out validation. Compiler/parser prototypes are possible components, not the scientific basis for an evaluator.

The follow-up [givens, TikZ target and evidence contract](tikz-data-contract.md) specifies typed augmentation operations, source-group splitting across all three tasks, a pinned harness source profile, criterion-level evidence and limitations, and reproducible diversity/trace requirements. It is a reviewable proposal; current tooling and candidates are not claimed to satisfy it. Synthetic generation waits for the listed contract, source and verifier gates.

The [dataset and evaluation strategy](tikz-dataset-evaluation-strategy.md) reviews all twelve local papers, current TypeSafe Jev documentation and contrasting judge research, then specifies a rapid three-task dataset and SFT sequence. It distinguishes proposals from implemented behavior and preserves direct TikZ generation with offline verification.

The [Jev research proposal](tikz-dataset-evaluation-strategy.md#using-typesafe-jev) now includes semantic binding, assisted IR assembly, coverage/equivalence judgments, Edit preservation and givens/rubric audits. Its first comparison separates the effect of extracted observations from Jev's contribution beyond deterministic checks. Learned semantic scores, executable mathematical checks and independent target approval are reported separately; the proposal is not an implemented evaluator.

Current audit corrections: the selection validator fails on stale grade-8 image anchors, although read-only reconciliation finds the source files and assets intact; the eight development candidates remain unapproved. MathPaper now uses one native drawing agent without a separate automatic reviewer. Local candidate tools still reference its removed compiler module. Resolve these compatibility and source-reference issues before new preparation runs. The September implementation descriptions and measurements below are historical, not a statement of the current checkout.

## Research extension — 2026-09-28

The current research design is now recorded in three linked documents:

- [Related works](tikz-related-work.md): 10 local papers and 16 additional works, with source evidence, limitations and transfer decisions.
- [Research protocol](tikz-research-protocol.md): E0–E9, including hypotheses, controls, metrics, resource caps, dataset lineage and decision gates.
- [Paper register](papers/README.md): versions, primary links, reading depth, local PDF hashes and metadata discrepancies.

The next executable research slice is **E0–E4**: approved targets and isolated evaluation; verifier calibration; information-selection controls; bounded feedback and Edit preservation. **E5–E6** then test local SFT and approved repair pairs. **E9** separates model and harness effects on a frozen test set. Augmentation/DPO/RL (E7–E8) are conditional extensions, not prerequisites.

The harness audit confirms that the author call limit excludes structured reviewer retries; new comparisons must cap and record total author/reviewer/extractor/selector usage. The offline DiagramIR command consumes supplied IR and does not yet provide extraction or online requirement feedback. These are proposed small extensions to the existing harness, not implemented features.

The source validator was rerun on 2026-09-28: **2,204 selected images, 851 prepared problems**; **285 images and 34 problems** remain review items. The eight pilot/phase-1 target proposals remain drafts. No new model experiment, training run, corpus edit or target approval was performed in this research pass.

The implementation, pilot measurements and test results below are historical snapshots from the earlier work; the E0–E9 protocol does not claim to have rerun them. The phase table remains the work queue; the protocol specifies how to test its research claims.

The primary claim is deliberately narrow and falsifiable: on the same frozen, rendered initial TikZ, do checker observations improve independently adjudicated strict-task success over the same model receiving the same source-derived requirements without checker observations (V−R), without damaging correct cases? Self-review (S) is a secondary operational comparator, separating total package value (V−S) from the benefit of explicit requirements alone (R−S). The protocol defines blinded scoring of the shared initial output and every repair, full-pipeline reporting for generation/render failures, paired source-group analysis, false-accept/false-reject gates, natural-versus-mutant holdouts and a no-evidence decision rule. Self-review acceptance, compile success and LLM rubric pass remain separate diagnostics.

## What is established

- The local source validator passes: **2,204 selected images** and **851 prepared problems** (165 examples, 116 practice problems, 570 exercises). All selected asset hashes match. Separately, 285 image records and 34 problem records need review. These are source-readiness counts, not training-pair counts.
- Source refresh in check mode reports no removed lines or reanchored rows. The two selected rows in `grade-12.additional-images.jsonl` already occur in the primary grade-12 manifest; do not add them again.
- The corpus delivery metadata still records pending human review. Source linkage and compilation alone do not establish approved reference targets.
- `mathmath` already has the shared bounded drawing agent, compiler, deterministic label placement and render review. Use these directly. The paths in the original handoff have moved: `workflows/problem_tikz.py`, `workflows/geometry_tikz.py`, `workflows/tikz.py`, `prompts/problem_tikz.py`, `prompts/tikz.py`, `schemas/tikz.py`, `evaluation/problem_tikz.py` and `evaluation/problem_tikz_experiment.py`.
- The current `problem_tikz` contract is required `instruction` plus optional `current_tikz`. Author and reviewer receive the same explicit inputs; invocations do not retain conversations, attempts or call budgets. Solve/workspace callers select and describe the necessary facts. The pilot snapshot below retains its original prompt versions and results from before this API change.
- The legacy evaluator grades statement-derived rubrics. It does **not** yet implement the three-task comparison with `target_tikz` required here. Its fixture caller and tests now use explicit instructions; removed invocation-record bookkeeping has not been restored.

The machine-readable snapshot is [tikz-improvement-baseline.json](tikz-improvement-baseline.json). The pilot's complete source statements, layout evidence and target-review status live in [tikz-pilot.jsonl](dataset-selection/tikz-pilot.jsonl).

## Work completed in this pass

1. Delegated dataset/source validation, harness audit, current-paper research and local-runtime inspection to four subagents; independently checked their findings before integration.
2. Added `langchain-openai` to `mathmath` and its lockfile. The existing `BaseChatModel` injection already handles it; no Ollama adapter was added. Dependency resolution required `langchain-core` 1.6.1 → 1.6.4.
3. Fixed experiment hashes that omitted the actual author instruction, shared harness instruction/version, tool description and fixed evaluator policy. Added focused regression checks so changing these components changes the relevant hash.
4. Created two source-grounded Generate candidates: grade-6 exercises 4.2 and 4.3, at Markdown lines 4333 and 4335 and PDF page 82 (`page_idx=81`). Their targets require human review before benchmark/training use.
5. Ran the same existing drawing harness on those two statements with Gemini and Ollama, with at most two author calls per case and LangSmith tracing. Preserved failed attempts and unmodified original model outputs.
6. Recorded information selection as phase 0 after the user's review. Deferred the attempted production notation-prompt changes: candidate counting and contribution need annotations and evidence before a new policy is adopted. The current prompt implementation remains v0.85; the evaluator prompt remains v14.

| Actual pilot outcome | Equilateral triangle, side 2 cm | Square, side 5 cm |
| --- | --- | --- |
| Gemini `gemini-3.5-flash-lite` | 1 attempt; compiled and workflow accepted; 31.5 s | 2 attempts; compiled, unresolved right-angle mark; 56.62 s |
| Ollama `hf.co/unsloth/Qwen3.5-0.8B-GGUF:UD-Q4_K_XL` | API 500: incomplete JSON arguments for `render_tikz`; 18.28 s | Same tool-argument error; 15.57 s |

Independent source/render inspection confirms triangle sides of 2 units and readable marks/labels. The square has correct 5-by-5 coordinates but a visible extra stroke below A, matching its review issue. Workflow acceptance is not an independent accuracy score. These two easy cases are a wiring and failure-discovery pilot, not a model ranking or representative benchmark. Both Ollama failures occurred before a render; they are not TeX compilation failures. Their token usage is unavailable, even though the trace aggregate reports zero.

The pilot manifest now also contains two manually revised target proposals, compiled through the same wrapper and visually inspected under `runs/tikz-pilot-targets/`. They retain the exact geometry and explore fewer visible marks. Each records the original model output, manual changes and artifact hashes; both remain `needs_review` with human review pending. These proposals illustrate the information-selection question, not a new general notation rule.

All four pilot traces were read back from the configured LangSmith project. Gemini's two trace totals are 8,757 and 23,199 tokens; original run IDs and paths are recorded in the baseline JSON. An earlier inspected geometry run took eight render attempts and about 245 s, so record repair cost alongside the final outcome.

## Next work, in order

| Phase | Deliverable | Completion criterion | Delegated work |
| --- | --- | --- | --- |
| 0. Information selection | Source-backed annotations of candidate facts and their contribution | A consistent counting unit, explicit drawing scope and reviewed reasons to show/omit information; test omissions without altering geometry | Annotate candidate facts, inspect alternatives and document disagreements |
| 1. Reference targets | A small, reviewed seed set for all three tasks | Every ready row has a complete task input, valid `target_tikz`, source provenance, compiled target and reviewed render | Curate complete problems, reconstruct selected crops, inspect labels/relations and propose corrections |
| 2. Evaluation alignment | Extend the existing evaluator to the shared task contract | Targets go only to the isolated grader; worker and automatic reviewer receive only task inputs; tests cover all three routes and reference isolation | Extend the migrated evaluator tests to all three tasks, check fixtures and artifact correspondence |
| 3. Harness baseline | Failure cases and one-variable comparisons | Each change is supported by a saved failure, deterministic regression check where applicable and before/after renders | Reproduce failures; inspect geometry, source diagnostics and review errors |
| 4. Local/cloud comparison | Gemini and OpenAI-compatible local models on the same frozen set | Same prompts, renderer, task inputs and call bounds; fixed independent grader plus human review | Run bounded batches; collect invalid tool calls, compile outcomes, latency and usage |
| 5. Supervised training | Direct-TikZ SFT/LoRA pilot | Improvement on held-out sources over the untuned checkpoint, with no material regression in the shared criteria | Audit training examples, build task-balanced exports, run controlled training jobs |
| 6. Research experiments | Justified data/reward ablations | Findings survive source-disjoint evaluation and human inspection | Compare task mixtures, teacher filtering and repair trajectories; try RL only after reward validation |

The primary agent owns the contract, priorities, integration and final review. Each subagent gets a bounded case list or file set; do not run parallel edits on the same files. Do not run formatter checks or automatic formatting; the user handles that at commit time.

### Dataset decisions

- **Generate:** author a self-contained instruction from a complete example/practice/exercise, retaining source provenance separately. Include essential construction facts from its image when needed; the drawing workflow receives neither the source problem nor its image implicitly.
- **Reconstruct:** use a selected crop and a reconstruction instruction. `geometry_region_to_tikz` currently supplies a fixed instruction; add a caller instruction only when the dataset needs it, keeping wording under `prompts/`.
- **Edit:** start from reviewed current TikZ and a concrete requested change. Store the completed target. A correction from an observed failed run is a useful candidate only when the requested change and unchanged geometry are checked.
- Keep source selection separate from task readiness. A generated proposal can contain `target_tikz` while its status is `needs_review`; it must not enter ready counts or training exports yet.
- Begin with coverage of available taxonomy types and known failures, not an arbitrary large sample count. Generate's selected problem sources currently cover grades 6–9; Reconstruct sources cover grades 6–12. Do not invent grade-10–12 Generate records.
- Group related records before splitting: the same original problem/crop, image digest, dependent context, paraphrase and derived Edit examples stay together. Also inspect SGK/SGV duplicates and near-duplicates across books. Freeze a held-out group before teacher generation, prompt tuning or training.
- Preserve task, grade, types, source kind, book/role, source locations and asset digests. Do not silently relabel from chapter titles or promote draft model outputs into targets.

### Harness and evaluation decisions

- Keep one renderer and one safe standalone wrapper. Validation, artifact writes and compilation remain deterministic. Models propose constructions and extract structure; executable DiagramIR checks provide verification evidence. A second model's rubric verdict is not a reference-target acceptance gate.
- Keep fact selection at the caller/dataset boundary and diagram execution stateless. An edit invocation receives its current TikZ explicitly. Legacy evaluation fixtures may assemble instructions from source statements at the evaluation boundary; never restore an implicit problem dependency inside the drawing workflow.
- The same four criteria apply to all tasks: compilation, mathematical/structural correctness, completeness and readability. For Edit, applying the requested change and preserving unaffected objects are instances of correctness/completeness, not a separate evaluation framework.
- Compare against `target_tikz` semantically and visually; exact source equality is not a correctness metric. Compile both sides using the same wrapper. Never send targets or external grader feedback back into generation or automatic repair.
- Separate source/constraint failures, missing content, layout errors, tool/schema errors, reviewer errors and infrastructure failures. The current square and local JSON failures exercise different layers.
- Record first-attempt and final outcomes, attempt counts, model/review usage, latency, prompt/policy hashes, source-group split, model identity and compiler settings. Error runs remain in the denominator; unavailable usage stays unavailable.
- The current default bounds 16 author calls. Each rendered attempt can cause up to three structured-review invocations: up to 64 logical model invocations overall before provider transport retries. The pilot reduced the author bound to two. Do not describe the author bound as a total API-call bound.
- Keep the grader fixed when comparing workers. Automatic acceptance and rubric scores support review; neither replaces inspection of the rendered diagrams.

## Ollama: the small integration

The local server was already running at `http://127.0.0.1:11434`; no server, model download or adapter was added. The machine has a GTX 1650 Ti with 4 GiB VRAM and the installed Qwen3.5 0.8B quantized model. A direct `ChatOpenAI` connectivity call returned `OK`; the drawing pilot exposed malformed tool arguments. Verify truncation/model output before changing the harness to compensate.

```python
from langchain_openai import ChatOpenAI
from agent.workflows.problem_tikz import problem_tikz
from agent.workflows.tikz import build_tikz_agent

model = ChatOpenAI(
    model="hf.co/unsloth/Qwen3.5-0.8B-GGUF:UD-Q4_K_XL",
    base_url="http://127.0.0.1:11434/v1",
    api_key="ollama",
    temperature=0,
    timeout=120,
    max_retries=0,
    max_tokens=2048,
    reasoning_effort="none",
    use_responses_api=False,
)
agent = build_tikz_agent(model, max_model_calls=2)
result = problem_tikz(
    instruction="Vẽ tam giác ABC vuông tại A và đường cao AH, H thuộc BC.",
    artifact_dir="runs/local-diagram",
    agent=agent,
)
```

The existing experiment runner also accepts `worker_model=model`; keep its grader separate. This follows the [ChatOpenAI compatible-endpoint interface](https://docs.langchain.com/oss/python/concepts/providers-and-models#openai-compatible-endpoints) and [Ollama /v1 support](https://docs.ollama.com/api/openai-compatibility).

Use Ollama for inference and bounded data-candidate generation. Training runs use the selected checkpoint's training stack; deploy a resulting model through Ollama only when its architecture/export is supported. The local GPU inventory is not evidence that a particular LoRA or multimodal training job will fit. Start with a measured small job before committing to hardware or a larger checkpoint.

## CPA: OpenAI-compatible connection

The repository-local `tools/cpa.py` builds `langchain_openai.ChatOpenAI` against CPA using `CPA_BASE_URL`, `CPA_MODEL` and `CPA_API_KEY` from the ignored local `.env` or process environment. `.env.example` documents the fields. Current settings are `http://127.0.0.1:8317/v1` and `gemini-3.8-flash-high`; credentials stay outside source control. Existing LangSmith settings fall back to the sibling MathPaper `.env`, without modifying that file.

```powershell
..\mathmath\.venv\Scripts\python.exe -B tools\cpa.py
```

This makes one connectivity call with a 60-second model timeout and no provider retries, enables LangSmith tracing, verifies the saved trace, and stores its response, usage and trace URL under `runs/cpa-connectivity/<run-id>/result.json`. Reuse `from tools.cpa import build_model` and inject `build_model()` into `build_tikz_agent` for an explicitly scoped drawing run. The connectivity command itself does not generate dataset records.

Verified on 2026-10-05: CPA advertised and accepted `gemini-3.8-flash-high`; the response was `CPA connection OK`. Response metadata reported `gemini-3.8-flash-n`, with 7 input tokens and 103 output tokens, including 99 reasoning tokens. Preserve requested and returned model identities separately; this observation does not establish the proxy's internal alias mapping. The confirmed LangSmith run ID is `a66174e2-8b74-4ef8-af86-5a8dc40a66c7`.

The implementation follows the documented [ChatOpenAI compatible-endpoint configuration](https://docs.langchain.com/oss/python/concepts/providers-and-models#openai-compatible-endpoints) and [LangSmith tracing context](https://docs.langchain.com/langsmith/trace-with-langchain#trace-without-setting-environment-variables). Chat Completions routing is explicit with `use_responses_api=False`.

## Research shortlist

Checked against primary sources on 2026-09-22. These papers motivate experiments; their published gains do not establish gains on Vietnamese grade-6–12 diagrams.

| Paper/version checked | Relevant experiment here |
| --- | --- |
| [AutomaTikZ](https://arxiv.org/abs/2310.00367), ICLR 2024 | Direct text → TikZ SFT baseline; prioritize aligned instructions and valid targets |
| [TikZilla v3](https://arxiv.org/abs/2603.03072v3), revised 2026-09-01, ICLR 2026 | Better data, then SFT → RL with rendered-image reward; first test whether data cleanup and SFT suffice |
| [GeoTikzBridge v2](https://arxiv.org/abs/2603.22687v2), revised 2026-03-27, accepted CVPR 2026 | Image → TikZ supervision and local geometric transformations for Reconstruct |
| [EdiTikZ v2](https://arxiv.org/abs/2609.01409v2), revised 2026-09-14, preprint | Revision-derived edits; joint reconstruction/editing supervision; rendered fidelity and edit application rewards |
| [GeoLoom](https://arxiv.org/abs/2512.08180) and [DiagramIR](https://arxiv.org/abs/2511.08283) | Keep direct TikZ generation; reuse DiagramIR's extraction schema and executable verifier after generation, then calibrate its checks against observed failures |

Initial ablations: untuned versus SFT on the same checkpoint; source-verified versus teacher-filtered data; Generate-only versus joint Generate/Reconstruct/Edit; one-shot versus bounded repair. Keep source groups and grader fixed. Rendering-aware preference/RL training comes later, after checking that its reward agrees with human judgments and cannot reward an empty or incomplete but compilable figure.

External corpora remain separate from the curriculum selection. Check the exact dataset/model revision, license and redistributable subset before importing; an article's headline corpus size does not imply those examples can be redistributed in this repository.

Academic-search audit: four multi-source search requests failed in the adapter with `asyncio.run() cannot be called from a running event loop`, before source-level success/skipped fields were returned. Eight direct arXiv identifier lookups returned matching title/author/year; the adapter retained `manual_needed` for its uncheckable identifier field. Official arXiv pages and linked author repositories were checked separately. This is a focused shortlist, not an exhaustive literature search.

## Verification and continuation

The source-selection validator passed and source refresh was a no-op during the pilot. After the instruction/stateless migration, the combined drawing, caller and evaluation suite has **193 passed, 1 failed**. The failure is the unchanged `test_authored_context_keeps_results_separate_from_complete_proofs`, which expects double newlines while `_author_results_section` at HEAD emits single newlines. Focused Ruff and diff checks pass. Strict mypy passes the two core TikZ files; the six other changed source files report ten existing typing errors in `workflows/workspace.py`, confirmed against its HEAD source. No formatter was run.

The evaluation tests use the real `langsmith.evaluate(..., upload_results=False)` with simulated models and local examples, matching the [official local-evaluation documentation](https://docs.langchain.com/langsmith/local) and the installed SDK. Hosted experiments retain `Client.evaluate`. Dataset input hashes now cover the assembled instruction, while hidden rubrics have a separate hash. Tests check input isolation, caller scope and stale-instruction rejection. The original two-case model pilot has not been rerun under prompt `problem_tikz:v0.86`; no new visual-quality or training result is claimed.

## Phase 1: first target batch and DiagramIR calibration

Historical record, checked on 2026-10-02: the three manifests and verification report linked in this section are absent from the current checkout. The compile and validator results below are retained as past reports and cannot be reproduced from those missing artifacts; today's selection validator fails as noted above. This older eight-row set is separate from the available eight Generate candidates in `candidate-flow-8.jsonl`.

The first batch contains **eight drafts, zero approved targets**: two existing [Generate candidates](dataset-selection/tikz-pilot.jsonl), four [Reconstruct candidates](dataset-selection/phase-1.reconstruct.jsonl), and two [synthetic Edit derivatives](dataset-selection/phase-1.edit.jsonl). Reconstruct covers G01 (segment), G03 (triangle), G07 (trapezoid), and A01 (parabola/axes). Edit adds a median to the pilot triangle and a diagonal to the pilot square. The rows share a `source_group` field and form six source groups; derived records stay in their parent's group. This batch is not a held-out benchmark.

All eight target strings compile with mathmath's existing standalone wrapper and compiler. Subagents compared source/before/after images and recorded provisional differences. Each target has a hash-bound extraction in the exact upstream `TikzIR` schema, with explicit omitted features. These extractions were authored by the agents from the TikZ source; they are not independently certified, and source/target acceptance remains pending human review. No additional Gemini, Ollama, or LangSmith calls were made for this batch.

[verify_diagram_ir.py](../tools/verify_diagram_ir.py) imports the user's local [DiagramIR checkout](../DiagramIR/) at commit `c6fd7405308b781960515495f829a4fa75cb0f33`. It uses the original `TikzIR` and `Evaluator`, without changing upstream or importing its provider-specific backtranslation/compiler stack. Only NumPy and Shapely were added to mathmath's `evaluation` dependency group; Pydantic and Pillow were already installed.

```powershell
# From mathmath: install the optional evaluator dependencies.
uv sync --locked --inexact --group evaluation

# From problem_tikz: run guards, then collect local compile and IR evidence.
..\mathmath\.venv\Scripts\python.exe -B -X utf8 tools\verify_diagram_ir.py --check
..\mathmath\.venv\Scripts\python.exe -B -X utf8 tools\verify_diagram_ir.py docs\dataset-selection\tikz-pilot.jsonl docs\dataset-selection\phase-1.edit.jsonl docs\dataset-selection\phase-1.reconstruct.jsonl --output runs\phase-1\verification
```

Choose a new output directory for each run; the runner refuses to overwrite evidence. The [first report](../runs/phase-1/verification/report.json) records engine/core/font hashes, package versions, input manifest hashes, compile artifacts, raw engine results, and per-check applicability. `runs/` is ignored local evidence, not a committed dataset export.

Observed calibration results:

- Eight targets compiled; seven returned `evidence_only`, and the A01 case returned `findings`. Neither status approves a target. The full source-selection validator also passed unchanged.
- Upstream accepts `{}` as a perfect result and continues after schema errors. The runner rejects empty/invalid IR, nonfinite numbers, zero-area polygons, zero-length segments, missing extraction metadata, stale TikZ bindings, and changed IR files before evaluation. Engine/compiler/render failures are retained as explicit failures.
- Upstream's unconstrained canvas and absent numeric comparisons return `True`. The runner records these as `not_evaluated`, along with shape checks that have no supported shapes to inspect. Segment-only outlines do not establish a closed triangle/square or the required side lengths.
- A01 exposed two false alarms: estimated label overlap between `-1` and `-\frac12`, and numerical proportion errors from interpreting axis ticks as length labels (including parsing the fraction as `12`). Independent source/render inspection found separated glyph bounds at x=123–153 and x=160–193 in the 200-DPI target PNG. The plotted function `y=-2x²-2x+4` has the shown landmarks A=(0,4), B=(-1,4), and vertex I=(-1/2,9/2). The schema also omits the parabola and arrowheads. The target was preserved; changing it to optimize this score would damage the experiment.
- The runnable check covers empty/schema/nonfinite/degenerate-geometry/stale-hash/path rejection, an open versus closed triangle, untested checks, and simulated engine/compiler/render failures. Focused Ruff and diff checks passed. All 68 referenced artifact files matched their hashes/byte counts; source crops/text and target-string bindings also matched. No formatter was run.

The code suggests four bounded research tasks, in this order:

1. **Extraction fidelity.** Compare extracted primitives with the compiled figure; keep deliberate missing/extra primitives as negative controls. Bind every IR to its exact TikZ, and measure omissions separately from engine accuracy. A source hash proves identity, not correct extraction.
2. **Constraint coverage.** Calibrate supported geometric checks with controlled coordinate changes. DiagramIR's `core_mathematical_properties...` mostly checks nondegeneracy; it does not prove the pilot triangle is equilateral or that the square has side 5. Shape recognition from separate segments and axis/function semantics are uncovered work, not prompt wording fixes.
3. **Reference completeness and edits.** Compare produced and target structure for missing/extra objects and preserved relationships, using the same four criteria across tasks. Reuse current/target pairs to test whether deleting the requested median/diagonal is detected. This is separate from a figure being internally consistent.
4. **Information contribution and actual readability.** Keep the candidate-fact research in [its own annotation plan](diagram-information-selection.md). DiagramIR cannot decide whether four right-angle marks help the reader. Calibrate collision findings against the actual TeX render before using its estimated font boxes as feedback.

Production still uses the existing drawing review loop. This pass prepares draft references and executable verifier evidence; replacement of that loop and automatic TikZ→IR extraction need the calibration above. Training exports remain blocked on target review and a source-group split, not on a second model's rubric score.

### Controlled faults: where the paper's scope stops

We then injected five explicit requirement/reference violations into the seed cases and updated the observed IR accordingly. These are controlled evaluator probes, **not** an evaluation of the paper's full LLM backtranslation pipeline or a general false-negative rate.

| Known change | Violated requirement | Upstream result |
| --- | --- | --- |
| Move triangle A from x=1 to x=1.4 | Triangle must be equilateral with side 2 cm | 1.0, no failed checks |
| Move square C from (5,5) to (5.7,5) | Figure must be a square with side 5 cm | 1.0, no failed checks |
| Remove AD from the median Edit | Requested median is missing | 1.0, no failed checks |
| Remove AC from the diagonal Edit | Requested diagonal is missing | 1.0, no failed checks |
| Swap A/B in the G01 reconstruction | Crop fixes the left-to-right order A,C,B | 1.0, no failed checks |

The label swap uses Reconstruct deliberately: the generic Generate instructions do not fix vertex names, so a relabeling there would not necessarily be wrong. As an extraction control, an explicit `Shape2D(type="triangle", cycle=true)` also receives 1.0 before and after breaking equal side lengths. An open triangle with `cycle=false` is detected by the closure check. Thus the limitation persists beyond the line-only encoding, while the supported closure check does work.

The [probe report](../runs/phase-1/controlled-probes/report.json) and [reproduction script](../runs/phase-1/controlled_probes.py) preserve mutations, known violations, paired TikZ/IR, compilation evidence and baseline/raw results. The practical decision is to keep DiagramIR offline as a source of calibrated checks. Acceptance still needs task/reference conditions and evidence that extraction matches the actual drawing; an aggregate self-consistency score cannot supply those conditions.

## 2026-10-06: deterministic support in the native drawing harness

The explicit harness implementation request now has a bounded implementation in MathPaper's existing renderer: literal point-list normalization, construction-derived midpoint ticks/projection corners, and actionable invalid-handoff/native-limit errors. No second drawing loop or geometry solver was introduced. The caller controls annotation policy; the model cannot disable it through tool arguments. Generated annotation scope is removed from edit-model context and recreated during rendering.

The supplied trace problem and Onn_generate Bai 6 were run with self-contained mathematical givens and frozen per-case rubrics, using Gemini 3.5 Flash Lite, at most six model calls per case and verified LangSmith tracing. The current square run uses two model calls and one render instead of four and three, with the required marks; wall time is 35.90 s versus 43.18 s. The harder circle reaches completion with zero render errors but takes 76.15 s; an executable PDF check confirms F incorrectly aliases E, so it fails the mathematical rubric. A subsequent code-only replay adds all three midpoint classes while preserving that geometric failure and the missing tangent corner. These are exploratory diagnostics, not a held-out benchmark or approved dataset rows.

See the [implementation and experiment report](../../mathmath/experiments/tikz_givens_20261006/report.md) for all variants, exact sources, renders, trace links, deterministic replays and limitations. The focused suite has 36 passing tests; seven native PGF visibility checks pass in one compiler call without a model. Formatting remains user-owned.

## 2026-10-06: Onn Generate/Edit dataset and harness calibration

Active user goal: prepare source-grounded Generate→Edit chains from all selected, substantive, complete Onn source problems; update both Solve and TikZ harnesses; run model evaluation only on TikZ; calibrate the existing evaluator against reviewed references, valid alternatives and deliberate mathematical/content/Edit failures. Completion requires actual rows, reviewed renders, lineage and frozen rubrics, implemented shared boundaries, functional checks and saved evaluation evidence. The earlier two-case renderer diagnostic does not complete this goal.

| Agent | Owned output | Required result |
| --- | --- | --- |
| onn_source_stages | dataset/onn-generate-edit-20261006/{source-audit,selection,stage-specs}.jsonl | Audit every Onn TeX source; retain exact source/hash/locators, merge duplicate groups, separate premises/auxiliaries/conclusions, and define dependency-complete staged scopes. |
| targets_main_early | dataset/onn-generate-edit-20261006/drafts/main-early/ | Full Generate/Edit candidates for selected main Bài1–3, with named dependent TikZ, instruction-specific predicates and exact parent-target/current-source chains. |
| targets_main_late | dataset/onn-generate-edit-20261006/drafts/main-late/ | Full staged candidates for main Bài4–6, including reviewed circle branches, meaningful auxiliaries and supported relation marks. |
| solve_handoff_design | MathPaper Solve schema/prompt/workflow/docs and focused handoff tests | Compose explicit drawing inputs from the exact frozen source and accumulated scope contributions; preserve saved records, deferred source order, prior-frame Edit inputs and failure details. |
| evaluation_calibration | evaluation/evaluator.py, tikz_geometry.py, run.py, owning docs/tests and task calibration evidence | Separate reference fidelity from executable instruction requirements, retain unknown/unsupported/target failures and calibrate real Onn negative/positive controls. |
| Primary | Shared TikZ/compiler boundary, integration, compilation, reviewed exports and traced TikZ-only model evaluation | Freeze the final source profile, compile with the shared compiler, integrate cross-family lineage/duplicates, independently review artifacts and report every success/failure without target leakage. |

Secondary-source target authoring and independent visual review are assigned as audit/authoring slots become available. Source files and existing user changes stay intact. All source groups/descendants retain one split; no arbitrary split proportions or training exports are inferred. Real Gemini runs use declared case/call bounds and LangSmith tracing after the instruction/target/rubric freeze. No formatter or second drawing loop is introduced.
