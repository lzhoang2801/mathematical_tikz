# Grade 8 SGK 2 — mathematical-givens audit

## Scope and verification

Source manifest: docs/dataset-selection/grade-8.problems.jsonl. Corpus source: 8/grade_8_sgk_2/book.final.md. The manifest has 118 rows for this book. I excluded 17 rows carrying A01, including mixed-label algebra record grade_8_sgk_2-L2728 (G03, A01): L1955, L1973, L2024, L2035, L2061, L2067, L2096, L2270, L2285, L2302, L2325, L2550, L2562, L2626, L2640, L2662, L2728. The remaining 101 rows are geometry: 90 prepared and 11 needs_review.

For all 101 retained rows, the manifest source_text equals the corpus text at the listed one-based line range. There are 61 figure-dependent rows. Fifty-two rows have nonempty image_paths (81 references; all files exist). The source_text also contains 88 inline image references, all of which resolve; seven are omitted from the corresponding image_paths fields: L4370, L4663 (two refs), L5168, L5185, L5347, and L5484. Nine F rows have empty image_paths: L4230, L4370, L5166, L5179, L5185, L5345, L5478, L5484, and L5492. F means the statement depends on a referenced figure for incidence, labels, measurements, or layout beyond what the text states. Figure facts are flagged here rather than transcribed from pixels.

Each row separates givens from the requested outcome. The outcome/proof conclusion is not a given. Aux codes: A0 = solution excerpt is in this source range and contains no new auxiliary line; A1 = no solution excerpt in this source range, so no solution-added line is source-verified; A2 = solution excerpt adds/uses the stated auxiliary construction. For A0 and A1, this does not claim that no auxiliary construction could help when independently solving the problem. The explicit source-added constructions are listed after the inventory.

All IDs below have the exact prefix grade_8_sgk_2-L. P = prepared; R = needs_review. F and Aux are recorded per row.

## Similarity and elementary geometry

- 3702, lines 3457–3465, R; Given: △ABC ∼ △MNP. Goal: identify the incorrect reordered similarity claim. No concrete measurements or figure. Aux A1.
- 3712, lines 3467–3477, R; Given: generic claims about congruence/similarity, equilateral triangles, and right triangles. Goal: select true claims. Conceptual item, no concrete diagram. Aux A1.
- 3724, lines 3479–3482, P, F; Given: ABC is scalene; M,N,P are midpoints of BC, CA, AB. Goal: find five distinct mutually similar triangles and explain. Figure 9.9 supplies drawn segments and the configurations to compare. Aux A1.
- 3729, line 3484, P; Given: ABC is isosceles at A; MNP is isosceles at M; ∠BAC = ∠PMN; AB = 2MN. Goal: prove △MNP ∼ △ABC and find the similarity ratio. Aux A1.
- 3792, lines 3543–3557, P, F; Given: triangles ABC and MNP; 3AB = 4BC = 8CA; MN = 8, NP = 6, PM = 3 cm. Goal: prove △ABC ∼ △MNP. Figure 9.14 supplies the diagram. Aux A0.
- 3809, lines 3559–3563, P; Given: P(ABC) = 18 cm, P(DEF) = 27 cm; AB = 4, BC = 6, DE = 6, FD = 12 cm. Goal: prove △ABC ∼ △DEF. Aux A1.
- 3887, lines 3627–3644, P, F; Given: △A′B′C′ ∼ △ABC; M,M′ are midpoints of BC,B′C′. Goal: prove △A′B′M′ ∼ △ABM. Figure 9.18 supplies the diagram. Aux A0.
- 3907, lines 3646–3648, P; Given: △A′B′C′ ∼ △ABC; M,M′ lie on rays opposite CB,C′B′; MC/MB = M′C′/M′B′. Goal: prove △A′B′M′ ∼ △ABM. Aux A1.
- 3979, lines 3714–3744, P, F; Given: △A′B′C′ ∼ △ABC; AM,A′M′ are corresponding angle bisectors. Goal: prove △A′B′M′ ∼ △ABM. Figure 9.23 supplies the diagram. Aux A0.
- 4011, lines 3746–3750, P, F; Given: A,B,C,D as in Figure 9.24; ∠ABC = ∠ADB. Goal: prove △ABC ∼ △ADB and AB² = AD·AC. Figure supplies incidence. Aux A1.
- 4025, lines 3760–3768, R; Given: four generic proposed similarity criteria: three proportional side pairs; two proportional side pairs plus an equal angle; two equal angle pairs; two equal side pairs. Goal: identify which assumptions establish similarity. No concrete figure. Aux A1.
- 4035, lines 3770–3774, P; Given: two similar triangles; first triangle sides 4, 8, 10 cm; second perimeter 33 cm; four candidate side triples are stated. Goal: choose the second triangle side triple. Aux A1.
- 4041, lines 3776–3778, P; Given: AM,BN,CP are medians of ABC; A′M′,B′N′,C′P′ are medians of A′B′C′; △A′B′C′ ∼ △ABC. Goal: prove the three corresponding median ratios are equal. Aux A1.
- 4045, line 3780, P; Given: AB = 12, AC = 15 cm; M lies on ray AB, N on ray AC; AM = 10, AN = 8 cm. Goal: prove △ABC ∼ △ANM. Aux A1.
- 4047, lines 3782–3786, P; Given: angle BAC; M∈AB, N∈AC; ∠ABN = ∠ACM; I = BN∩CM. Goal: prove △ABN ∼ △ACM and IB·IN = IC·IM. Aux A1.
- 4053, lines 3788–3791, P, F; Given: two vertical posts on level ground have heights 3 m and 2 m; cross-wires join opposite tops and feet. Goal: find the crossing point height h above ground. Figure 9.25 supplies the layout. Aux A1.
- 4060, lines 3795–3811, P, F; Given: points A,B,C,D,E as in Figure 9.26; AB = 6, AC = 9, AD = 8, BC = 12, BD = 4 cm. Goal: prove △ABC ∼ △BDA and △BDE ∼ △ACE. Figure supplies incidence. Aux A0; the solution derives AC∥BD and uses existing extensions through A,C, without adding a new named segment.
- 4078, lines 3813–3832, P, F; Given: angle xOy; A,B∈ray Ox, C,D∈ray Oy; OA = 2, OB = 6, OC = 3, OD = 4 cm; E = AD∩BC. Goal: find BE/DE. Figure 9.27 supplies layout. Aux A0.
- 4101, line 3836, P; Given: △ABC ∼ △DEF; ∠A = 60°, ∠E = 80°. Goal: find ∠B,∠C,∠D,∠F. Aux A1.
- 4103, line 3838, P; Given: △ABC ∼ △A′B′C′; AB = 3 cm, A′B′ = 6 cm, perimeter ABC = 10 cm. Goal: find perimeter A′B′C′. Aux A1.
- 4105, lines 3840–3846, P, F; Given: trapezoid ABCD with AB∥CD; ∠DAB = ∠DBC; AB = 2, AD = 3, BD = 4 cm. Goal: prove △ABD ∼ △BDC and find BC,DC. Figure 9.28 supplies layout. Aux A1.
- 4113, lines 3848–3850, P, F; Given: points A–F as in Figure 9.29; DE∥AB, EF∥BC; DE = 4, AB = 6 cm. Goal: prove △AEF ∼ △ECD and find the similarity ratio. Aux A1.
- 4117, lines 3852–3855, P, F; Given: points A–E as in Figure 9.30; ∠BAC = ∠CDB. Goal: prove △AED ∼ △BEC. Figure supplies incidence. Aux A1.
- 4122, line 3857, P; Given: trapezoid ABCD with AB∥CD; M∈AD,N∈BC; 2AM = MD, 2BN = NC; AB = 5, CD = 6 cm. Goal: find MN. Aux A1.

## Right triangles, Pythagorean theorem, and similarity applications

- 4208, lines 3939–3959, P; Given: triangle ABC with AB = 3, AC = 4, BC = x cm; consider the cases where the right angle is at B and at A. Goal: find x in each case. Aux A0.
- 4230, lines 3961–3963, P, F; Given: grid spacing 1 cm; points A,B,C as in Figure 9.35. Goal: find all triangle side lengths. Figure supplies point positions. Aux A1.
- 4271, lines 4002–4011, P, F; Given: right triangles and dimensions in Figure 9.37. Goal: find x and identify similar triangles. Aux A1.
- 4323, lines 4048–4057, P, F; Given: △ABC and △A′B′C′ are right at A,A′; AB = A′B′ and BC = B′C′. Goal: prove the stated right-triangle congruence result using Pythagoras. Figure 9.41 accompanies the statement. Aux A1.
- 4346, lines 4068–4070, R; Given: ABC is right at A; four equations relating AB,BC,AC are listed. Goal: classify each equation as true or false. Aux A1.
- 4350, lines 4072–4076, P; Given: candidate side triples (1,1,2), (2,4,20), (5,4,3), (2,2,2√2) cm. Goal: select the triple forming a right triangle. Aux A1.
- 4356, lines 4078–4085, P, F; Given: x,y,z,t labels in Figure 9.43. Goal: calculate their values. Figure supplies all measurements and incidence. Aux A1.
- 4365, lines 4087–4088, P; Given: ABC is isosceles at A; altitude AH = 3 cm; base BC = 10 cm. Goal: find AB and AC. Aux A1.
- 4368, line 4090, P; Given: rectangle width 8 cm; diagonal 17 cm. Goal: find its area. Aux A1.
- 4370, lines 4092–4095, R, F; Given: square ABCD side 5 m; dog tethered at A by a 6 m rope; garden region has boundary A,B,E,F,D. Goal: decide whether the dog can reach every garden point. Figure 9.44 supplies E,F locations and garden shape. Aux A1.
- 4416, lines 4136–4167, P, F; Given: AD,BE,CF are altitudes of ABC and meet at H. Goal: prove HA·HD = HB·HE = HC·HF and △AEF ∼ △ABC. Figure 9.47 accompanies the solution. Aux A0.
- 4449, lines 4169–4178, P, F; Given: pole and shadow form right triangle ABC at A; Việt and his shadow form right triangle A′B′C′ at A′; sunlight gives ∠B = ∠B′. Goal: decide whether the triangles are similar and explain how to calculate pole height AC. Figure 9.48 and the referenced opening situation supply further context. Aux A1.
- 4518, lines 4234–4257, P, F; Given: altitude feet H,H′ from A,A′ lie on BC,B′C′; A′B′/AB = A′H′/AH = A′C′/AC. Goal: prove △A′B′C′ ∼ △ABC. Figure 9.53 supplies layout. Aux A0.
- 4544, lines 4259–4264, P, F; Given: two sloping roof segments AB,CD; CD = 6 m, AB = 4 m, HA = 2 m, AC = 1 m. Goal: prove ∠ABD = ∠CDB. Figure 9.54 supplies incidence. Aux A1.
- 4557, lines 4272–4280, R; Given: generic proposed criteria for similarity of two right triangles: equal acute angles; proportional leg and hypotenuse; one equal leg; proportional leg pairs. Goal: identify a sufficient condition. No concrete figure. Aux A1.
- 4567, lines 4282–4291, P, F; Given: right triangles in Figure 9.55. Goal: identify similar pairs. The figure supplies their measurements. Aux A1.
- 4578, line 4293, P; Given: acute angle xOy; A,N∈ray Ox and B,M∈ray Oy; AM⊥Oy, BN⊥Ox. Goal: prove △OAM ∼ △OBN. Aux A1.
- 4580, lines 4295–4299, P; Given: rectangles ABCD,A′B′C′D′; AC = 3AB, B′D′ = 3A′B′; A′B′ = 2AB; area ABCD = 2 m². Goal: prove △ABC ∼ △A′B′C′ and find area A′B′C′D′. Aux A1.
- 4586, lines 4301–4305, P; Given: △A′B′C′ ∼ △ABC with ratio k; A′H′ and AH are corresponding altitudes. Goal: prove A′H′/AH = k and the area ratio is k². Aux A1.
- 4592, lines 4307–4310, P, F; Given: A and B lie on opposite sides of an impassable river; M is on the bank; AM = 2 m and AM⊥AB; ∠AMB is measured. A paper triangle A′M′B′ is right at A′, A′M′ = 1 cm, ∠A′M′B′ = ∠AMB, A′B′ = 5 cm. Goal: find AB in metres. Figure 9.56 supplies layout. Aux A1.
- 4663, lines 4363–4388, P, F; Given: example pairs include squares, circles, and equilateral triangles; further examples concern perspective similarity, nature, architecture, and design. Goal: illustrate similar-shape examples. Figures 9.62–9.63 and related images supply the examples. Aux A1.
- 4721, lines 4390–4402, P, F; Given: three pictured shape pairs. Goal: identify similar pairs and draw a perspective-similar pair with a common center. Figure 9.67 supplies shapes. Aux A1.
- 4751, line 4414, P; Given: O lies outside segment AB; scale ratio 1/2. Goal: construct the perspective-similar image of AB centered at O. Aux A1.
- 4753, lines 4416–4429, P, F; Given: four pictured shapes. Goal: find the similar pairs. Figure 9.68 supplies shapes. Aux A1.
- 4768, lines 4431–4441, P, F; Given: pairs of regular hexagons, equilateral triangles, and squares. Goal: identify which pair is perspective-similar. Figure 9.69 supplies placement. Aux A1.
- 4782, lines 4445–4478, P, F; Given: ABC right at A; AH is an altitude; AB = 5 cm, AH = 4 cm. Goal: prove △AHB ∼ △CHA and find BH,CH,AC. Figure 9.70 accompanies the solution. Aux A0.
- 4817, lines 4480–4521, P, F; Given: AB = 4, AC = 3, BC = 5 cm; AH is an altitude; M,N are midpoints of AH,BH. Goal: prove the stated metric identities and △ANB ∼ △CMA. Figure 9.71 supplies layout. Aux A0.
- 4862, lines 4525–4529, P; Given: ABC right at A with altitude AH; BH = 16, CH = 9 cm. Goal: find AH, AB, AC. Aux A1.
- 4868, lines 4531–4535, P; Given: AB = 6, AC = 8, BC = 10 cm; M∈BC and BM = 4 cm; MN⊥AC at N; MP⊥AB at P. Goal: prove △BMP ∼ △MCN and find AM. Aux A1.
- 4874, lines 4537–4543, P, F; Given: AH,HE,HF are altitudes of triangles ABC, AHB, AHC respectively. Goal: prove the three stated triangle similarities. Figure 9.72 supplies incidence. Aux A1.
- 4882, line 4545, P; Given: ABC right at A; AH is an altitude; M,N are midpoints of AB,AC. Goal: prove △HBM ∼ △HAN. Aux A1.
- 4884, lines 4547–4551, P; Given: near noon An’s shadow is 60 cm and the flagpole shadow is 3 m; An is 1.4 m tall; later An’s shadow is 3 m. Goal: find the flagpole height and its later shadow length. Aux A1.
- 4894, lines 4557–4558, R; Given: ABC is scalene; △A′B′C′ ∼ △ABC. Goal: choose the correct vertex-ordering claim. Aux A1.
- 4897, lines 4560–4564, R; Given: △A′B′C′ ∼ △ABC with ratio 2. Goal: select the correct side-ratio statement. Aux A1.
- 4903, lines 4566–4570, R; Given: candidate triples (3,5,6), (6,8,10), (1,0.5,1.25), (9,16,25) m. Goal: identify a right-triangle triple. Aux A1.
- 4909, lines 4572–4577, R; Given: ABC right at A and DEF right at D; AB≠AC, DE≠DF; options give angle relations between B,C,E,F. Goal: identify which option does not imply triangle similarity. Aux A1.
- 4918, lines 4581–4584, P, F; Given: Figure 9.73; MN∥AB and MP∥AC. Goal: list three distinct similar triangle pairs. Figure supplies vertex incidence. Aux A1.
- 4923, lines 4586–4588, P, F; Given: Figure 9.74; ∠ABD = ∠ACE. Goal: prove △ABD ∼ △ACE and △BOE ∼ △COD. Figure supplies incidence. Aux A1.
- 4927, lines 4590–4594, P, F; Given: BM,CN are medians of ABC and meet at G; M,N are opposite-side midpoints. Goal: prove △GMN ∼ △GBC and find the ratio. Figure 9.75 supplies layout. Aux A1.
- 4933, lines 4596–4600, P; Given: ABC right at A; AB = 5, AC = 4 cm; AH is an altitude; HD is an altitude in △HAB. Goal: prove △HDA ∼ △AHC and find HA,HB,HC,HD. Aux A1.
- 4939, lines 4602–4608, P, F; Given: AH is an altitude; AH = 12, CH = 9, BH = 16 cm; M,N are midpoints of AH,BH. Goal: prove ABC is right at A; prove MN⊥AC and CM⊥AN; find area AMN. Figure 9.76 supplies layout. Aux A1.
- 4947, lines 4610–4617, P, F; Given: ABC right at A; D,E,F as in Figure 9.77; AD bisects ∠BAC; DE⊥AC and DF⊥BC. Goal: prove the stated ratios, similarity, and DF = DB. Figure supplies incidence. Aux A1.
- 4956, line 4619, P; Given: vertical stick height 1 m and shadow 1.5 m; pyramid shadow 208.2 m. Goal: find pyramid height. Aux A1.
- 4958, line 4621, P; Given: Lan is 1 m from a window; window height 80 cm; opposite building has six floors of 4 m each; her sightline just spans the building. Goal: find distance to the building. Sightline geometry is implicit in the scenario. Aux A1.

## Pyramids and spatial geometry

- 5067, lines 4721–4743, P, F; Given: regular triangular pyramid S.ABC in Figure 10.7. The solution gives base sides 5 cm and slant altitude SH = 6 cm. Goal: find lateral surface area. Aux A0; SH is used as the slant segment, but the figure may already show it.
- 5091, lines 4745–4749, P, F; Given: regular triangular pyramid S.MNP; IP = 3, SP = 5 cm. Goal: find lateral surface area. Figure 10.8 locates I,P. Aux A1.
- 5118, lines 4772–4808, P, F; Given: regular triangular pyramid S.ABC; base side 6 cm; pyramid height SO = 10 cm; √27≈5.2. Goal: find base area and volume. Aux A2: the solution uses CH⊥AB and H as midpoint of AB; whether already drawn in Figure 10.10 is figure-dependent.
- 5166, line 4820, P, F; Given: regular triangular pyramid in Figure 10.12. Goal: name vertex, lateral edges/faces, base, height, and a slant segment. Figure supplies labels. Aux A1.
- 5168, lines 4822–4831, P, F; Given: equilateral triangle side 10 cm; fold along orange lines to form a regular triangular pyramid. Goal: construct/fold the pyramid net. Figure supplies crease pattern. Aux A1.
- 5179, lines 4833–4837, P, F; Given: regular triangular pyramid S.MNP; base side 6 cm; height 5 cm; √27≈5.2. Goal: find base area and volume. Figure 10.15 supplies layout. Aux A1.
- 5185, lines 4839–4842, P, F; Given: regular triangular pyramid model with every edge 20 cm; √300≈17.32. Goal: find the paper area covering the lateral faces. Figure 10.16 supplies layout. Aux A1.
- 5237, lines 4883–4901, P, F; Given: regular square pyramid S.MNPQ in Figure 10.19. Goal: identify its vertex, lateral edges/faces, base, height, and one slant segment. Figure supplies labels. Aux A0.
- 5298, lines 4944–4966, P, F; Given: regular square pyramid S.ABCD; base side 6 cm; height 4 cm; slant segment 5 cm. Goal: find lateral area and volume. Figure 10.22 supplies layout. Aux A0.
- 5322, lines 4968–4970, P; Given: wooden regular square pyramid box; base side 2 m; slant segment 3 m; painting costs 30,000 đồng/m². Goal: find painting cost. Aux A1.
- 5326, lines 4972–4981, P, F; Given: regular square-pyramid tent; base side 2 m; height 2 m; each lateral-face altitude 2.24 m. Goal: find air volume and fabric area including ground face. Figure 10.23 supplies layout. Aux A1.
- 5345, line 4989, P, F; Given: regular square pyramid S.EFGH in Figure 10.24. Goal: name vertex, lateral edges/faces, base, height, and one slant segment. Figure supplies labels. Aux A1.
- 5347, lines 4991–5002, P, F; Given: pictured cardboard nets. Goal: identify which folds into a regular square pyramid. Figure 10.25 supplies all net geometry. Aux A1.
- 5360, lines 5004–5027, P, F; Given: square sheet and the pictured sequence of operations. Goal: form the lateral faces of a regular square pyramid. Figure 10.26 supplies cuts/folds. Aux A1.
- 5385, lines 5029–5035, P, F; Given: regular square pyramid S.ABCD; base side 10 cm; slant segment 13 cm. Goal: find lateral and total surface areas. Figure 10.27 supplies layout. Aux A1.
- 5393, line 5037, P; Given: regular square pyramid; base side 3 cm; height 3 cm. Goal: find volume. Aux A1.
- 5398, lines 5039–5043, P, F; Given: concrete block with lower square prism base side 40 cm, height 25 cm; upper regular square pyramid height 100 cm. Goal: find total volume. Figure 10.29 supplies composition. Aux A1.
- 5406, lines 5047–5061, P, F; Given: regular triangular pyramid S.HIK in Figure 10.30. The solution uses base sides 10 cm and slant segment 12 cm. Goal: find lateral surface area. Aux A0.
- 5422, lines 5063–5082, P, F; Given: regular square-pyramid roof cover; its four lateral faces are equilateral triangles of side 2 m; border width negligible. Goal: find glass area. Figure 10.31 supplies layout. Aux A2: solution introduces H as midpoint of CD in equilateral face SCD and uses SH⊥CD, the face altitude; the figure may already draw it.
- 5447, line 5086, P; Given: regular triangular pyramid S.ABC; base area 15.6 cm²; height 10 cm. Goal: find volume. Aux A1.
- 5449, lines 5088–5098, P, F; Given: pictured cardboard nets. Goal: distinguish nets folding into regular triangular versus regular square pyramids. Figure 10.32 supplies net geometry. Aux A1.
- 5461, lines 5100–5103, P, F; Given: regular triangular pyramid A.BCD; base side 10 cm; height 12 cm; √75≈8.66. Goal: find volume. Figure 10.33 supplies layout. Aux A1.
- 5466, lines 5105–5109, P; Given: Louvre model is a regular square pyramid; height 21 m; base side 34 m; lateral edge 31.92 m. Goal: find volume and glazing area for four lateral faces. Aux A1.
- 5478, lines 5115–5119, P, F; Given: regular triangular pyramid in Figure 10.34; options SB,SH,SI,HI. Goal: identify the slant segment. Figure supplies point placement. Aux A1.
- 5484, lines 5121–5127, R, F; Given: regular square pyramid; options for its base are square, parallelogram, rhombus, rectangle. Goal: select the base shape. Figure 10.?? supplies pictured context. Aux A1.
- 5492, lines 5129–5135, P, F; Given: conceptual formula choices for lateral area of a regular triangular pyramid, using base perimeter/half-perimeter and slant segment. Goal: select the correct formula. Aux A1.
- 5500, lines 5137–5141, P; Given: regular triangular pyramid with height h and volume V. Goal: express base area S. Aux A1.
- 5508, lines 5145–5152, P, F; Given: regular triangular and square pyramids in Figure 10.35. Goal: identify vertices, edges, height, and one slant segment for each. Figure supplies labels. Aux A1.
- 5517, lines 5154–5162, P, F; Given: regular triangular and square pyramids in Figure 10.36. Goal: find each lateral surface area. Figure supplies measurements. Aux A1.
- 5527, line 5164, P; Given: regular square pyramid; height 9 cm; base perimeter 12 cm. Goal: find volume. Aux A1.
- 5529, lines 5166–5169, P, F; Given: cube side 30 cm; remaining solid is a regular square pyramid with base side 30 cm and height 30 cm. Goal: find removed volume. Figure 10.37 supplies the cut orientation. Aux A1.
- 5534, lines 5171–5174, P, F; Given: wood block has a cube base side 9 cm and a regular square pyramid on top. Goal: find block volume. Figure 10.38 is needed for pyramid dimensions. Aux A1.
- 5539, lines 5176–5179, P, F; Given: equilateral triangular sheet side 20 cm; fold along dotted lines to form a regular triangular pyramid; √75≈8.66. Goal: find lateral surface area. Figure 10.39 supplies fold pattern. Aux A1.

## Solution-added auxiliary lines, separated from conclusions

- L5118: add/use CH perpendicular to AB in the equilateral base; H is the midpoint of AB. The requested conclusion is base area and pyramid volume.
- L5422: add/use H as midpoint of CD in equilateral face SCD and SH perpendicular to CD. The requested conclusion is the four-face glass area.
- L4060: the solution derives AC parallel to BD and refers to existing extensions through A,C; this is a derived relation, not a new named segment.
- Other source ranges with worked solutions mainly establish the requested similarity/metric conclusions using stated or figure-provided segments. For exercise-only ranges, no solution-added auxiliary line is source-verified in the manifest slice; candidate Edit variants may still be designed from a separately solved construction.