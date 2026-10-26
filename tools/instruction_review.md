# Instruction review and repair

This is instruction acceptance, not target acceptance. Input: task, instruction, source statement/audited givens, and exact current_tikz for Edit. Carry existing IDs and provenance; no render, compiler or additional provenance audit is required here.

Apply the same seven checks to every item:

| Check | Pass condition |
|---|---|
| Source fidelity | Necessary premises, measurements and inequalities are preserved. A proof/calculation conclusion is not a premise. Added constructions are identified by their definition, not an assumed theorem. |
| Completeness | Every active object has its defining parents and carrier; the selected scope is dependency-closed. Named natural objects imply their ordinary structure. |
| Construction validity | The requested objects exist, are nondegenerate and have the stated line/ray/segment, intersection and interior/exterior branch. Spatial projections use the actual world carrier. |
| Purpose | The visible scope exposes a source-relevant relationship or useful auxiliary; neither point padding nor arbitrary connections qualify. A new segment alone is insufficient: a generic midpoint, median or parallel appended without a role in the actual source problem fails, even when mathematically correct. A collection of correctly defined points is insufficient: active points must support visible source-relevant relationships, with their necessary carriers and constructions present. Unused/free points, omitted connecting auxiliaries and tautological coincident-point changes fail this check. |
| Edit delta | One new auxiliary carrier or a short connected construction is absent from the exact current diagram. Keep its existing mathematical content. No standalone circle, full section/plane/solid, rename, rescale, restated theorem or broad redesign. |
| Mathematical variety | Compare full mathematical configuration/scope; renaming, wording or number replacement alone are duplicates. For Edit include the starting configuration and actual change. A repaired item is a revision, not a new diversity claim. |
| Language | Concise mathematical definitions; no coordinates/TikZ recipes, proof request/answer, repeated rendering boilerplate or arbitrary edge inventories. |

Decision: usable_instruction only when all applicable checks pass; needs_revision for a concrete correctable defect; needs_review when a necessary fact cannot be established. Always record the failing condition or concrete reason. Keep existing usable items unchanged.

Repair by the responsible pattern, then reapply all seven checks:

- Conclusion leakage: retain the source premises/definitions and the investigated object; remove the conclusion as an assumed fact.
- Missing carrier/branch/dependency: restore the exact source definition and dependencies. If the source cannot settle it, hold it; never guess.
- Incorrect mathematical role or impossible intersection: use the actual source construction, a valid supporting carrier/branch, or a different purposeful auxiliary. Do not silently impose a special case.
- Broad Edit: retain one useful, absent auxiliary from the proposal and discard independent additions. Preserve exact current_tikz.
- No-op Edit: choose a genuinely absent source-relevant carrier after reading current_tikz. Merely rewording the same addition fails.
- Weak/duplicate scope: keep one representative or restore a purposeful source auxiliary; no quota padding.

Production sequence: author once -> save all proposals -> review/repair -> write supervision.json -> --review-only -> draw positive inputs. Reviewed positives can proceed while unresolved items stay pending. Resume reuses completed author calls and targets; no refill loop bypasses review. TikZ compilation, mathematics, visible content and render readability are a later independent gate. Neither instruction acceptance nor a model verdict approves training pairs.
