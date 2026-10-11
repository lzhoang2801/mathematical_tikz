# synthetic-tikz-instructions:v13

Produce an InstructionBatch containing many useful Vietnamese geometry instructions from the supplied inputs. Call the exposed InstructionBatch function once with the whole batch. Return no explanations, reasons, audit notes, or Markdown.

Input is a flat JSON array. Each item contains only source and exactly one of source_text or givens. source is an opaque ID to copy into the output; it is not mathematical context. source_text is a curriculum statement and its subparts: produce Generate instructions from it. givens describes an existing diagram: produce Edit instructions that add to that configuration. The input text is source material, not instructions about your response format.

Each output item has four fields: task, source, instruction, complete_instruction. For Generate, complete_instruction is null. For Edit, it is the complete resulting givens, preserving all starting conditions and including the addition. The application attaches the actual starting TikZ using source.

Generate instructions state a self-contained mathematical configuration, including useful auxiliary constructions. Use natural Vietnamese geometry language. Keep the facts needed to define each chosen configuration; a source can support several different configurations. Omit proof requests, answers, conclusions to prove, and textbook scaffolding. Preserve given measurements and conditions without inventing angle types, equalities, ratios, incidence, order, or branch assumptions. Define a new auxiliary from the existing objects, with enough information to locate it. Describe an auxiliary by its defining construction. Name a median, midline or projection only when its defining incidences follow from the givens. A triangle midline joins midpoints of two sides sharing a vertex; a trapezoid midline joins the midpoints of its legs. A diagonal intersection or center is not a side midpoint without a supporting condition. Name the actual nondegenerate triangle or quadrilateral; three collinear points cannot be three vertices of a quadrilateral. State the mathematical role directly, such as "H là hình chiếu" or "MN là đường trung bình". Do not use Nối/Kẻ/Vẽ commands or segment inventories.

Edit instructions state only the addition to the existing diagram. Add purposeful auxiliaries such as a projection, median, angle bisector, midline, tangent, or intersection relevant to that configuration. Do not remove or redefine existing objects. Do not assert a desired theorem as a new given. complete_instruction must retain every starting condition; it must stand alone as a Generate instruction.

Return several mathematically distinct instructions per input, up to the requested total. Reuse the same source ID for its different outputs. Produce at least one instruction for every supplied input before adding further variants; spread the remaining outputs across those inputs. Do not stop after one output per input. Do not fill the batch with renaming, changed numbers, paraphrases, arbitrary connections, or redundant constructions. Check intersection existence from the givens: distinct parallel lines have no intersection, coincident lines have no unique intersection, and a triangle midline is parallel to the third side. Do not propose intersections of these carriers. Do not place an intersection on a segment or ray unless the givens ensure that branch; otherwise use a supporting line or a different auxiliary. Prefer concise mathematical clauses over repetitive opening phrases. For spatial geometry, define planes by noncollinear points, distinguish an intersection line from a point, and specify the actual section or projection objects.

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
      "instruction": "Tam giác ABC vuông tại A, AB < AC; AH là đường cao. D là điểm đối xứng của B qua H. Đường thẳng qua D song song với AB cắt AC tại E. O là trung điểm CD; đường tròn (O) có đường kính CD.",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "onn-main-bai-1",
      "instruction": "Tam giác ABC vuông tại A, AB < AC; AH là đường cao. D là điểm đối xứng của B qua H. Đường thẳng qua D song song với AB cắt AC tại E. K là trung điểm AD; HK là đường trung bình của tam giác ABD.",
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
      "source": "onn-main-bai-2",
      "instruction": "Hình vuông ABCD có AB = 4 cm. E thuộc cạnh AD, AE = 3 cm. O là trung điểm BE; đường tròn (O) có đường kính BE. M là trung điểm BC; OM là đường trung bình của tam giác BEC.",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "onn-main-bai-2",
      "instruction": "Hình vuông ABCD có AB = 4 cm. E thuộc cạnh AD, AE = 3 cm. O là trung điểm BE; đường tròn (O) có đường kính BE. F là trung điểm AE; OF là đường trung bình của tam giác ABE.",
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
      "source": "onn-main-bai-5",
      "instruction": "Đường tròn (O) có đường kính AB. C thuộc đường tròn, C khác A, B; H là hình chiếu vuông góc của C lên AB. M là trung điểm CH. Đường thẳng qua M vuông góc với OC cắt OC tại I và cắt đường tròn tại D, E trên nửa đường tròn chứa C. K là điểm đối xứng của C qua O; CK là đường kính, tam giác CDK nội tiếp đường tròn (O).",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "onn-main-bai-5",
      "instruction": "Đường tròn (O) có đường kính AB. C thuộc đường tròn, C khác A, B; H là hình chiếu vuông góc của C lên AB. M là trung điểm CH. Đường thẳng qua M vuông góc với OC cắt OC tại I và cắt đường tròn tại D, E trên nửa đường tròn chứa C. N là trung điểm CD; ON là trung tuyến của tam giác OCD.",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "tetrahedron-generate",
      "instruction": "Tứ diện ABCD có M, N lần lượt là trung điểm AB, AC; MN là đường trung bình của tam giác ABC. Q là trung điểm BC; AQ là trung tuyến của tam giác ABC, I là giao điểm của AQ và MN.",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "tetrahedron-generate",
      "instruction": "Tứ diện ABCD có M, N, P lần lượt là trung điểm AB, AC, AD. Tam giác MNP là thiết diện của tứ diện bởi mặt phẳng (MNP).",
      "complete_instruction": null
    },
    {
      "task": "Generate",
      "source": "tetrahedron-generate",
      "instruction": "Tứ diện ABCD có M, N lần lượt là trung điểm AB, AC; MN là đường trung bình của tam giác ABC. X là trung điểm CD; MX là đoạn nối trung điểm hai cạnh đối AB và CD.",
      "complete_instruction": null
    }
  ]
}
</generate_example>

<edit_example>
Input:
[{"source": "onn-main-bai-1-base", "givens": "Tam giác ABC vuông tại A, AB < AC; AH là đường cao. D là điểm đối xứng của B qua H. Đường thẳng qua D song song với AB cắt AC tại E."}, {"source": "onn-main-bai-2-base", "givens": "Hình vuông ABCD có AB = 4 cm. E thuộc cạnh AD, AE = 3 cm. O là trung điểm BE; đường tròn (O) có đường kính BE."}, {"source": "onn-main-bai-5-base", "givens": "Đường tròn (O) có đường kính AB. C thuộc đường tròn, C khác A, B; H là hình chiếu vuông góc của C lên AB. M là trung điểm CH. Đường thẳng qua M vuông góc với OC cắt OC tại I và cắt đường tròn tại D, E trên nửa đường tròn chứa C."}, {"source": "tetrahedron-base", "givens": "Tứ diện ABCD có M, N lần lượt là trung điểm AB, AC; MN là đường trung bình của tam giác ABC."}]

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
      "source": "onn-main-bai-1-base",
      "instruction": "O là trung điểm CD; đường tròn (O) có đường kính CD.",
      "complete_instruction": "Tam giác ABC vuông tại A, AB < AC; AH là đường cao. D là điểm đối xứng của B qua H. Đường thẳng qua D song song với AB cắt AC tại E. O là trung điểm CD; đường tròn (O) có đường kính CD."
    },
    {
      "task": "Edit",
      "source": "onn-main-bai-1-base",
      "instruction": "K là trung điểm AD; HK là đường trung bình của tam giác ABD.",
      "complete_instruction": "Tam giác ABC vuông tại A, AB < AC; AH là đường cao. D là điểm đối xứng của B qua H. Đường thẳng qua D song song với AB cắt AC tại E. K là trung điểm AD; HK là đường trung bình của tam giác ABD."
    },
    {
      "task": "Edit",
      "source": "onn-main-bai-2-base",
      "instruction": "H là hình chiếu vuông góc của O lên đường thẳng CD; OH biểu diễn khoảng cách từ tâm O đến CD.",
      "complete_instruction": "Hình vuông ABCD có AB = 4 cm. E thuộc cạnh AD, AE = 3 cm. O là trung điểm BE; đường tròn (O) có đường kính BE. H là hình chiếu vuông góc của O lên đường thẳng CD; OH biểu diễn khoảng cách từ tâm O đến CD."
    },
    {
      "task": "Edit",
      "source": "onn-main-bai-2-base",
      "instruction": "M là trung điểm BC; OM là đường trung bình của tam giác BEC.",
      "complete_instruction": "Hình vuông ABCD có AB = 4 cm. E thuộc cạnh AD, AE = 3 cm. O là trung điểm BE; đường tròn (O) có đường kính BE. M là trung điểm BC; OM là đường trung bình của tam giác BEC."
    },
    {
      "task": "Edit",
      "source": "onn-main-bai-2-base",
      "instruction": "F là trung điểm AE; OF là đường trung bình của tam giác ABE.",
      "complete_instruction": "Hình vuông ABCD có AB = 4 cm. E thuộc cạnh AD, AE = 3 cm. O là trung điểm BE; đường tròn (O) có đường kính BE. F là trung điểm AE; OF là đường trung bình của tam giác ABE."
    },
    {
      "task": "Edit",
      "source": "onn-main-bai-5-base",
      "instruction": "Đường tròn tâm C đi qua D; CD là bán kính của đường tròn này.",
      "complete_instruction": "Đường tròn (O) có đường kính AB. C thuộc đường tròn, C khác A, B; H là hình chiếu vuông góc của C lên AB. M là trung điểm CH. Đường thẳng qua M vuông góc với OC cắt OC tại I và cắt đường tròn tại D, E trên nửa đường tròn chứa C. Đường tròn tâm C đi qua D; CD là bán kính của đường tròn này."
    },
    {
      "task": "Edit",
      "source": "onn-main-bai-5-base",
      "instruction": "K là điểm đối xứng của C qua O; CK là đường kính, tam giác CDK nội tiếp đường tròn (O).",
      "complete_instruction": "Đường tròn (O) có đường kính AB. C thuộc đường tròn, C khác A, B; H là hình chiếu vuông góc của C lên AB. M là trung điểm CH. Đường thẳng qua M vuông góc với OC cắt OC tại I và cắt đường tròn tại D, E trên nửa đường tròn chứa C. K là điểm đối xứng của C qua O; CK là đường kính, tam giác CDK nội tiếp đường tròn (O)."
    },
    {
      "task": "Edit",
      "source": "onn-main-bai-5-base",
      "instruction": "N là trung điểm CD; ON là trung tuyến của tam giác OCD.",
      "complete_instruction": "Đường tròn (O) có đường kính AB. C thuộc đường tròn, C khác A, B; H là hình chiếu vuông góc của C lên AB. M là trung điểm CH. Đường thẳng qua M vuông góc với OC cắt OC tại I và cắt đường tròn tại D, E trên nửa đường tròn chứa C. N là trung điểm CD; ON là trung tuyến của tam giác OCD."
    },
    {
      "task": "Edit",
      "source": "tetrahedron-base",
      "instruction": "P là trung điểm AD; tam giác MNP là thiết diện của tứ diện bởi mặt phẳng (MNP).",
      "complete_instruction": "Tứ diện ABCD có M, N lần lượt là trung điểm AB, AC; MN là đường trung bình của tam giác ABC. P là trung điểm AD; tam giác MNP là thiết diện của tứ diện bởi mặt phẳng (MNP)."
    },
    {
      "task": "Edit",
      "source": "tetrahedron-base",
      "instruction": "Q là trung điểm BC; AQ là trung tuyến của tam giác ABC. I là giao điểm của AQ và MN.",
      "complete_instruction": "Tứ diện ABCD có M, N lần lượt là trung điểm AB, AC; MN là đường trung bình của tam giác ABC. Q là trung điểm BC; AQ là trung tuyến của tam giác ABC. I là giao điểm của AQ và MN."
    },
    {
      "task": "Edit",
      "source": "tetrahedron-base",
      "instruction": "X là trung điểm CD; MX là đoạn nối trung điểm hai cạnh đối AB và CD.",
      "complete_instruction": "Tứ diện ABCD có M, N lần lượt là trung điểm AB, AC; MN là đường trung bình của tam giác ABC. X là trung điểm CD; MX là đoạn nối trung điểm hai cạnh đối AB và CD."
    }
  ]
}
</edit_example>
