# Grade 9 SGK 1: mathematical-givens inventory

Audit of docs/dataset-selection/grade-9.problems.jsonl against 9/grade_9_sgk_1/book.final.md. Exact source_text range verification across the grade-9 manifest: 275 rows matched, 0 mismatches.

## Counts and filtering

- SGK1 manifest rows: 123.
- Excluded as algebra-focused: 11 — grade_9_sgk_1-L209, -L252, -L335, -L343, -L658, -L671, -L682, -L731, -L940, -L971, -L1188. The first nine are equation/system/graph tasks (including mislabeled G13); L971 is circular-motion rates solved as a linear system; L1188 is a garden-area equation.
- Genuine geometry rows inventoried: 112 (110 manifest-prepared, 2 needs_review).
- Retain genuine geometric G13: L3646, coordinate points relative to a circle.
- needs_review: L4017 (prior practical/sector diagram absent from row); L4539 (woven-product figure absent/unlinked). L3298 is marked prepared but H4.23 and its measurements are missing from this record, so it also needs source recovery before authoring.

## Legend

G = explicit givens; F = figure/crop availability or unresolved visual dependency; Aux = source-procedure auxiliary objects, distinct from the conclusion; Goal = requested conclusion, not an initial given. “No linked crop” describes the selection manifest; some rows have an existing image embedded in Markdown, noted below.

## Row-by-row inventory

### Source lines 1999–3390

- grade_9_sgk_1-L2029 [1999–1999] — G: circular planting-bed area ≈2 m². F: no figure; complete. Aux: none. Goal: estimate diameter.
- grade_9_sgk_1-L2208 [2168–2172] — G: rectangular TV screen, side ratio 4:3; part b diagonal 40 in. F: none; complete. Aux: diagonal d and width x are variables. Goal: formula and dimensions.
- grade_9_sgk_1-L2656 [2594–2595] — G: cube-shaped box, volume 730 dm³. F: none; complete. Aux: none. Goal: estimate edge length.
- grade_9_sgk_1-L2688 [2626–2642] — G: open-top cube box, volume 216 dm³; seam area negligible. F: crop linked, not needed for facts. Aux: solution derives five square faces from open-top cube. Goal: sheet area.
- grade_9_sgk_1-L2742 [2680–2684] — G: circle area 4 m². F: none; complete. Aux: none. Goal: diameter rounded to 0.01 m.
- grade_9_sgk_1-L2865 [2797–2818] — G: ΔABC right at A; AB=3 cm, AC=4 cm; α=∠B. F: H4.6 linked. Aux: none; solution-derived BC=5 is not a given. Goal: trig ratios.
- grade_9_sgk_1-L2892 [2822–2824] — G: ΔABC right at A; AB=5 cm, AC=12 cm. F: no crop; complete. Aux: none. Goal: trig ratios at B.
- grade_9_sgk_1-L2928 [2856–2870] — G: ΔABC right at A; ∠C=30°; BC=a. F: H4.8 linked. Aux: none. Goal: AB, AC in terms of a.
- grade_9_sgk_1-L2944 [2872–2874] — G: ΔABC right at A; ∠C=45°; AB=c. F: none; complete. Aux: none. Goal: BC, AC in terms of c.
- grade_9_sgk_1-L3070 [2984–2986] — G: ΔABC right at A; case a AB=8 cm, BC=17 cm; case b AC=0.9 cm, AB=1.2 cm. F: none; complete. Aux: none. Goal: trig ratios at B,C.
- grade_9_sgk_1-L3074 [2988] — G: right triangle; acute angle 60°; adjacent leg 3 cm. F: none; complete. Aux: none. Goal: opposite leg.
- grade_9_sgk_1-L3076 [2990–2991] — G: right triangle; acute angle 30°; opposite leg 5 cm. F: none; complete. Aux: none. Goal: hypotenuse.
- grade_9_sgk_1-L3079 [2993] — G: rectangle side lengths 3 and √3. F: none; complete. Aux: diagonal. Goal: angle between diagonal and shorter side.
- grade_9_sgk_1-L3149 [3061–3078] — G: airplane speed 500 km/h; path angle 30° above horizontal; time 1.2 min. F: H4.13 linked; text contains facts. Aux: solution models path AB, vertical altitude BH, right ΔABH. Goal: BH.
- grade_9_sgk_1-L3168 [3080–3090] — G: (1) ladder length 3 m, safe angle 65° to ground, wall perpendicular to ground; (2) river width ≈250 m, boat path ≈320 m, drift angle α queried. F: H4.14/H4.15 linked for incidence. Aux: right-triangle models. Goal: ladder-foot distance and α.
- grade_9_sgk_1-L3201 [3113–3126] — G: sunlight-ground angle ≈34°; tower shadow 8.6 m. F: H4.17 linked. Aux: upright tower and horizontal shadow make right triangle. Goal: tower height.
- grade_9_sgk_1-L3216 [3128–3133] — G: tree shadow 25 m; sunlight-ground angle 40°. F: H4.18 linked. Aux: vertical tree and horizontal ground make right triangle. Goal: height.
- grade_9_sgk_1-L3225 [3137–3147] — G: ΔABC right at A; AB=5, AC=8. F: H4.19 linked. Aux: none. Goal: BC and angles; computed values are conclusions.
- grade_9_sgk_1-L3237 [3149–3151] — G: right ΔABC; AB=4, hypotenuse BC=8. F: none; complete. Aux: none. Goal: AC, B,C.
- grade_9_sgk_1-L3241 [3153–3169] — G: ΔABC right at A; AB=3; ∠B=42°. F: H4.20 linked. Aux: none. Goal: ∠C, AC, BC.
- grade_9_sgk_1-L3277 [3185–3187] — G: ΔABC right at A; BC=9; ∠C=53°. F: no linked crop; text complete. Aux: none. Goal: solve triangle.
- grade_9_sgk_1-L3287 [3195–3196] — G: ΔABC right at A; a=BC hypotenuse, b=AC, c=AB; cases (a=21,b=18), (b=10,∠C=30°), (c=5,b=3). F: none; complete. Aux: none. Goal: solve each case.
- grade_9_sgk_1-L3290 [3198–3201] — G: H4.22 dump-bed right-triangle diagram: ramp/body length 4 m; ground segment 5 m; right angle at brace/body junction; α between ramp and horizontal ground. F: linked crop required and confirms labels/angle. Aux: none. Goal: α.
- grade_9_sgk_1-L3298 [3206] — G: asks roof tilt α and width AB only. F: unresolved; H4.23 is referenced but absent, image_paths empty, no measurements/configuration in text. Aux: none. Goal: α, AB; recover crop first.
- grade_9_sgk_1-L3300 [3208] — G: rhombus; diagonals 2√3 and 2. F: no crop; shape and values textual. Aux: diagonals; perpendicular/bisecting relations follow from rhombus properties. Goal: angles.
- grade_9_sgk_1-L3302 [3210–3212] — G: trapezoid ABCD, AD∥BC, AD=16 cm, BC=4 cm, ∠A=∠B=∠ACD=90°. F: no linked crop; setup textual. Aux: subpart constructs altitude CE in ΔACD; E is its foot on AD. Goal: angle equalities, AC relation/length, ∠D.
- grade_9_sgk_1-L3306 [3214–3217] — G: person A; flat ground mirror B; AB=1.2 m; upright tree base C; BC=4.8 m; B between A,C; eye height 1.65 m. F: H4.24 linked for sightline. Aux: sightline via mirror to tree top/reflected-ray geometry. Goal: tree height.
- grade_9_sgk_1-L3313 [3221–3235] — G: ΔABC right at A; AB=5 cm, AC=12 cm. F: crop linked. Aux: none. Goal: trig ratios.
- grade_9_sgk_1-L3329 [3237–3265] — G: unfinished right trapezoid ABCD, right at A,D; AB=1 m, CD=4 m, AD=6 m; α between BC and ground AD. F: H4.26 linked. Aux: solution constructs I=AD∩BC and BE∥AD meeting CD at E, then right ΔBEC. Goal: α, BC.
- grade_9_sgk_1-L3361 [3269] — G: rectangular book width 17 cm, length 24 cm; α between diagonal and 17 cm side. F: none; complete. Aux: diagonal. Goal: sin α, cos α, α.
- grade_9_sgk_1-L3363 [3271–3273] — G: ΔABC; H foot of altitude AH strictly between B,C; HB=3 cm, HC=6 cm, ∠HAC=60°. F: none; complete. Aux: AH⊥BC from altitude definition. Goal: sides and angles.
- grade_9_sgk_1-L3367 [3275–3277] — G: H4.27 river diagram: parallel banks; bank baseline 50 m; diagonal sightline makes 40° with bank (40° marked at both ends in crop); width d perpendicular to banks. F: linked crop required for baseline/angle. Aux: perpendicular width. Goal: d.
- grade_9_sgk_1-L3371 [3279–3294] — G: four H4.28 cases: (a) right triangle, base 3, angle 40°; (b) rectangle side 7, diagonal 10, lower-right angle queried; (c) right triangle legs 5,7, acute angle queried; (d) α=35° slanted line over baseline, slanted intervals 3 and 2, vertical heights marked ?. F: all four crops linked and required. Aux: right triangles/perpendiculars as drawn. Goal: question-mark values.
- grade_9_sgk_1-L3388 [3296–3299] — G: lake-side ΔACB, CA=90 m, CB=150 m, included ∠ACB=120°. F: H4.29 linked; text gives measurements. Aux: none. Goal: AB.
- grade_9_sgk_1-L3393 [3301–3304] — G: dam trapezoid section; top AB=3 m; tan D=1.25, tan C=1.5; height 3.5 m. F: H4.30 confirms AB∥DC and perpendicular height from A falls between bases. Aux: altitude from A to DC and its foot, as in figure. Goal: CD, AD, BC.
- grade_9_sgk_1-L3398 [3306–3311] — G: submarine starts at sea surface; straight path 21° to surface; case a traveled 200 m; case b speed 9 km/h and target depth 200 m. F: H4.31 linked. Aux: vertical-depth/horizontal-surface triangle. Goal: depth and time.
- grade_9_sgk_1-L3409 [3317–3324] — G: H4.32 right 3-4-5 triangle; α adjacent leg 3 and hypotenuse 5. F: linked crop required to map angle/sides. Aux: none. Goal: cos α.
- grade_9_sgk_1-L3418 [3326–3332] — G: ΔMNP right at M; ∠MNP queried; no measurements. F: H4.33 linked. Aux: none. Goal: identify sine ratio.
- grade_9_sgk_1-L3426 [3334–3341] — G: ΔABC right at A; tan B queried; no measurements. F: H4.34 linked. Aux: none. Goal: identify tangent ratio.
- grade_9_sgk_1-L3447 [3355] — G: right triangles with larger acute angle twice smaller. F: none; complete. Aux: none. Goal: similarity; sin/cos of larger acute angle.
- grade_9_sgk_1-L3449 [3357–3363] — G: isosceles tent model; base 4.4 m, perpendicular height 1.8 m; α between roof slope and ground. F: H4.35 confirms equal slopes/midpoint altitude. Aux: altitude bisects base by isosceles-triangle property. Goal: α.
- grade_9_sgk_1-L3457 [3365–3368] — G: broken-tree base, break point, tip form right triangle; fallen segment makes 20° with ground; horizontal root-tip span 5 m. F: H4.36 linked; text complete. Aux: vertical trunk and ground right angle. Goal: original height.
- grade_9_sgk_1-L3462 [3370–3377] — G: ΔABC right at A; ∠B=α. F: crop linked. Aux: Pythagorean proof introduces side labels/ratio expressions, no new geometric object. Goal: sin/cos definitions and identity.
- grade_9_sgk_1-L3471 [3379–3390] — G: at solstice noon Sun is vertical at Syene; Alexandria 800 km from Syene; tower height 25 m, shadow 3.1 m; source labels O Earth center, S Syene, A Alexandria, H tower top, shadow AB. F: H4.38 linked with labels. Aux: parallel sun rays/central-angle transfer in procedure. Goal: Earth circumference.

### Source lines 3451–4041

- grade_9_sgk_1-L3547 [3451–3462] — G: O midpoint of AB; asks whether (O;OA) contains B. F: H5.2 linked. Aux: none. Goal: B∈(O;OA); AB being diameter is a consequence.
- grade_9_sgk_1-L3560 [3464–3466] — G: ΔABC right at A. F: no linked crop; complete. Aux: circle with diameter BC is requested construction. Goal: A lies on it.
- grade_9_sgk_1-L3619 [3519–3534] — G: M lies on circle (O) with diameter AB. F: H5.5 linked. Aux: requested N reflection of M in O and P reflection across AB; procedure locates N on OM and P on perpendicular through M. Goal: construct N,P; no additional result assumed.
- grade_9_sgk_1-L3636 [3536–3538] — G: circle (O), A,B∈(O); d is perpendicular bisector of chord AB. F: no linked crop; complete. Aux: none. Goal: d is an axis.
- grade_9_sgk_1-L3646 [3546] — G: Oxy; M=(0,2), N=(0,−3), P=(2,−1); circle center O radius √5. F: no crop; coordinates complete. Aux: plotting only. Goal: classify points inside/on/outside. Genuine geometry G13.
- grade_9_sgk_1-L3648 [3548] — G: ΔABC right at A; AB=3 cm, AC=4 cm. F: no linked crop; complete. Aux: circumcircle requested. Goal: concyclicity and radius.
- grade_9_sgk_1-L3650 [3550–3556] — G: circle (O); d through O; A on circle, A∉d; B reflection of A over d; C,D reflections of A,B respectively over O. F: no linked crop; complete. Aux: reflected points are input definitions. Goal: circle membership, ABCD rectangle, C/D symmetric over d.
- grade_9_sgk_1-L3658 [3558–3562] — G: square ABCD; E intersection of diagonals; side=3 cm in part b. F: no crop; complete. Aux: circumcircle requested. Goal: center/axes and radius.
- grade_9_sgk_1-L3713 [3611–3622] — G: convex quadrilateral ABCD; ∠BAC=90°, ∠BDC=90°. F: H5.8 linked. Aux: solution sets O midpoint BC and uses circle with diameter BC. Goal: four concyclic; AD<BC.
- grade_9_sgk_1-L3726 [3624–3626] — G: circle with diameter BC; A on it, A≠B,C. F: no crop; complete. Aux: none. Goal: BC<AB+AC<2BC.
- grade_9_sgk_1-L3749 [3647–3667] — G: A,B,C∈(O), as H5.10. F: H5.10 linked; needed for point order/minor-major arc identity; no measures. Aux: none. Goal: enumerate central angles/arcs.
- grade_9_sgk_1-L3803 [3697–3716] — G: ABC right-isosceles at A. F: H5.11 linked; needed to see pictured circle through vertices and locate O; text states only triangle facts. Aux: midpoint/median AO used as altitude; O/circle are diagram-defined. Goal: arc measures.
- grade_9_sgk_1-L3824 [3718–3721] — G: C∈(O); perpendicular bisector of OC meets (O) at A,B. F: no crop; intersection orientation free up to symmetry. Aux: none. Goal: arcs ACB, ABC.
- grade_9_sgk_1-L3831 [3725–3726] — G: semicircle with diameter AB; arbitrary M on it. F: no crop; complete. Aux: none. Goal: distance bound.
- grade_9_sgk_1-L3834 [3728–3731] — G: circle (O;5 cm); chord AB=6 cm; central angle subtending arc AB is 2α. F: no crop; minor/major branch unspecified, making angle/arc portrayal ambiguous. Aux: perpendicular from O to AB/radii in solution. Goal: distance O-to-AB; tan α.
- grade_9_sgk_1-L3839 [3733] — G: center O; dist(O,line AB)=3 cm; minor arc AB=100°. F: no crop; complete. Aux: perpendicular from O to AB in solution. Goal: radius.
- grade_9_sgk_1-L3841 [3735–3740] — G: clock-hand tips trace circles; time interval 36 minutes. F: H5.12 embedded in Markdown and exists, though image_paths empty; crop is clock face. Aux: none. Goal: swept-arc measures.
- grade_9_sgk_1-L3892 [3786–3817] — G: A,B on (O;3 cm); ∠AOB=120°. F: H5.13 linked; full measurements and minor/major branch are clear. Aux: none. Goal: arc measures and lengths.
- grade_9_sgk_1-L3925 [3819–3821] — G: arc subtends central angle 40°; circle radius 9 cm. F: no crop; endpoint labels unnecessary. Aux: none. Goal: arc length.
- grade_9_sgk_1-L3985 [3879–3887] — G: concentric circles radii 3 m,5 m. F: no crop. Aux: annulus is region between circles. Goal: area.
- grade_9_sgk_1-L3995 [3889–3899] — G: sector radius 5 cm; corresponding arc length 4π cm. F: no crop. Aux: none. Goal: sector area.
- grade_9_sgk_1-L4017 [3911–3913], needs_review — G: sector from preceding Thực hành; radius 4 cm. F: missing dependency: prior practical's angle/diagram is outside this span and not linked; sector angle/branch unavailable. Aux: none. Goal: area; recover prior practical.
- grade_9_sgk_1-L4030 [3924–3928] — G: circle (O;4 cm); A,B,C on it; ΔABC isosceles at A; minor arc BC=70°. F: no crop; complete. Aux: none. Goal: equality of minor arcs and lengths.
- grade_9_sgk_1-L4036 [3930] — G: sector radius 4 cm, arc 36°. F: no crop; complete. Aux: none. Goal: area.
- grade_9_sgk_1-L4038 [3932] — G: concentric circles radii 6 cm,4 cm. F: no crop. Aux: annulus. Goal: area.
- grade_9_sgk_1-L4040 [3934–3939] — G: circular pizzas; first diameter 16 cm split into 6 equal sectors; second diameter 18 cm split into 8 equal sectors. F: H5.18 crops embedded in Markdown and exist though image_paths empty; text has values. Aux: equal sectors are defined. Goal: compare sector areas.
- grade_9_sgk_1-L4047 [3941–3944] — G: unfolded fan is semicircle radius 2.2 dm; folded paper length ≈1.6 dm. F: H5.19 linked, needed to interpret radial paper strip/inner boundary. Aux: inner concentric semicircle radius 2.2−1.6=0.6 dm is derived. Goal: paper area.
- grade_9_sgk_1-L4054 [3948–3983] — G: acute isosceles ΔABC at A; BH,CK are altitudes from B,C; part c adds ∠BAC=40°. F: H5.20 linked; text complete. Aux: solution adds O midpoint BC and circle diameter BC; circle-through-H/K is part-a goal, not premise. Goal: H,K on circle; small arcs BH=CK; measure small arc KH.
- grade_9_sgk_1-L4091 [3985–4000] — G: minor arc=90°, circle radius R; segment bounded by arc and chord. F: H5.21 linked and shows shaded minor segment. Aux: solution introduces sector and ΔOAB for area subtraction. Goal: segment-area formula.
- grade_9_sgk_1-L4110 [4004] — G: chord AB not through O on (O); A′,B′ reflections of A,B through O. F: no crop; complete. Aux: reflections are input definitions. Goal: whether perpendicular bisector A′B′ is an axis.
- grade_9_sgk_1-L4112 [4006–4010] — G: ΔABC is not right; H,K are perpendicular feet from B,C to AC,AB. F: no linked crop; foot positions on sides vs extensions unspecified; layout ambiguity. Aux: circle with diameter BC is requested in part a, not a premise. Goal: circle passes through H,K; KH<BC.
- grade_9_sgk_1-L4118 [4012–4017] — G: circular waterwheel; waterline chord AB=4 m; lowest circle point C; CH=0.5 m. F: H5.22b linked and inspected; H is foot of perpendicular from O to AB (right-angle mark). Aux: OH perpendicular; chord midpoint/equidistance follows from chord theorem. Goal: radius.
- grade_9_sgk_1-L4129 [4019–4027] — G: circle (O;5 cm); desired chord AB has distance from O=2.5 cm. F: no crop; chord orientation free up to rotation. Aux: perpendicular from O to AB and radii OA,OB in construction. Goal: chord length, minor-arc measure/length, sector area.
- grade_9_sgk_1-L4139 [4029–4032] — G: chainwheel radius 15 cm; sprocket radius 4 cm; bicycle-wheel diameter 65 cm; one crank revolution. F: H5.23 embedded in Markdown and exists but image_paths empty; diagram needed for gear/linkage orientation; text names chain and gears. Aux: chain/gear relation is mechanism, not a source-defined Euclidean center spacing; do not invent placement. Goal: travel distance.
- grade_9_sgk_1-L4144 [4034–4041] — G: equilateral ΔABC, AB=2√3 cm; semicircle diameter BC intersects AB,AC at D,E other than B,C. F: H5.24 linked; fixes semicircle side/point order. Aux: radius follows from BC. Goal: equal small arcs BD,DE,EC and segment area.

### Source lines 4111–4657

- grade_9_sgk_1-L4223 [4111–4114] — G: line a; dist(O,a)=4 cm; circles centered O with radii 3,5,4 cm. F: no crop; complete. Aux: none. Goal: classify line-circle relations.
- grade_9_sgk_1-L4244 [4130–4151] — G: chord AB of (O), AB not through O; line through O perpendicular AB meets tangent at A at C. F: H5.27 linked, confirms incidence. Aux: solution adds D=AB∩OC. Goal: CB tangent.
- grade_9_sgk_1-L4267 [4153–4155] — G: square side 6 cm; diagonals meet I; circle (I;3 cm). F: no crop; complete. Aux: none. Goal: circle tangent to all sides.
- grade_9_sgk_1-L4314 [4200–4228] — G: MA,MB tangent to (O;R) at A,B; part b R=2 cm, MO=4 cm. F: H5.29 linked. Aux: solution uses triangles OAM/OBM. Goal: OM⊥AB and tangent lengths.
- grade_9_sgk_1-L4352 [4236] — G: circle radii 4,6,7,8 cm; lines a,b parallel 6 cm apart; centers lie on b. F: no crop; complete. Aux: none. Goal: identify which circles cover line a.
- grade_9_sgk_1-L4354 [4238] — G: circle (O) passes through A,B,C; ΔABC isosceles at A. F: no crop; complete. Aux: line through A parallel BC is requested construction. Goal: that line tangent to (O).
- grade_9_sgk_1-L4356 [4240] — G: ∠xOy with bisector Ot; A∈ray Ox, B∈ray Oy, OA=OB; line through A perpendicular Ox meets Ot at M. F: no crop; complete. Aux: circle (M;MA) occurs in requested claim. Goal: MA,MB are intersecting tangents.
- grade_9_sgk_1-L4358 [4242–4246] — G: SA,SB intersecting tangents to (O) at A,B; M on minor arc AB; tangent at M meets SA at E, SB at F; part b M=(segment SO)∩circle. F: no crop; text complete. Aux: E,F intersections are defined. Goal: perimeter relation and SE=SF. Caveat: “any point on minor arc” can include degenerate endpoints A,B; use interior M or record the convention.
- grade_9_sgk_1-L4421 [4303–4307] — G: OO′=5 cm; circle radii 4 cm,3 cm. F: no crop; complete. Aux: none. Goal: intersection relation; do not elevate solution conclusion to a given.
- grade_9_sgk_1-L4429 [4309–4315] — G: circle (O;5 cm), OI=2 cm; compare circle (I;r), r=4 or6 cm. F: no crop; complete. Aux: none. Goal: relative positions.
- grade_9_sgk_1-L4462 [4342–4348] — G: OO′=5 cm; radii 3 cm,2 cm. F: no crop; complete. Aux: none. Goal: contact type.
- grade_9_sgk_1-L4470 [4350–4352] — G: OO′=3 cm; radii 8 cm,5 cm. F: no crop; complete. Aux: none. Goal: contact type.
- grade_9_sgk_1-L4507 [4387–4393] — G: radii 3 cm,5 cm; OO′>8 cm. F: no crop; complete. Aux: none. Goal: relative position.
- grade_9_sgk_1-L4515 [4395–4397] — G: OO′=2 cm; radii 5 cm and r<3 cm (r>0 implicit as a radius). F: no crop; complete. Aux: none. Goal: relative position by r.
- grade_9_sgk_1-L4539 [4417], needs_review — G: only says circles are outer edges of woven products; asks intersecting/nonintersecting pairs. F: H5.37 absent/unlinked. Following L4541 embeds a different circle schematic also captioned H5.37; not a safe substitute for the woven-product crop. Text has no counts, positions, labels. Aux/Goal: cannot specify fully until correct image is recovered.
- grade_9_sgk_1-L4541 [4419–4424] — G: OO′=5 cm; reference (O;3 cm); compare circles at O′ with radii 3,1,8 cm. F: H5.37 embedded in Markdown and exists but image_paths empty; text gives numeric facts. Aux: none. Goal: relative positions.
- grade_9_sgk_1-L4548 [4426–4432] — G: O,A,O′ collinear; branches A between O,O′; O between A,O′; O′ between A,O; radii OA,O′A. F: no crop; order explicit. Aux: none. Goal: radius relations/contact type.
- grade_9_sgk_1-L4556 [4434] — G: circles (O),(O′) externally tangent at A; line through A meets each again at B,C. F: no crop; “cuts at B,C” conventionally means second intersections; common tangent at A excluded implicitly. Aux: none. Goal: OB∥O′C.
- grade_9_sgk_1-L4560 [4438–4462] — G: circles (O;R),(O′;R′) intersect at A,B; M reflection of A through O; N reflection of A through O′. F: H5.38 linked for orientation; text complete. Aux: circle with diameter AB is introduced as part-b target, not given. Goal: M,N membership; M,B,N collinear; MN tangent to diameter-AB circle.
- grade_9_sgk_1-L4586 [4464–4501] — G: externally separate circles (O;R),(O′;R′), R>R′; common external tangent d touches at A,B; O,O′ on same side of d; P=d∩OO′; A′ reflection of A over OO′. F: H5.39 linked. Aux: solution adds B′, foot from O′ to PA′, to prove second tangency. Goal: PO/PO′=R/R′; PA′ common tangent.
- grade_9_sgk_1-L4627 [4505–4509] — G: parallel a,b; O in strip; distances to a,b are 2 cm,3 cm; circle center O radius R. F: no crop; complete. Aux: none. Goal: R range for cutting both, then circle relation to b when tangent to a.
- grade_9_sgk_1-L4633 [4511–4520] — G: T1,T2 are circles traced by long/short clock-hand tips (common spindle is implicit); radii R1,R2; T3 center is R1/2 from spindle, radius R2/2; final R1=3 cm,R2=2 cm. F: H5.41 embedded and exists but image_paths empty. Aux: none. Goal: relations among circles.
- grade_9_sgk_1-L4644 [4522–4527] — G: circle (O) diameter AB; tangents at A,B; third tangent at P∈circle, P≠A,B meets first/second at M,N; Q=MN∩line through O perpendicular AB. F: no crop; complete. Aux: third tangent and Q are requested constructions. Goal: MN=MA+NB; Q midpoint MN; AB tangent to circle with diameter MN.
- grade_9_sgk_1-L4651 [4529–4533] — G: circles (O),(O′) externally tangent at A; both tangent to d at distinct B,C; tangent to (O) at A meets BC at M. F: no crop; complete. Aux: M is defined intersection. Goal: MA tangent to second circle; M midpoint BC; ABC right.
- grade_9_sgk_1-L4714 [4589–4594] — G: circle (O;4 cm); OA=√15 cm, OB=4 cm. F: no crop; complete. Aux: none. Goal: membership classification.
- grade_9_sgk_1-L4721 [4596–4603] — G: BD diameter; ∠AOB=40°, ∠BOC=100°. F: H5.43 linked and required for cyclic order/orientation; text alone does not specify A,C,D order. Aux: none. Goal: arc DC/AD choice; preserve figure branch.
- grade_9_sgk_1-L4730 [4605–4613] — G: circles (A;R1),(B;R2), R2<R1; circles intersect. F: H5.44 linked; intersecting branch stated. Aux: none. Goal: inequality for AB.
- grade_9_sgk_1-L4740 [4615–4622] — G: circle (O;R), lines a1,a2; d1,d2 distances from O; circle cuts a1 and is tangent to a2. F: H5.45 linked; text complete. Aux: perpendicular distance definitions. Goal: inequalities.
- grade_9_sgk_1-L4751 [4626–4632] — G: circle (O) diameter BC; A≠B,C; part b A is an intersection of (B;BO) and (O) (the non-B intersection is unique); part c BC=6 cm. F: no crop; complete. Aux: none. Goal: right-angle equivalence; triangle angles; arc AC and sector area.
- grade_9_sgk_1-L4759 [4634–4637] — G: chord AB of (O;4 cm), not diameter; C,D antipodes of A,B; part b adds ABCD square. F: no crop; complete. Aux: none. Goal: C,D lie on circle; major arc and sector measures under square condition.
- grade_9_sgk_1-L4764 [4639–4642] — G: B between A,C; AB=2 cm, BC=1 cm; circles (A;1.5 cm),(B;3 cm),(C;2 cm). F: no crop; complete. Aux: none. Goal: identify pairwise intersecting/disjoint/tangent pairs.
- grade_9_sgk_1-L4769 [4644–4646] — G: ΔABC right at A; circles (B;BA),(C;CA) intersect at A,A′. F: no crop; complete. Aux: A′ is the second intersection. Goal: BA,BA′ and CA,CA′ are tangent pairs.
- grade_9_sgk_1-L4773 [4648–4657] — G: circles (O),(O′) intersect at A,B; line d through A meets first at E≠A, second at F≠A; A strictly between E,F; I,K are midpoints AE,AF. F: H5.46 linked; text complete. Aux: midpoint definitions are part of setup. Goal: OO′KI right trapezoid; IK=EF/2; condition for rectangle.
