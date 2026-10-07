# JEV-30 bounded source-root selection

Created 2026-10-02 from the prepared problem records and selected image records in docs/dataset-selection/, cross-checked against the current grade 6–9 curriculum Markdown and layout.final.json files. This pack contains exactly 10 distinct source groups intended to seed 10 Generate + 10 Reconstruct + 10 Edit candidates. It contains source roots only: no final task rows, instructions, TikZ targets, rubrics, or approved gold.

Every root is grade 6–9, has a complete exercise/example/practice text span and exactly one selected source crop. The current Markdown line slice equals the prepared manifest source_text; its crop link resolves to the selected crop; the crop exists and its SHA-256 is recorded; the crop basename occurs on the cited page in the current layout. All ten selected crops were visually checked for source selection.

| # | Source group | Grade | Kind | Source labels (problem / crop) | Source location and crop | Edit seed |
|---:|---|---:|---|---|---|---|
| 1 | grade_8_sgk_2-L2270 | 8 | example | A01 / A01 | 8/grade_8_sgk_2/book.final.md:2110–2123; page 50; crop SHA 51f6bbc59768… | construct |
| 2 | grade_7_sgk_1-L560 | 7 | example | A04 / A04 | 7/grade_7_sgk_1/book.final.md:521–537; page 15; crop SHA 218b605cb20f… | rephrase |
| 3 | grade_6_sgk_2-L2328 | 6 | exercise | G01 / G01 | 6/grade_6_sgk_2/book.final.md:2152–2159; page 48; crop SHA 897cb811f148… | rephrase |
| 4 | grade_6_sgk_2-L3083 | 6 | exercise | G02 / G02 | 6/grade_6_sgk_2/book.final.md:2853–2857; page 61; crop SHA d6de820508f1… | change_instance |
| 5 | grade_8_sgk_1-L3849 | 8 | example | G03, G05 / G05 | 8/grade_8_sgk_1/book.final.md:3639–3648; page 79; crop SHA 46bdb2322f19… | render_variant |
| 6 | grade_6_sgk_1-L5091 | 6 | exercise | G07 / G07 | 6/grade_6_sgk_1/book.final.md:4677–4679; page 90; crop SHA acd8f4f8a7a2… | render_variant |
| 7 | grade_9_sgk_2-L3566 | 9 | practice | G08 / G08 | 9/grade_9_sgk_2/book.final.md:3393–3398; page 87; crop SHA a54559deb10b… | render_variant |
| 8 | grade_9_sgk_1-L3547 | 9 | example | G09 / G09 | 9/grade_9_sgk_1/book.final.md:3451–3462; page 85; crop SHA 310a4a24bbe9… | render_variant |
| 9 | grade_9_sgk_1-L4314 | 9 | example | G11 / G11 | 9/grade_9_sgk_1/book.final.md:4200–4228; page 103; crop SHA 4d37a21cb2dc… | construct |
| 10 | grade_6_sgk_1-L1496 | 6 | exercise | G15 / G15 | 6/grade_6_sgk_1/book.final.md:1393–1395; page 28; crop SHA b94ffabe2f5c… | change_instance |

## Source-use constraints

- The source_text field is the exact prepared-manifest text, including worked solutions where the book extract contains them. task_source_excerpt ends immediately before the first Giải section where one exists. Use that excerpt plus the selected crop for task authoring; do not pass worked solutions or the full source pack to the generation worker.
- The structured source_facts separate source-text givens/goals and reviewed image observations. Goals such as “prove OM ⟂ AB,” “I is a midpoint,” and “the circle passes through B” remain goals, never active premises. Image observations cite the whole hashed crop and pixel dimensions; no coordinate or exact length is inferred from approximate pixels.
- grade_8_sgk_1-L3849 has its numeric segment labels in the crop; use the crop to establish label-to-segment placement while keeping the worked Thales solution out of worker input. grade_6_sgk_2-L2328 is figure-dependent; its reviewed facts are a∩b=P, A∈a, B∈b.
- grade_9_sgk_2-L3566 preserves the raw source spelling “Hôi” in the source text; task preparation may correct it only as a documented text-normalization decision.
- Edit seeds are proposed synthetic operations, not source facts or finalized task instructions. Their descendants must retain this root source_group; split assignment is deliberately unassigned pending duplicate review.

## Readiness boundary

These ten sources are ready for task authoring, not ready training samples. Each task still needs a self-contained instruction, an aligned reviewed target, its own frozen rubric, and evidence/checker calibration. The selected-crop status does not certify mathematical target correctness or end-to-end evaluation. The broader source validator previously reported stale grade-8 SGV image anchors; these ten crops were individually verified against current Markdown/layout instead of refreshing unrelated manifests.

Source manifest decisions remain as found (prepared for problem records, selected for crop records). This note does not change aggregate totals, manifest decisions, source images, or curriculum files.
