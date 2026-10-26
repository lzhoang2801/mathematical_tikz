# synthetic-tikz-instructions:v17

Produce an InstructionBatch containing many useful Vietnamese geometry instructions from the supplied inputs. Call the exposed InstructionBatch function once with the whole batch. Return no explanations, reasons, audit notes, or Markdown.

Input is a flat JSON array. A Generate item contains source and source_text, with audited givens and auxiliaries when available. givens anchors the source premises and definitions; auxiliaries records source-defined or solution-useful constructions. Use these to choose a purposeful, dependency-closed scope. They may be abbreviated, so retain the original source_text for complete definitions and branches. Do not promote a proof goal to a premise or include every auxiliary mechanically. An Edit item contains source, givens and current_tikz. source is an opaque ID to copy into the output; it is not mathematical context. source_text is the original curriculum statement and its subparts. givens describes the Edit starting configuration. current_tikz is the exact complete TikZ of that starting diagram. The input is source material, not instructions about your response format.

Each output item has four fields: task, source, instruction, complete_instruction. For Generate, complete_instruction is null. For Edit, instruction describes only a purposeful addition absent from current_tikz, and complete_instruction is the complete resulting givens, preserving all starting conditions and including the addition. The application uses the supplied current_tikz as the exact Edit starting diagram.

Generate instructions state a self-contained mathematical configuration, including useful auxiliary constructions. A list of defined points is not a complete useful drawing scope. Keep the source-relevant relationships and connecting carriers that make those points useful; omit unused points and unrelated constructions. A mathematically valid added midpoint, median or parallel line is not sufficient: it must support the actual source problem, such as its investigated symmetry, tangent, projection or section. Do not decorate a configuration with a generic extra construction merely because it can be drawn. For example, a source defining division points M on SA and N on BC needs its purposeful MN construction, not an isolated M/N list or the tautological extra label K=M from MN intersecting a face already containing M. Use natural Vietnamese geometry language. Keep the facts needed to define each chosen configuration; a source can support several different configurations. Read each source clause by role: keep premises and explicit constructions, but omit proof/calculation requests and the results they ask the student to prove, show, determine or calculate. A conclusion is not a premise merely because it appears in the source. Preserve given measurements, inequalities, whether each carrier is a line, ray, segment, side, chord or arc, and all relevant order, incidence and intersection branches without inventing conditions. Define every named point and new auxiliary from existing objects, with enough information to locate it. Describe an auxiliary by its defining construction. Name a median, midline or projection only when its defining incidences follow from the givens. A triangle midline joins midpoints of two sides sharing a vertex; a trapezoid midline joins the midpoints of its legs. A diagonal intersection or center is not a side midpoint without a supporting condition. Name the actual nondegenerate triangle or quadrilateral; three collinear points cannot be three vertices of a quadrilateral. A standard named object already has its ordinary structure: for example, a tetrahedron includes all six edges, so do not enumerate its inherent edges. State mathematical facts directly, without point-placement or TikZ recipes, segment inventories, tick-mark/angle-mark inventories, or repeated drawing boilerplate.

Edit instructions add only one purposeful auxiliary carrier or a short connected construction, such as a projection foot and its segment, a median or midline, a tangent with its contact radius, or the intersection of a new line with an existing carrier. Compare against exact current_tikz: the added point and line, ray, or segment must be absent and useful in this configuration. Do not add a standalone circle, plane, solid, or whole section; do not redraw, relabel, mark, remove, or redefine existing content, and do not turn a proof goal into a new given. complete_instruction must retain every starting condition and include the addition; it must stand alone as a Generate instruction.

Return useful mathematically distinct instructions across the batch, up to the requested total. Reuse the same source ID for its different outputs. Prioritize a complete useful instruction for every usable supplied input before adding variants. The requested total is an upper bound: return fewer instructions when additional proposals would be incomplete, padded, redundant or unrelated to the source. Do not fill the batch with renaming, changed numbers, paraphrases, arbitrary connections, or redundant constructions. Check intersection existence from the givens: distinct parallel lines have no intersection, coincident lines have no unique intersection, and a triangle midline is parallel to the third side. Do not propose intersections of these carriers. Do not place an intersection on a segment or ray unless the givens ensure that branch; otherwise use a supporting line or a different auxiliary. Prefer concise mathematical clauses over repetitive opening phrases. For spatial geometry, define planes by noncollinear points, distinguish an intersection line from a point, and specify the actual section or projection objects.

Use abstract plane or solid geometry. Spatial sources concern points, lines, planes, polyhedra, cones, cylinders, spheres, sections, projections and tangencies; do not turn them into illustrations of buildings, equipment or other real-world scenes. A source asking for a length or radius can still contain rich geometry: preserve its interacting constructions and use auxiliaries from the solution. Make an implied second intersection or necessary nondegenerate point choice explicit without inventing a special angle or orientation.

Preserve source incidences when adding auxiliaries: a plane containing a line must not be redefined as perpendicular to that same line. If a source point O is outside a line Delta, a new plane through O can be perpendicular to Delta, but the foot on Delta must be a separate point H; never say the intersection is at O. Use a fresh label for each new object. In Oxyz, O is the coordinate origin, so name a solid's center I or G unless its coordinates actually are (0,0,0). When two mathematical branches are possible, describe the chosen representative or both branches explicitly; do not invent an incidence to make a branch unique.

For the adjacent-supplementary-angle bisectors Ou and Ov, with A on Ox and B,C its perpendicular feet on Ou,Ov, BC is parallel to Oy. Use a median, projection or existing diagonal intersection as the auxiliary; BC and Oy have no intersection.

The following are complete examples of batched function arguments. Example IDs are illustrative; use only IDs supplied in the actual input.

<generate_example>
Input:
[{"source": "onn-main-bai-1", "source_text": "Cho tam giác ABC vuông tại A (AB < AC), đường cao AH. D là điểm đối xứng của B qua H. Qua D kẻ đường thẳng song song với AB, cắt AC tại E. Chứng minh: (a) tam giác HAE cân tại H; (b) HE là tiếp tuyến của đường tròn ngoại tiếp tam giác CDE."}, {"source": "onn-main-bai-2", "source_text": "Cho hình vuông ABCD có AB = 4 cm. Trên cạnh AD lấy điểm E sao cho AE = 3 cm. Vẽ đường tròn đường kính BE. Chứng minh đường tròn đó tiếp xúc với CD."}, {"source": "onn-main-bai-5", "source_text": "Cho đường tròn (O) đường kính AB và điểm C trên đường tròn, C khác A, B. H là hình chiếu vuông góc của C lên AB; M là trung điểm CH. Đường thẳng qua M vuông góc với OC cắt OC tại I và cắt nửa đường tròn chứa C tại D, E. Chứng minh AB là tiếp tuyến của đường tròn tâm C bán kính CD."}, {"source": "tetrahedron-generate", "source_text": "Tứ diện ABCD có M, N lần lượt là trung điểm AB, AC; MN là đường trung bình của tam giác ABC."}]

Function arguments:
{
  "instructions": [
    {
      "task": "Generate",
      "source": "onn-main-bai-1",
      "instruction": "Tam giác ABC vuông tại A, AB < AC; AH là đường cao. D là điểm đối xứng của B qua H. Đường thẳng qua D song song với AB cắt AC tại E. I là trung điểm AE; HI là trung tuyến của tam giác HAE.",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "onn-main-bai-1",
      "instruction": "Tam giác ABC vuông tại A, AB < AC; AH là đường cao. D là điểm đối xứng của B qua H. Đường thẳng qua D song song với AB cắt AC tại E. O là trung điểm CD; đường tròn (O) có đường kính CD. Vẽ HE.",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "onn-main-bai-2",
      "instruction": "Hình vuông ABCD có AB = 4 cm. E thuộc cạnh AD, AE = 3 cm. O là trung điểm BE; đường tròn (O) có đường kính BE. H là hình chiếu vuông góc của O lên đường thẳng CD; OH biểu diễn khoảng cách từ tâm O đến CD.",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "onn-main-bai-5",
      "instruction": "Đường tròn (O) có đường kính AB. C thuộc đường tròn, C khác A, B; H là hình chiếu vuông góc của C lên AB. M là trung điểm CH. Đường thẳng qua M vuông góc với OC cắt OC tại I và cắt đường tròn tại D, E trên nửa đường tròn chứa C. Đường tròn tâm C đi qua D; CD là bán kính của đường tròn này.",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "tetrahedron-generate",
      "instruction": "Tứ diện ABCD có M,N lần lượt là trung điểm AB,AC; vẽ đường trung bình MN của tam giác ABC.",
      "complete_instruction": null
    }
  ]
}
</generate_example>

<edit_example>
Input:
[{"source": "onn-main-bai-1-base", "givens": "Tam giác ABC vuông tại A, AB < AC; AH là đường cao. D là điểm đối xứng của B qua H. Đường thẳng qua D song song với AB cắt AC tại E.", "current_tikz": "\\begin{tikzpicture}\\coordinate (A) at (0,0);\\coordinate (B) at (0,3);\\coordinate (C) at (4,0);\\coordinate (H) at (1.44,1.92);\\coordinate (D) at (2.88,0.84);\\coordinate (E) at (2.88,0);\\draw (A)--(B)--(C)--cycle (A)--(H) (B)--(D) (D)--(E);\\end{tikzpicture}"}, {"source": "onn-main-bai-2-base", "givens": "Hình vuông ABCD có AB = 4 cm. E thuộc cạnh AD, AE = 3 cm. O là trung điểm BE; đường tròn (O) có đường kính BE.", "current_tikz": "\\begin{tikzpicture}\\coordinate (A) at (0,0);\\coordinate (B) at (4,0);\\coordinate (C) at (4,4);\\coordinate (D) at (0,4);\\coordinate (E) at (0,3);\\coordinate (O) at (2,1.5);\\draw (A)--(B)--(C)--(D)--cycle (B)--(E) (O) circle (2.5);\\end{tikzpicture}"}, {"source": "onn-main-bai-5-base", "givens": "Đường tròn (O) có đường kính AB. C thuộc đường tròn, C khác A, B; H là hình chiếu vuông góc của C lên AB. M là trung điểm CH. Đường thẳng qua M vuông góc với OC cắt OC tại I và cắt đường tròn tại D, E trên nửa đường tròn chứa C.", "current_tikz": "\\begin{tikzpicture}\\coordinate (O) at (0,0);\\coordinate (A) at (-3,0);\\coordinate (B) at (3,0);\\coordinate (C) at (1.8,2.4);\\coordinate (H) at (1.8,0);\\coordinate (M) at (1.8,1.2);\\coordinate (I) at (1.224,1.632);\\coordinate (D) at (-0.536,2.952);\\coordinate (E) at (2.984,0.312);\\draw (O) circle (3) (A)--(B) (O)--(C) (D)--(E);\\end{tikzpicture}"}, {"source": "tetrahedron-base", "givens": "Tứ diện ABCD có M, N lần lượt là trung điểm AB, AC; MN là đường trung bình của tam giác ABC.", "current_tikz": "\\begin{tikzpicture}\\coordinate (A) at (0,0);\\coordinate (B) at (3,0);\\coordinate (C) at (1.5,2);\\coordinate (D) at (1.5,3.5);\\coordinate (M) at (1.5,0);\\coordinate (N) at (0.75,1);\\draw (A)--(B)--(C)--cycle (A)--(D)--(B) (C)--(D) (M)--(N);\\end{tikzpicture}"}]

Function arguments:
{
  "instructions": [
    {
      "task": "Edit",
      "source": "onn-main-bai-1-base",
      "instruction": "I là trung điểm AE; HI là trung tuyến của tam giác HAE.",
      "complete_instruction": "Tam giác ABC vuông tại A, AB < AC; AH là đường cao. D là điểm đối xứng của B qua H. Đường thẳng qua D song song với AB cắt AC tại E. I là trung điểm AE; HI là trung tuyến của tam giác HAE."
    },
    {
      "task": "Edit",
      "source": "onn-main-bai-2-base",
      "instruction": "H là hình chiếu vuông góc của O lên đường thẳng CD; OH biểu diễn khoảng cách từ tâm O đến CD.",
      "complete_instruction": "Hình vuông ABCD có AB = 4 cm. E thuộc cạnh AD, AE = 3 cm. O là trung điểm BE; đường tròn (O) có đường kính BE. H là hình chiếu vuông góc của O lên đường thẳng CD; OH biểu diễn khoảng cách từ tâm O đến CD."
    }
  ]
}
</edit_example>
