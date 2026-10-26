# Mathematical geometry diagrams with TikZ

The project builds editable TikZ diagrams for mathematical geometry in grades 6–12. A diagram expresses a configuration through geometric objects, their relationships, constructions, labels and relation marks.

The geometry scope and source-selection principles are defined in [geometry-k12-vn.md](geometry-k12-vn.md).

## Tasks

Generate creates a diagram from a self-contained description of a geometric configuration. Edit applies a specified change to an existing TikZ diagram. Reconstruct recreates the diagram shown in an image. All three tasks produce TikZ source.

```text
Geometric givens and requested constructions -> Generate -> TikZ
Current TikZ and edit instruction            -> Edit -> completed TikZ
Diagram image                               -> Reconstruct -> TikZ
```

<a id="task-inputs"></a>

### Task inputs

| Task | Sample input | Target |
| --- | --- | --- |
| Generate | `instruction`: geometric givens and requested constructions | `target_tikz` |
| Edit | `current_tikz` + `instruction`: the existing diagram and requested change | `target_tikz` |
| Reconstruct | `image`: exactly one diagram image | `target_tikz` |

The `system` message defines task behavior and output format for every task. The `user` message contains the sample input in the table. During training, the `assistant` message contains the exact `target_tikz`.

Reconstruct's user content contains only the diagram image. Shared record schemas store its `instruction` and `current_tikz` as absent or `null`. Its system instruction supplies the reconstruction behavior.

Generate instructions define the named objects, premises, dependencies, branch conditions and drawing scope. Edit instructions define the change against the actual supplied diagram. Completed TikZ from any task can provide the starting state for a subsequent Edit.

### Target representation

The target is the exact TikZ source for one diagram, with a verified render when preparing a training pair. Task system instructions specify the required output format. Shared wrapping, library support and compile bindings follow [dataset conventions](../dataset/CONVENTIONS.md).

## Dataset preparation

Prepare sources from complete geometry examples, practice problems and exercises, plus checked image/code pairs. Preserve the original givens and introduce purposeful auxiliary constructions with explicit definitions.

The current source pool is [dataset/audit_givens/selection.jsonl](../dataset/audit_givens/selection.jsonl). Production and curation artifacts live under `dataset/synthetic/`. [Dataset conventions](../dataset/CONVENTIONS.md) define batching, lineage, checkpoint recovery, image bindings and Parquet export.

A candidate carries its task input, `target_tikz`, `id` and `source`. The source reference resolves to the original problem in the source ledger. The ledger owns the problem text, locator and links between duplicate presentations; the sample does not repeat them.

Split preparation groups all samples from the same original problem, linked Generate/Edit pairs and duplicate diagrams. Freeze those assignments in the split file. Training exports contain only the task input, target and row identity; source lookup and split evidence remain outside model input.

Authoring requests, execution traces, compile artifacts and review decisions belong to their respective process records.

## Quality and evaluation

A useful sample has an unambiguous task input, a mathematically aligned target and readable geometry. Compilation establishes that the code runs. Source and image review establish that it represents the requested configuration.

| Dimension | What is assessed |
| --- | --- |
| Compile | The TikZ source validates and compiles. |
| Mathematical correctness | Observed geometric relations and marked requirements hold. |
| Content coverage | Required objects, connections, curves, labels and relation marks are present. |
| Visual readability | Labels, strokes and objects can be distinguished and associated correctly. |

Offline scoring compares `target_tikz` and `output_tikz`. Supported observations, score availability and batch evaluation are defined in [evaluation.md](evaluation.md). Source/input fidelity remains part of target curation.

## Training and inference

Training uses the task-specific sample input and the exact target response. Inference uses the same system instruction and sample input. Export predictions with their references and row identities for offline scoring.

Notebook input contracts, saved adapters and prediction export are documented in [train/README.md](../train/README.md). Validation supports iteration; test is reserved for the final checkpoint.
