# Synthetic data operation

The production contract and commands are in [dataset conventions](../../../../dataset/CONVENTIONS.md).

- Run `tools/run_synthetic_dataset.py` with explicit Generate/Edit quotas, base count, batch size, author-call budget and drawing-attempt budget.
- Use `dataset/audit_givens/selection.jsonl`; selected source locators and hashes must match the current corpus.
- The instruction model receives `tools/instruction_prompt.md`, a flat batch of {source, source_text} or {source, givens}. It receives no target TikZ, image, rubric, skill text or orchestration instructions.
- Application code resolves an Edit's base ID to its exact actual TikZ. The drawing model receives only instruction and current TikZ.
- Reuse a completed Edit target for its separately authored full Generate instruction; preserve all source lineage and review each pairing.
- Resume the same command with `--resume`. Source/harness identity is pinned; prompt revisions affect future author calls only; completed work is reused and calls remain bounded.
- Compiled candidates can seed candidate descendants. They are not independently reviewed targets. Inspect `review.html`, source fidelity and mathematical requirements before recording ready review or exporting assigned splits.
- Use `tools/generate_instruction.py` only for instruction-only requests. Use `tools/draw_instruction.py --export` for reviewed final rows.

This guide is for operators, not a model prompt. The repository's current AGENTS.md governs delegation and verification.
