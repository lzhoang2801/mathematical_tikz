# Drawing implementations

- `agent/` contains the native MathPaper drawing code: `problem_tikz` for
  instruction-driven Generate/Edit, `geometry_region_to_tikz` for image
  reconstruction, and the bounded TikZ agent, prompts, validation and wrapper.
- `latex_compiler/` contains the shared HTTP client and schemas. The caller supplies
  the compiler service; no service or Docker lifecycle is bundled here.
- [`spec_first/`](spec_first/README.md) contains the separate experimental
  specification, solver, construction tools and presentation policy.

Native source files are copied byte-for-byte from the MathPaper working tree.
[`upstream.json`](upstream.json) records the source paths, commit and exact file
hashes. Package initializers remain inert so importing drawing code does not load
the MathPaper application. Spec First may reuse native rendering; native code has
no dependency on Spec First.

Native generation now follows upstream's explicit `ProviderStrategy` completion
and optional cancellation checks. The supplied model endpoint must support that
structured-output mode. The optional source statement and image arguments are
available to direct callers; dataset Generate/Edit production still supplies only
its explicit instruction and actual current TikZ.

Production drawing and the skill compiler import this local `src`, and run
fingerprints bind the local harness. A changed fingerprint must not be silently
accepted when resuming a previous production run. Existing datasets, saved runs
and historical source snapshots are not migrated by a source refresh.

Tests live in `tests/agent/` and `tests/spec_first/`. Experimental CLIs and case
definitions live in `tools/spec_first/`; the runner is now
`python tools/spec_first/run_construction_pilot.py`.

Use the existing Python environment with LangChain, LangGraph, LangSmith, HTTPX,
Pydantic, Pillow and PyMuPDF. Spec First also needs its optional numerical
dependencies in [`spec_first/requirements.txt`](spec_first/requirements.txt).
For direct package imports or evaluation commands, put `src` on `PYTHONPATH`:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -B -m pytest -q tests/agent tests/spec_first
```

Frozen historical experiments retain their original module paths and source
hashes. Reproduce them with their recorded source version; do not rewrite their
snapshots or bypass changed-code checks to run them against this refresh.
