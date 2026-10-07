# Grade 6 SGK 1: exhaustive geometry givens audit

- Source manifest: `docs/dataset-selection/grades-6-7.problems.jsonl`; corpus source: `6/grade_6_sgk_1/book.final.md`.
- Audit scope: all 80 manifest rows for this book, ordered by source line. Kept all 74 records carrying geometry labels; excluded the six A04-only number-line/algebra records listed below. There are no mixed A/G labels in this book.
- Verification: every normalized manifest `source_text` equals its stated corpus line span (80/80); every `image_paths` entry exists in the read-only corpus (0 missing). Figure assets for a row are exactly the paths in that row's manifest `image_paths`.
- Readiness: 68 retained rows are `prepared`; six retain `needs_review` status from the manifest: L1378, L5610, L5883, L6057, L6135, L6154. These flags are preserved below.
- Auxiliary-line policy: record only lines explicitly introduced by a source solution. None of the calculation/identification exercises below has a source solution adding a new geometric line. Worked solutions named below use the stated polygon sides, measurements, or already-given diagonals/heights. L6075 is a paper-folding/cutting construction; its fold axes are part of the activity, not a solution-added auxiliary line.
- Figure-dependent facts remain tied to the source crops; do not infer lengths, equalities, or exact coordinates from visual scale. Rows with absent image links or structurally degraded source are flagged explicitly.
- Algebra-only exclusions (A04): `grade_6_sgk_1-L570`, `-L620`, `-L3408`, `-L3715`, `-L3721`, `-L3935`.

## Retained row inventory

### grade_6_sgk_1-L1378 — lines 1275–1281 — `needs_review` — G07
- Givens: rectangle ABCD encoded as an HTML table with the top side divided into segments labeled `a`, `a`, and `1`; the left side is labeled `a`. The table implies width `2a+1` and height `a` only if its cell layout faithfully represents the lost diagram.
- Figure dependency: degraded table markup is the only representation; verify the original crop before using dimensions or subdivision as certain.
- Auxiliary: none evidenced. Goal: write an area expression and evaluate at `a=3 cm`.

### grade_6_sgk_1-L1496 — lines 1393–1395 — `prepared` — G15
- Givens: rectangular prism with three edge lengths `a,b,c`; then `a=5 cm`, `b=4 cm`, `c=3 cm`. Diagram crop supplies the box orientation and dimension placements.
- Figure dependency: one linked prism image; no other stated incidence facts.
- Auxiliary: no solution shown. Goal: express total surface area in `a,b,c`, then evaluate it.

### grade_6_sgk_1-L4679 — lines 4304–4313 — `prepared` — G03,G08
- Givens: regular hexagon ABCDEF, decomposed into six equilateral triangles; the six secondary diagonals are AC, BD, CE, DF, EA, FB. The figure also shows the opposite-vertex segments through O and their crossings.
- Figure dependency: linked hexagon with its interior chords; use the named segment list from text and crop.
- Auxiliary: no solution adding lines. Goal: identify the six equilateral triangles in the decomposition and other equilateral triangles visible in the figure.

### grade_6_sgk_1-L4721 — lines 4333–4333 — `prepared` — G03
- Givens: equilateral triangle with side length 2 cm.
- Figure dependency: none; freely oriented triangle.
- Auxiliary: no solution shown. Goal: draw the specified triangle.

### grade_6_sgk_1-L4723 — lines 4335–4335 — `prepared` — G07
- Givens: square with side length 5 cm.
- Figure dependency: none; freely oriented square.
- Auxiliary: no solution shown. Goal: draw the square.

### grade_6_sgk_1-L4725 — lines 4337–4339 — `prepared` — G07,G15
- Givens: the pictured net is six square panels: four in a horizontal strip, with one square above and one below the second panel; one outer panel is highlighted. No side length is stated.
- Figure dependency: linked net; panel adjacency and highlighted panel come only from the crop.
- Auxiliary: no solution shown. Goal: cut/fold/join the net to make a lidded box.

### grade_6_sgk_1-L4729 — lines 4341–4341 — `prepared` — G07
- Givens: a square sheet (A4 paper is the material), with no dimensions or interior marks specified.
- Figure dependency: a referenced decorative square example; exact internal pattern is optional and student-designed.
- Auxiliary: no solution shown. Goal: draw and decorate a square using a chosen design.

### grade_6_sgk_1-L4733 — lines 4343–4345 — `prepared` — G07
- Givens: a 3-by-3 array of congruent small squares, with A at the lower-left corner and B at the upper-right corner. Allowed route segments are diagonals of small squares.
- Figure dependency: linked square grid; exact cell adjacency is visible in the crop.
- Auxiliary: no solution shown. Goal: give at least two paths from A to B along small-square diagonals.

### grade_6_sgk_1-L4737 — lines 4347–4358 — `prepared` — G03,G07
- Givens: a square sheet and the pictured fold/cut sequence, whose stated objective is an equilateral triangle. No metric side length is given.
- Figure dependency: three linked sequential crops specify fold direction, cut line and resulting piece; do not replace them with an inferred scale.
- Auxiliary: no separate mathematical solution; fold/cut lines are procedural construction marks shown in the source. Goal: fold and cut the sheet to obtain an equilateral triangle.

### grade_6_sgk_1-L4750 — lines 4360–4360 — `prepared` — G08
- Givens: six houses at the six vertices of a regular hexagon. The transformer station must have equal distance to all six houses.
- Figure dependency: no crop; regular-hexagon vertex arrangement stated in text.
- Auxiliary: no solution shown. Goal: locate a point equidistant from the six vertices (the center is a consequence, not an extra given).

### grade_6_sgk_1-L5056 — lines 4642–4646 — `prepared` — G07
- Givens: three quadrilaterals on a square grid: Q-M-N-P has horizontal parallel bases and equal sloping legs; D-E-F-G and I-J-H-K are the other pictured grid quadrilaterals. Grid coordinates are figure-defined.
- Figure dependency: linked image labels all three shapes; identify which are isosceles trapezoids from the actual vertices/edge directions, not appearance alone.
- Auxiliary: no solution shown. Goal: name the isosceles trapezoid(s).

### grade_6_sgk_1-L5081 — lines 4667–4667 — `prepared` — G07
- Givens: rectangle with adjacent sides 6 cm and 4 cm.
- Figure dependency: none.
- Auxiliary: no solution shown. Goal: draw the rectangle.

### grade_6_sgk_1-L5083 — lines 4669–4669 — `prepared` — G07
- Givens: rhombus with side length 4 cm.
- Figure dependency: none; angles are not specified.
- Auxiliary: no solution shown. Goal: draw a rhombus satisfying the side length.

### grade_6_sgk_1-L5085 — lines 4671–4671 — `prepared` — G07
- Givens: parallelogram with one side 6 cm and an adjacent side 3 cm.
- Figure dependency: none; angles are free.
- Auxiliary: no solution shown. Goal: draw a matching parallelogram.

### grade_6_sgk_1-L5087 — lines 4673–4675 — `prepared` — G07,G08
- Givens: regular hexagon ABCDEF with the interior diagonals/chords shown in the linked crop.
- Figure dependency: one linked labeled figure; use its actual line set when counting constituent trapezoids/rectangles.
- Auxiliary: no solution shown. Goal: name all isosceles trapezoids and rectangles in the figure.

### grade_6_sgk_1-L5091 — lines 4677–4679 — `prepared` — G07
- Givens: parallelogram ABCD; diagonals AC and BD intersect at I.
- Figure dependency: linked diagram shows the two diagonals and their crossing.
- Auxiliary: the diagonals are explicit givens, not solution-added lines. No solution provided. Goal: check whether I is the midpoint of each diagonal.

### grade_6_sgk_1-L5095 — lines 4681–4681 — `prepared` — G07
- Givens: an arbitrarily chosen paper rhombus and its two diagonals.
- Figure dependency: no fixed dimensions or labeled vertices; students supply a rhombus.
- Auxiliary: both cutting lines are the rhombus's stated diagonals, not added solution lines. Goal: cut into four pieces and rearrange into a rectangle.

### grade_6_sgk_1-L5097 — lines 4683–4685 — `prepared` — G07
- Givens: six congruent isosceles trapezoids; the linked crop shows their assembly into a table shape. No lengths or angles are stated.
- Figure dependency: table silhouette and piece arrangement are crop-defined.
- Auxiliary: no solution shown. Goal: assemble the six pieces into the pictured table.

### grade_6_sgk_1-L5156 — lines 4742–4760 — `prepared` — G07
- Givens: rectangular billboard, width 5 m and length 10 m; decorative wire follows its perimeter; cost is 40,000 VND per metre.
- Figure dependency: illustration only; dimensions are explicit in text.
- Auxiliary: worked solution uses the rectangle perimeter; no new geometric line. Goal: determine wire cost.

### grade_6_sgk_1-L5176 — lines 4762–4776 — `prepared` — G07
- Givens: rectangular room floor 8 m by 6 m; square tiles have side 40 cm; grout width is ignored.
- Figure dependency: tile-pattern illustration only; no additional subdivision requirement.
- Auxiliary: worked solution uses the two rectangle side lengths and square area; no added line. Goal: determine tile count.

### grade_6_sgk_1-L5192 — lines 4778–4786 — `prepared` — G07
- Givens, part (a): rectangular steel ties 35 cm by 30 cm; total wire length 260 m. Part (b): steel table frame with an isosceles-trapezoid top: bases 1,200 mm and 600 mm, legs 600 mm each, height 730 mm; ignore weld length.
- Figure dependency: two crops, one per subproblem. Part (b) shows vertical support legs under the trapezoid top.
- Auxiliary: no source solution shown. Goal: number of ties in (a) and wire length for one frame in (b); preserve these as two distinct geometric subproblems.

### grade_6_sgk_1-L5229 — lines 4813–4821 — `prepared` — G07
- Givens: parallelogram with adjacent side lengths 3 cm and 5 cm.
- Figure dependency: crop labels one side 5 cm and adjacent side 3 cm; angles are not fixed.
- Auxiliary: worked solution computes perimeter from opposite equal sides; no new line. Goal: perimeter.

### grade_6_sgk_1-L5239 — lines 4823–4850 — `prepared` — G07
- Givens: outer rectangle 160 cm by 60 cm; two interior rhombi, each with side 50 cm, arranged in the pictured grille. Ignore weld length.
- Figure dependency: linked diagram fixes how each rhombus meets the rectangle boundary and each other.
- Auxiliary: worked solution uses the given perimeter components; no new geometric line. Goal: total steel for four identical grilles.

### grade_6_sgk_1-L5293 — lines 4873–4885 — `prepared` — G07
- Givens: parallelogram timber has corresponding base 30 cm and perpendicular height 20 cm (right-angle mark shown).
- Figure dependency: linked crop shows the height foot on the base; the dimensions are stated/shown with the figure.
- Auxiliary: worked solution uses the marked perpendicular height; no extra line. Goal: area.

### grade_6_sgk_1-L5307 — lines 4887–4891 — `prepared` — G07
- Givens: rectangular plot 12 m by 10 m; flower region is parallelogram AMCN and the complement is grass. Figure places M and N at the midpoints of opposite 12 m sides: BM=MC=AN=ND=6 m.
- Figure dependency: linked partition image supplies vertex placement and the midpoint subdivisions.
- Auxiliary: no source solution adds a line. Goal: compute labour cost for flower and grass regions using rates 50,000 and 40,000 VND/m².

### grade_6_sgk_1-L5339 — lines 4917–4929 — `prepared` — G07
- Givens: rhombus ABCD; diagonals AC=8 cm and BD=6 cm.
- Figure dependency: linked crop shows both diagonals crossing inside the rhombus.
- Auxiliary: worked solution uses the two explicitly given diagonals; no added line. Goal: area.

### grade_6_sgk_1-L5353 — lines 4931–4936 — `prepared` — G07
- Givens: rectangular garden 8 m by 5 m; a rhombus is inscribed with its vertices at the rectangle's side midpoints; plant density is 4 roses/m².
- Figure dependency: crop shows the inscribed rhombus and labels the 5 m side; 8 m is stated in text.
- Auxiliary: no source solution shown. Goal: determine number of roses in the rhombus.

### grade_6_sgk_1-L5362 — lines 4940–4940 — `prepared` — G07
- Givens: rectangle ABCD with AB=4 cm and BC=6 cm.
- Figure dependency: none; rectangle type supplies right angles and opposite-side equality.
- Auxiliary: no solution shown. Goal: perimeter and area.

### grade_6_sgk_1-L5364 — lines 4942–4943 — `prepared` — G07
- Givens: rhombus MNPQ with MN=6 cm; all four sides are equal by the named type.
- Figure dependency: none.
- Auxiliary: no solution shown. Goal: perimeter.

### grade_6_sgk_1-L5367 — lines 4945–4947 — `prepared` — G07
- Givens: rectangular garden 15 m by 10 m; gate width is one-third the 15 m length. Figure places the gate opening on a long side; the remaining boundary is fence.
- Figure dependency: linked crop shows opening placement; it appears centered, but only its width and side are stated mathematically.
- Auxiliary: no solution shown. Goal: fence length.

### grade_6_sgk_1-L5371 — lines 4949–4955 — `prepared` — G07
- Givens: trapezoidal field with parallel bases 15 m and 25 m, perpendicular height 10 m, and yield 0.8 kg/m².
- Figure dependency: linked crop labels both bases and shows a right-angle height of 10 m.
- Auxiliary: no source solution shown. Goal: field area and rice yield.

### grade_6_sgk_1-L5379 — lines 4957–4959 — `prepared` — G07
- Givens: floor plan composed of four rectangles: living room 6×8 m, dining/kitchen 6×6 m, hall 2×12 m, WC 2×2 m.
- Figure dependency: linked orthogonal floor-plan crop determines how rooms join; no additional dimensions are legible in prose.
- Auxiliary: no source solution shown. Goal: total floor area.

### grade_6_sgk_1-L5383 — lines 4961–4963 — `prepared` — G07
- Givens: trapezoid ABCD with AB=10 m and DC=25 m; rectangle ABED has area 150 m². Crop shows AB parallel to DC, D-E-C collinear, and BE perpendicular to the bases.
- Figure dependency: linked figure supplies the rectangle/trapezoid incidence and right angle.
- Auxiliary: no source solution shown; BE is a figure-defined side/height, not an added solution line. Goal: trapezoid area.

### grade_6_sgk_1-L5387 — lines 4965–4965 — `prepared` — G07
- Givens: rectangular room 9 m by 3 m; square tiles have side 30 cm.
- Figure dependency: none; ignore cutting constraints not stated.
- Auxiliary: no solution shown. Goal: number of tiles.

### grade_6_sgk_1-L5391 — lines 4969–4989 — `prepared` — G07
- Givens: yard boundary is a trapezoid with bases 30 m and 42 m and height 24 m; house footprint is a rectangle 15 m by 18 m; seed covers 33 m² per bag.
- Figure dependency: crop shows the house within the trapezoidal yard and the perpendicular height.
- Auxiliary: worked solution subtracts the house rectangle area from the trapezoid area; no new geometric line. Goal: grass area and seed-bag count.

### grade_6_sgk_1-L5413 — lines 4991–5023 — `prepared` — G07
- Givens: rectangular floor length 20 m and width one-quarter of length; square tiles have side 4 dm; total tile purchase cost is 11,875,000 VND.
- Figure dependency: no crop; dimensions and ratio are in text.
- Auxiliary: worked solution derives width from the ratio and compares rectangle/tile areas; no added geometric line. Goal: unit price per tile.

### grade_6_sgk_1-L5451 — lines 5027–5033 — `prepared` — G03,G07
- Givens: three independent constructions: (a) square side 5 cm; (b) rectangle 4 cm by 2 cm; (c) equilateral triangle side 3 cm.
- Figure dependency: none.
- Auxiliary: no solution shown. Goal: draw each specified shape; retain as three distinct subproblems for variant derivation.

### grade_6_sgk_1-L5459 — lines 5035–5041 — `prepared` — G07
- Givens: rhombus MPNQ with diagonals MN=8 cm and PQ=6 cm; part (b) additionally gives side MP=5 cm.
- Figure dependency: linked crop labels the rhombus and its two crossing diagonals.
- Auxiliary: diagonals are explicit givens. No solution shown. Goals: area, then perimeter.

### grade_6_sgk_1-L5467 — lines 5043–5043 — `prepared` — G07
- Givens: rectangular sheet has area 96 cm² and one side 12 cm.
- Figure dependency: none.
- Auxiliary: no solution shown. Goal: perimeter.

### grade_6_sgk_1-L5469 — lines 5045–5050 — `prepared` — G07
- Givens: square garden side 20 m; an internal border path runs around all four sides and has width 2 m; the remaining inner region is cultivated.
- Figure dependency: crop shows the uniform inset border on the top and left; extend the same 2 m width around the whole square as stated.
- Auxiliary: no solution shown. Goal: area remaining for cultivation.

### grade_6_sgk_1-L5476 — lines 5052–5054 — `prepared` — G07
- Givens: rectangular garden length 25 m and width three-fifths of the length; two perpendicular paths, each 1 m wide, cross through the garden and partition four planting rectangles.
- Figure dependency: linked crop determines the cross-shaped path layout.
- Auxiliary: no solution shown. Goal: area used for planting.

### grade_6_sgk_1-L5482 — lines 5058–5060 — `prepared` — G07
- Givens: a square divided by one vertical and one horizontal midline into a 2-by-2 grid of congruent small squares.
- Figure dependency: linked figure is the complete grid.
- Auxiliary: no solution shown. Goal: count all squares of every size.

### grade_6_sgk_1-L5486 — lines 5062–5064 — `prepared` — G03,G07
- Givens: one large equilateral triangle partitioned into four congruent equilateral triangles by its three midsegments; the central small triangle is inverted.
- Figure dependency: linked crop supplies the exact subdivision.
- Auxiliary: subdivision lines are drawn in the given figure, not introduced by a solution. Goal: count equilateral triangles, isosceles trapezoids and rhombi.

### grade_6_sgk_1-L5490 — lines 5066–5072 — `prepared` — G03,G07
- Givens: three independent constructions: equilateral triangle side 5 cm, square side 6 cm, rectangle 4 cm by 3 cm.
- Figure dependency: none.
- Auxiliary: no solution shown. Goal: draw each shape.

### grade_6_sgk_1-L5498 — lines 5074–5076 — `prepared` — G07
- Givens: (a) parallelogram with adjacent side lengths 4 cm and 3 cm; (b) rhombus with side 3 cm.
- Figure dependency: none; angles are free.
- Auxiliary: no solution shown. Goal: draw both quadrilaterals.

### grade_6_sgk_1-L5502 — lines 5078–5078 — `prepared` — G07
- Givens: rectangle with length 6 cm and width 5 cm.
- Figure dependency: none.
- Auxiliary: no solution shown. Goal: perimeter and area.

### grade_6_sgk_1-L5504 — lines 5080–5086 — `prepared` — G07,G08
- Givens: regular hexagon ABCDEF with center O; OA=6 cm and diagonal BF=10.4 cm. Rhombus ABOF is a named subfigure.
- Figure dependency: linked crop shows the hexagon and internal segments through O; exact selected segments should follow that figure.
- Auxiliary: no source solution adding lines. Goal: areas of rhombus ABOF and the full hexagon.

### grade_6_sgk_1-L5512 — lines 5088–5090 — `prepared` — G07
- Givens: orthogonal stepped plot outline; crop labels a 6 m horizontal inset, a 3 m inner vertical, a 7 m bottom, a 5 m right side, and 2 m for both the upper vertical step and short rightward step. The outline closes as an orthogonal polygon.
- Figure dependency: the linked crop is essential; it gives the outline and dimension placement. No named vertices or other marks.
- Auxiliary: no solution shown. Goal: area of the plot.

### grade_6_sgk_1-L5516 — lines 5092–5094 — `prepared` — G07
- Givens: rectangle whose length is twice its width; cut/rearrange without changing area.
- Figure dependency: crop shows the cut/rearrangement suggestion; no numeric dimensions are specified.
- Auxiliary: no source solution shown. Goal: produce a square with equal area.

### grade_6_sgk_1-L5520 — lines 5096–5098 — `prepared` — G07
- Givens: porch is a trapezoid with parallel sides 54 dm and 72 dm and perpendicular height 45 dm; construction cost is 103,000 VND per 9 dm².
- Figure dependency: linked crop labels the two bases and shows the right-angle height.
- Auxiliary: no source solution shown. Goal: total porch cost.

### grade_6_sgk_1-L5610 — lines 5167–5197 — `needs_review` — G14
- Givens: a composite symmetry-identification activity. It asks which pictured letters/objects have an axis of symmetry and asks students to predict axes; the referenced crops contain the candidate shapes and examples.
- Figure dependency: seven linked image assets across multiple subquestions; the silhouettes/glyphs themselves carry the relevant facts. Keep each pictured candidate separate; the text alone does not identify them.
- Auxiliary: no solution adding a geometric line. Goal: classify axis symmetry and state axes. Preserve `needs_review` because this is a multi-part lesson/activity rather than one clean source problem.

### grade_6_sgk_1-L5780 — lines 5308–5310 — `prepared` — G14
- Givens: an isosceles trapezoid, shown without labels or dimensions.
- Figure dependency: linked crop supplies the trapezoid; its symmetry axis is perpendicular to the parallel bases and bisects both, but the axis is not drawn in the crop.
- Auxiliary: no solution shown. Goal: identify/draw the axis of symmetry.

### grade_6_sgk_1-L5784 — lines 5312–5314 — `prepared` — G08,G14
- Givens: regular hexagon; no length or orientation constraints beyond regularity.
- Figure dependency: linked crop shows the hexagon.
- Auxiliary: no solution shown. Goal: give the number of symmetry axes.

### grade_6_sgk_1-L5788 — lines 5316–5328 — `prepared` — G14
- Givens: four independent pictured candidate shapes, labeled a–d in the source; classify axial symmetry.
- Figure dependency: four linked image crops supply the actual shapes; no metric givens.
- Auxiliary: no solution shown. Goal: identify which candidates have an axis of symmetry.

### grade_6_sgk_1-L5802 — lines 5330–5338 — `prepared` — G14
- Givens: a set of pictured candidate shapes, each shown in a linked composite image.
- Figure dependency: the crop supplies each silhouette and its orientation; no dimensions or named vertices are given.
- Auxiliary: no solution shown. Goal: sort candidates into zero, one, or two axes of symmetry.

### grade_6_sgk_1-L5883 — lines 5401–5422 — `needs_review` — G14
- Givens: the text states a segment has a center of symmetry at its midpoint; additional pictured letters and shapes are candidates for central symmetry, with centers to predict/check by a half-turn.
- Figure dependency: five linked image assets cover several separate subquestions; preserve candidate boundaries and marked letterforms from the crops.
- Auxiliary: no solution adding lines. Goal: decide which candidates have a center and locate it. Preserve `needs_review` because the manifest groups multiple lesson/example panels.

### grade_6_sgk_1-L5958 — lines 5468–5476 — `prepared` — G14
- Givens: two incomplete shapes on square grids; O is the required center of symmetry.
- Figure dependency: two linked crops specify the existing partial strokes, grid coordinates and O location.
- Auxiliary: the missing half-turn image is the requested construction, not a source-solution auxiliary. Goal: complete each figure with center O.

### grade_6_sgk_1-L6012 — lines 5516–5525 — `prepared` — G14
- Givens: three pictured candidate shapes, each supplied as a separate crop.
- Figure dependency: all three shapes are image-defined; no lengths or labels are stated.
- Auxiliary: no solution shown. Goal: identify shapes with a center of symmetry.

### grade_6_sgk_1-L6025 — lines 5526–5538 — `prepared` — G14
- Givens: four pictured shapes, each with a marked point O.
- Figure dependency: linked crops determine both each shape and the location of O.
- Auxiliary: no solution shown. Goal: test whether the marked O is a center of symmetry for each shape.

### grade_6_sgk_1-L6039 — lines 5540–5552 — `prepared` — G14
- Givens: four pictured candidate shapes.
- Figure dependency: linked crops specify their outline and relative placement.
- Auxiliary: no solution shown. Goal: identify those with central symmetry and determine their centers.

### grade_6_sgk_1-L6053 — lines 5554–5556 — `prepared` — G14
- Givens: one paper-fold/cut activity illustrated by the linked crop; the text asks for the folding and cutting steps used in the referenced practical example.
- Figure dependency: one crop supplies the intended cut pattern/result; the prose alone is insufficient to specify the final outline.
- Auxiliary: fold/cut marks are procedural and figure-defined; no separate mathematical solution line.

### grade_6_sgk_1-L6057 — line 5558 — `needs_review` — G14
- Givens: paper rectangle 3 cm by 5 cm, folded once horizontally and once vertically, then cut according to referenced pictures; infer the unfolded letter/shape.
- Figure dependency: no image path is attached and the manifest source text contains no cut pictures. The defining cut pattern is missing from this record.
- Auxiliary: unavailable. Goal cannot be made determinate until the source crop is recovered; retain `needs_review`.

### grade_6_sgk_1-L6059 — lines 5560–5566 — `prepared` — G14
- Givens: two incomplete shapes on square grids; O must be the center of symmetry.
- Figure dependency: two linked crops supply the existing strokes, grid and O.
- Auxiliary: the completion strokes are the requested construction, not a source-solution auxiliary. Goal: complete both figures around O.

### grade_6_sgk_1-L6075 — lines 5576–5615 — `prepared` — G14
- Givens: the worked example constructs a five-point star by folding and cutting; the source explains that the complete star has five axes of symmetry and a center of symmetry. Multiple sequential figures show the fold/cut stages and result.
- Figure dependency: nine linked assets span the starting figure, folding states, cutting, and opened result. They are a procedure sequence, not nine independent geometry givens.
- Auxiliary: the fold creases are axes used in the paper construction; no additional proof line is introduced. Goal: reproduce the fold-and-single-cut construction.

### grade_6_sgk_1-L6115 — lines 5616–5631 — `prepared` — G03,G14
- Givens: three pictured objects: an equilateral triangle, a heart, and a kite.
- Figure dependency: each object is in a separate linked crop; only the equilateral-triangle regularity is stated in its caption, while contours of the heart/kite are image-defined.
- Auxiliary: no solution shown. Goal: classify each as having a center and/or an axis of symmetry.

### grade_6_sgk_1-L6135 — lines 5633–5639 — `needs_review` — G14
- Givens: symmetry classification of pictured logos, including a Southeast Asian Games emblem and a UNESCO World Heritage emblem.
- Figure dependency: two linked logo crops are present; the manifest groups them as options b and c, and any preceding option is not represented by a linked crop here.
- Auxiliary: no solution shown. Goal: identify axial and central symmetry. Preserve `needs_review` because one grouped choice may be absent from the image links.

### grade_6_sgk_1-L6147 — lines 5641–5645 — `prepared` — G14
- Givens: two partial shapes and a specified line d, which must become an axis of symmetry.
- Figure dependency: two linked crops supply each partial contour and the line d.
- Auxiliary: completion strokes are the requested construction, not solution-added givens. Goal: complete both shapes with axis d.

### grade_6_sgk_1-L6152 — line 5646 — manifest says `prepared` — G09,G14
- Givens in text: a shape is to be copied on grid paper and completed so that O is its center of symmetry.
- Figure dependency: the text references a figure, but `image_paths` is empty and no figure markup occurs in this source span. The initial partial shape and O are unavailable in the manifest/corpus text slice.
- Auxiliary: unavailable. Goal: underdetermined from retained source data; flag for review despite the current `prepared` decision.

### grade_6_sgk_1-L6154 — lines 5648–5653 — `needs_review` — G14
- Givens: a symmetry-classification question with at least one pictured candidate; text also includes a stray `SOS`/option marker.
- Figure dependency: one linked image is present, but the grouped prompt/options are incomplete or corrupted.
- Auxiliary: no solution shown. Goal: classify axial and central symmetry only after recovering the complete options; retain `needs_review`.

### grade_6_sgk_1-L6161 — lines 5655–5663 — `prepared` — G14
- Givens: starting broken line has four segments, each 1 cm; add another broken line of total length 8 cm so the combined figure has both axial symmetry and central symmetry.
- Figure dependency: crop gives the initial four-segment chain and its orientation; the added chain is open-ended design space constrained by length and symmetries.
- Auxiliary: the added chain is the requested construction, not a source-solution auxiliary. No solved construction is supplied.

### grade_6_sgk_1-L6173 — lines 5667–5676 — `prepared` — G14
- Givens: three shapes a–c shown on square grids; determine every axis each shape has.
- Figure dependency: three linked crops supply grid coordinates and contours.
- Auxiliary: no solution shown. Goal: identify all reflection axes for each figure.

### grade_6_sgk_1-L6184 — lines 5678–5687 — `prepared` — G14
- Givens: three pictured candidate shapes a–c.
- Figure dependency: three linked crops give the outlines; no labels or dimensions are stated.
- Auxiliary: no solution shown. Goal: identify which shape(s) have a center of symmetry.

### grade_6_sgk_1-L6195 — lines 5689–5703 — `prepared` — G14
- Givens: four pictured partial/complete motifs a–d and a line d designated as the symmetry axis for completion.
- Figure dependency: four linked crops supply the starting motifs and line position.
- Auxiliary: added decorations are the requested construction; no source solution lines are given. Goal: complete each motif so line d is an axis.

### grade_6_sgk_1-L6215 — lines 5709–5713 — `prepared` — G14
- Givens: one half-leaf/leaf outline with a specified line d.
- Figure dependency: linked crop gives the partial leaf contour and line position.
- Auxiliary: the reflected half is the requested construction, not an added solution line. Goal: complete and decorate a leaf symmetric about d.

## Source-quality notes

- L1378's rectangle/grid markup needs visual recovery before its subdivisions are trusted.
- L6057 has no linked cut-pattern image, and L6152 has no linked starting figure although the prompt requires one. L6135 may omit an earlier option. These source defects are separate from the six manifest review statuses above.
- L5610 and L5883 combine broad lesson/exercise panels; split subfigures before turning them into independent training sources.
- Image-defined symmetry silhouettes are intentionally not assigned inferred coordinates or lengths in this audit. Each candidate must be transcribed from the cited manifest image paths before authoring a self-contained instruction/target pair.

## Verified figure-asset index

Each path below is copied from the source manifest `image_paths`; corpus existence was checked. `none` means no linked asset was recorded.
- `grade_6_sgk_1-L1378`: none
- `grade_6_sgk_1-L1496`: 6/grade_6_sgk_1/images/44b80d705c285a8ce16d9403de838680aa08c63ead520b195c3dbe1f3cea2cc9.jpg
- `grade_6_sgk_1-L4679`: 6/grade_6_sgk_1/images/725417458e2326e0c79b7928eb5597ddc2ff0458825b1be4acce2c24667cfe7b.jpg
- `grade_6_sgk_1-L4721`: none
- `grade_6_sgk_1-L4723`: none
- `grade_6_sgk_1-L4725`: 6/grade_6_sgk_1/images/0d68e21cf7d1584f49a0c99fab3c012505c42c6d1b2873552049ad610fb28b54.jpg
- `grade_6_sgk_1-L4729`: none
- `grade_6_sgk_1-L4733`: 6/grade_6_sgk_1/images/86ccd455ef31a46bd739d42e647daaa1d528e0cd069a7a5cd9710423844fcb7f.jpg
- `grade_6_sgk_1-L4737`: 6/grade_6_sgk_1/images/722131256b6d48ee1a3dc245b24e716260e681ee704e0cd39427a292e9ac10a5.jpg, 6/grade_6_sgk_1/images/12d07b77a42e78c324539d4db8674a93c2d7cbb4f99a1f1984a078df0e556dba.jpg, 6/grade_6_sgk_1/images/273766f4722c649325a0d571506ca5dc3226df8317ddaa804045e931366fff71.jpg
- `grade_6_sgk_1-L4750`: none
- `grade_6_sgk_1-L5056`: 6/grade_6_sgk_1/images/7ed509baf1951b809d113fd4ec93933bc7d8dcb7680d960f00e1c7f544b6916a.jpg
- `grade_6_sgk_1-L5081`: none
- `grade_6_sgk_1-L5083`: none
- `grade_6_sgk_1-L5085`: none
- `grade_6_sgk_1-L5087`: 6/grade_6_sgk_1/images/b05750e4518d869fbdc77066354ae29152282c46ce2934cceb35f8a4ca47dd5d.jpg
- `grade_6_sgk_1-L5091`: 6/grade_6_sgk_1/images/45f21e0b6d7fe3f8afca75ab828fa3941784c2edba8babf3d805254363694d15.jpg
- `grade_6_sgk_1-L5095`: none
- `grade_6_sgk_1-L5097`: 6/grade_6_sgk_1/images/5d74c8268d0db62635284418359edead729e2550161a7199c0b14c32017642fc.jpg
- `grade_6_sgk_1-L5156`: 6/grade_6_sgk_1/images/d693d5bf0a7173e19725b3f76846487f78e4cd11cd6576235f066aaecd16fe0d.jpg
- `grade_6_sgk_1-L5176`: 6/grade_6_sgk_1/images/d82707cae456d2f6be1089dd72be7400eaab64c2ea9f89d49977051d6bff49a7.jpg
- `grade_6_sgk_1-L5192`: 6/grade_6_sgk_1/images/d947871f0c884d21078414bf64d4ab4d6b607c4868992914e2fca487dd1a5c9c.jpg, 6/grade_6_sgk_1/images/c230fd0e2ae1fa38ef7a4e97047114f4e793663851fb6163a3970ecc3b3800d1.jpg
- `grade_6_sgk_1-L5229`: 6/grade_6_sgk_1/images/e6d696ecffbe58b3938f9f74702b8d050180918317466a8b1d6c6ef5643ded54.jpg
- `grade_6_sgk_1-L5239`: 6/grade_6_sgk_1/images/1c959a3b01332ff50be9cceb29d68f66910a0fff853a8f422d9f61e9c0264684.jpg
- `grade_6_sgk_1-L5293`: 6/grade_6_sgk_1/images/87f4e66af77caae4da1044b0fcee8ae2dde22e708122a6ba822c2b1d09198c9f.jpg
- `grade_6_sgk_1-L5307`: 6/grade_6_sgk_1/images/5fdef440d728749a4d2152b1cd87cca3a57de8fab7e5c3a6e3e9a591a3c3536a.jpg
- `grade_6_sgk_1-L5339`: 6/grade_6_sgk_1/images/8cc41d273a7df7beb84d39eb342f7fb766eae43c1d70abe28c74c353455d322e.jpg
- `grade_6_sgk_1-L5353`: 6/grade_6_sgk_1/images/70117359be6c6050fd18b082e741938f2d97ce15ba794aa9e74e2fcde2ce83bc.jpg
- `grade_6_sgk_1-L5362`: none
- `grade_6_sgk_1-L5364`: none
- `grade_6_sgk_1-L5367`: 6/grade_6_sgk_1/images/d008238e364239f1e138d4b019d1802327661485af527cae4fb52d2982fc7a78.jpg
- `grade_6_sgk_1-L5371`: 6/grade_6_sgk_1/images/280f1531fdbca9a1c561d6528fd4351cca9ac25b84c7a7b3dd2b264e09d6ca1a.jpg
- `grade_6_sgk_1-L5379`: 6/grade_6_sgk_1/images/72c021180d8474623f0662f97395ace3220ff34b281bee0016a49b117b198097.jpg
- `grade_6_sgk_1-L5383`: 6/grade_6_sgk_1/images/6e147dd95de6082262ff820588eab5f267f3f86fae56c37dcf643fa9c54ecd89.jpg
- `grade_6_sgk_1-L5387`: none
- `grade_6_sgk_1-L5391`: 6/grade_6_sgk_1/images/0c56c4d7ccab6fc708e8b763de9d158168ecee791f53b257effdaa9a2994c3f6.jpg
- `grade_6_sgk_1-L5413`: none
- `grade_6_sgk_1-L5451`: none
- `grade_6_sgk_1-L5459`: 6/grade_6_sgk_1/images/f95e880d22b4959810e4bd193cd6ea43d3f49c0d63f6fc462b39b099174f72ee.jpg
- `grade_6_sgk_1-L5467`: none
- `grade_6_sgk_1-L5469`: 6/grade_6_sgk_1/images/3c3d5429167b485ac8b7731879c93c46cf620bf022febf2c4d9fcd33266e2880.jpg
- `grade_6_sgk_1-L5476`: 6/grade_6_sgk_1/images/a8f21cc2da8396bd0d4c50618063489672a9c42cf2401025f351c472e66a3301.jpg
- `grade_6_sgk_1-L5482`: 6/grade_6_sgk_1/images/e1794672308fd4387069e938a1ac2c43a4d00a37585f227cc78d1cc18f7a6013.jpg
- `grade_6_sgk_1-L5486`: 6/grade_6_sgk_1/images/8a2e444c8a57ad52fcd941f28af1dda280e71b0ad0b107b4815f9d14186bdb58.jpg
- `grade_6_sgk_1-L5490`: none
- `grade_6_sgk_1-L5498`: none
- `grade_6_sgk_1-L5502`: none
- `grade_6_sgk_1-L5504`: 6/grade_6_sgk_1/images/7b785441d261adecb61a1e160085f107a7d39d373071bb6688bdb3a21dd0168a.jpg
- `grade_6_sgk_1-L5512`: 6/grade_6_sgk_1/images/814bc8316a38a6c6a07e8a377e2c3812aa73102b4f772a46adf837cf3ee42780.jpg
- `grade_6_sgk_1-L5516`: 6/grade_6_sgk_1/images/c31fcabdfc63c996339f6926862edcfbe573ed8ebadcde029ff877b999cac477.jpg
- `grade_6_sgk_1-L5520`: 6/grade_6_sgk_1/images/1760ed7e21a663dd7d2fb8fecedc5d67e5c0c37f7ea6b88a167f7aaced1ac0ea.jpg
- `grade_6_sgk_1-L5610`: 6/grade_6_sgk_1/images/1659e923efec5f0650a17504932b920a209ee0f6a3b37489492ce78895f097a2.jpg, 6/grade_6_sgk_1/images/0355c80b7a39ffc052b3c6cf7e3b3c8303bce43b18a57cf41a8c49caf6a33f82.jpg, 6/grade_6_sgk_1/images/c24772175fc420e07fe0dde6893a998b355e87c4d71ed7ca25c47cbd499984c6.jpg, 6/grade_6_sgk_1/images/bb7be8eee286c5c92a725b71292a9387af0dc0a1c7b058fc380e5b09cfa7567c.jpg, 6/grade_6_sgk_1/images/aa9eaa726731ff92ab5ee8d5820f1828f2a4ebf3e944053263c077905a8187bc.jpg, 6/grade_6_sgk_1/images/e5333103282a8a6a7e0d6a7028dae616f430f33c9d5e08f308a402024a9ddc36.jpg, 6/grade_6_sgk_1/images/159aa2df1b0b036a17fe7e1e22745a24655abb3992c9b831cab4c29bbf25a313.jpg
- `grade_6_sgk_1-L5780`: 6/grade_6_sgk_1/images/a7e768ac94aaf8f7f2defed3116230d916bbf15bc107243b44e63bf0edb78819.jpg
- `grade_6_sgk_1-L5784`: 6/grade_6_sgk_1/images/5ac948560408d5e4e1ab83daf02fb47f3f26af388394e98fbe47c22864133aec.jpg
- `grade_6_sgk_1-L5788`: 6/grade_6_sgk_1/images/04cb71bec022d122e7c991ec3b2f325fd838810e498e6146b5e5d6b6360c5529.jpg, 6/grade_6_sgk_1/images/c42c7d29c3734682d6ef7c3d345178cb70fb937c022ccb889cfe24c28110a0ab.jpg, 6/grade_6_sgk_1/images/05243ccc013be59cf1612f81a64fea2d94da4b1e7aa2580119975a53ae45dfa0.jpg, 6/grade_6_sgk_1/images/59a62387933f5636230d3d26799d8831f85586818a1ac3b6b7fb16251af24b68.jpg
- `grade_6_sgk_1-L5802`: 6/grade_6_sgk_1/images/351261c5ba892ea23a796bea1b86bbf65f7e4380e586cee04bbd7025e75ef386.jpg
- `grade_6_sgk_1-L5883`: 6/grade_6_sgk_1/images/ec9df5f344377cc2a98d64bf5c2bcf23bb3b16bba1d4c64a246b2c3e2330b81b.jpg, 6/grade_6_sgk_1/images/1ebe777cb173d205d5f09a40ec4a8a4b244fa577579309c071af929c38b5074b.jpg, 6/grade_6_sgk_1/images/f0f6e51fae7271ae48c34feeb49ebde9786868c9f17856e037b87a68d0340d5a.jpg, 6/grade_6_sgk_1/images/80b41c5331240c776ad052aeed9c8eb6e5106bcdea1e4996a65a26fa4797dfde.jpg, 6/grade_6_sgk_1/images/58f661d1d926a41b56009c255c06f1d035c90c544533a65592a0697c448e8505.jpg
- `grade_6_sgk_1-L5958`: 6/grade_6_sgk_1/images/5fd1967c91ea76f89b9f5dbde1b5620b494aff60577e6c9a0e0d897e3eec3c08.jpg, 6/grade_6_sgk_1/images/441e2146754a741e1a5d6bb8348792e69ec2e766291c823061dc1d2fedf76e4b.jpg
- `grade_6_sgk_1-L6012`: 6/grade_6_sgk_1/images/ce3552a6df3b49f01177c1f5b45cf1fb2a835870f56e7cb3fb9d8caeb3bfd1f8.jpg, 6/grade_6_sgk_1/images/453d332190b2fab6b59863100c2e4feffe8a66c9d2c2340f35ad4b687154ccfd.jpg, 6/grade_6_sgk_1/images/b35d021b791ce485e8db66300a82925fd34f71fe4faa0eed231f7a898e7cfa19.jpg
- `grade_6_sgk_1-L6025`: 6/grade_6_sgk_1/images/b8709f05fc344ad5baae5d4ab9a878f1c26bd95450731e04096c60c8e4015b0e.jpg, 6/grade_6_sgk_1/images/d4f4a4ef39a6a1fc9b5082cedff14501dcdd06af958713134918c789e19b5b72.jpg, 6/grade_6_sgk_1/images/a75d2f4b0610eba64f4bea1d1d55c43003cb3e245ec9efce1911f33453eb630f.jpg, 6/grade_6_sgk_1/images/645451c2db0d91d1e2663e678799f88a4b0bdb4c4797be2cd325ce5e01d0f2b7.jpg
- `grade_6_sgk_1-L6039`: 6/grade_6_sgk_1/images/0dfe316ff71027ca5c6513587e5e9c68275a15889daef2bf01238713aa4ea31f.jpg, 6/grade_6_sgk_1/images/262602eb0fdfed5680c265481b7bb16adaa2378d8563fdeee006025c18997869.jpg, 6/grade_6_sgk_1/images/71d79783d724be78e9a199f1a481a14296feea01fffb16225664c5613136c5f0.jpg, 6/grade_6_sgk_1/images/4f01cc7ae0c41cc2626967db0fcab8f213ee078025cab1c0ddcd8d3ae76443af.jpg
- `grade_6_sgk_1-L6053`: 6/grade_6_sgk_1/images/097ea8d7fae5ccbd1844c1e9c97040e6c16cd7f14671d2cde0fc0936bb7f2d7c.jpg
- `grade_6_sgk_1-L6057`: none
- `grade_6_sgk_1-L6059`: 6/grade_6_sgk_1/images/df4f08fbc8059e0e72e25a33d109c70425aa4bcd2d64bada01a1e67b91756c32.jpg, 6/grade_6_sgk_1/images/3b2eb0ebb0f34c41c8b197e8dde6a196eddeb3c1129b264bf121bb5f9aa3ab5d.jpg
- `grade_6_sgk_1-L6075`: 6/grade_6_sgk_1/images/c9aab0fd9b424e9d691cc914d96b1206dbceb1b915ccbeba157b0a10b7e4a1df.jpg, 6/grade_6_sgk_1/images/604d036d0577d4c5b05137350707d0cd5d82fc5f721b866d6a3c927321e5296f.jpg, 6/grade_6_sgk_1/images/1cda0b8fa218497f2bd0202a19ab7012233a7992ce15198d59c4474b1c3a2e04.jpg, 6/grade_6_sgk_1/images/1acd7c071bf48beff68ccac88bb73fe2c01a5c10be6ee19b34b634d1fb4bbfb5.jpg, 6/grade_6_sgk_1/images/375f7e0b486c5e388f04040ebf4fd9e309ca862d24ba605cdd6468e535b108e1.jpg, 6/grade_6_sgk_1/images/7833d9fb8bddc23443cbb1ef1bb742b15fce44b4afdb76f26e199c0cfd8311a3.jpg, 6/grade_6_sgk_1/images/594f36539ba4ee6879b8c9819f266f18754aba5165b4109060dae37e586e3e37.jpg, 6/grade_6_sgk_1/images/d0e224e8cb0ff120a31b896e4370c7f6067b382133942e9d93c8cb89a02be971.jpg, 6/grade_6_sgk_1/images/0181c82362bd24027ce3ee407cb49c78d151c3123dac647a63a2c805ff49fe42.jpg
- `grade_6_sgk_1-L6115`: 6/grade_6_sgk_1/images/dc7798ad6f4cef78cffca99bd3802fa7260cf3ecaa13b19157f84234eea90e9e.jpg, 6/grade_6_sgk_1/images/b1bc0b705ecbca2b3a9d7cb6d0e002dbf8056e62e1f5b0f406a07083a4d653c5.jpg, 6/grade_6_sgk_1/images/9607576d9f2683361b3a3166c1faff27e50d23c8c847ff51ae483c2e1cd23405.jpg
- `grade_6_sgk_1-L6135`: 6/grade_6_sgk_1/images/0d1b69b5d3d7ea2aa2655db4b28e48c77812acb2fa05f62ead05171b0aca3d55.jpg, 6/grade_6_sgk_1/images/15845ac1fe0d435b6bedd83b6350fb91dacbc9a19429fbc48d85b36f29e7debf.jpg
- `grade_6_sgk_1-L6147`: 6/grade_6_sgk_1/images/18de8789c9c9b3d66f97b8a99e811bf0d248178a07f2182475d7fbd13e40b407.jpg, 6/grade_6_sgk_1/images/a57cab8902f8bc97ddfe77b13a14c802ae019d9f1164dde7c1926a5504ca7abd.jpg
- `grade_6_sgk_1-L6152`: none
- `grade_6_sgk_1-L6154`: 6/grade_6_sgk_1/images/b9efbb2ae3337b00af83c7a20a17809907dc28aa11c781b9e98fa15ee985c97e.jpg
- `grade_6_sgk_1-L6161`: 6/grade_6_sgk_1/images/a03ba615ddfd3cc594e52f73dd969738034595a1a627c681baa0c3b1807116fe.jpg
- `grade_6_sgk_1-L6173`: 6/grade_6_sgk_1/images/d4936d4c259e74fd188365be4ac2dcf0d90a1504e4c15c41d7dc60df5d324617.jpg, 6/grade_6_sgk_1/images/e032adf80307e63cb9e470f6b930bc94d81cc90fa25ec723d7c92ca9f81e7dbd.jpg, 6/grade_6_sgk_1/images/4df13e34bb646a6be9a2a8b7aafe3fd0ca6c3d07ce3f2c30062b7547a65b2132.jpg
- `grade_6_sgk_1-L6184`: 6/grade_6_sgk_1/images/7cdf96594920c51ffa94eaa3d48713d58c722a03bb280164c9b4fe7be2febc7c.jpg, 6/grade_6_sgk_1/images/f915e49dfbe7dab0be84f9e06990f583924022818b1d76842aaafb72a18ca826.jpg, 6/grade_6_sgk_1/images/0c6c22293df3caa7081f2991dbee0f4812d632555acd2797ec273b9e2b4aed1b.jpg
- `grade_6_sgk_1-L6195`: 6/grade_6_sgk_1/images/2a184f45d39bc7e3e774f6317e46deb738acf740353eeb93e87cacbc5483ff8b.jpg, 6/grade_6_sgk_1/images/ed91e5233478f43281cd088ece6deb1a6e7e1de870ef0f80cc36542940e337a2.jpg, 6/grade_6_sgk_1/images/0b9b40f0e74fc45793f8a9df1ec97c35fe42dfbc447468acfc97e24b71399432.jpg, 6/grade_6_sgk_1/images/348dc3c45a6bdb9ee9c63589433b684c6fe1610ee23586b3ad0e34a0324e26ad.jpg
- `grade_6_sgk_1-L6215`: 6/grade_6_sgk_1/images/081614f86120346dd9b9ceb68f9bd2aa7307ee75068910a4baba9c09be850eaf.jpg
