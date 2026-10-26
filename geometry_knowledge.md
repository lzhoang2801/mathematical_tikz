# Geometry Knowledge

## Contract

- Use the 16 base predicates with their exact names, parameter order, and meaning.
- Use a derived predicate only when its complete expansion is defined below; expand it into base predicates before solving.
- Additional spatial predicates are typed primitives because planar predicates cannot express spatial incidence faithfully.
- Predicate names must be established mathematical terms. Never invent an alias, reverse a parameter order, or overload one name with unrelated meanings.
- Emit only relations stated explicitly or implied with certainty by a definition or a theorem required by the problem.
- Never invent a length, angle, incidence, orientation, point order, or auxiliary object.
- Each predicate below states its own required visible evidence. A construction that
  is correct only in coordinates or source is not sufficient; ordinary incidence
  needs no invented decoration.

## Points, Segments, Lines, Rays and Order

- A point is named by a capital letter such as `A`, `B`, `O`, `M`, or `H`.
- Segment `AB`, also written `[AB]`, is finite and has endpoints `A,B`.
- Straight line `(d)` is unbounded in both directions and has no endpoints. Distinct points `A,B` on `(d)` may determine it; they are not endpoints of `(d)`. Its render extends visibly beyond both defining points.
- Ray `Ox` has origin `O` and is unbounded in direction `x`. Its render has an arrowhead in that direction and preserves the stated order of its named points.
- Preserve extent exactly. Never render a segment as a straight line, a straight line as a segment, or a ray as either one.

Base predicates:

- `online(P,A,B)`: `P` lies on the straight line determined by distinct points `A,B`; it asserts collinearity only.
- `online_inside(P,A,B)`: `P` lies strictly between `A,B`, inside segment `AB`.
- `online_extension(P,A,B)`: `P` is collinear with `A,B` and lies outside segment `AB`. The statement must separately identify the extended endpoint and point order.
- `midpoint(M,A,B)`: `M` is the midpoint of segment `AB`; entails `online_inside(M,A,B)` + `equal_line(A,M,M,B)`. Render the parent segment `AB` as one continuous visible stroke (or its two visibly joined halves), place `M` on it, and put matching native equality marks across `AM` and `MB`.

Derived mathematical predicates:

- `collinear(P,A,B)` := `online(P,A,B)`.
- `between(P,A,B)` := `online_inside(P,A,B)`.
- `on_extension(P,A,B)` := `online_extension(P,A,B)` plus the stated endpoint and point order.
- `intersection(P,(AB),(CD))` := `online(P,A,B)` + `online(P,C,D)`.
- `interior_intersection(P,[AB],[CD])` := `online_inside(P,A,B)` + `online_inside(P,C,D)`.
- `concurrent(P,(A1B1),...,(AnBn))` := `online(P,A1,B1)` + ... + `online(P,An,Bn)`.

The base predicates do not distinguish the two directions outside segment `AB`. Therefore `on_ray(P,Ox)` is not derivable from `online_extension` alone and requires directed point-order data; retain it as a semantic ray obligation rather than weakening it to `online`.

## Lengths, Angles, and Line Relations

Base predicates:

- `dist(A,B,value)`: distance `AB`, equivalently the length of segment `AB`, equals `value`. The value is statement data, not a diagram-label obligation. Do not annotate `AB` with it unless the caller explicitly asks for that measurement to be shown in the diagram.
- `angle(A,B,C,theta)`: `angle ABC = theta` degrees. Parameter order must exactly match the angle notation; the middle point `B` is the vertex. Render an angle arc at `B` with the stated value, except `theta=90`, which needs a right-angle square.
- `angle_relation(A,B,C,D,E,F,m)`: `angle ABC = m * angle DEF`, preserving both angle orders exactly. Render matching angle arcs, with a multiplier/value annotation whenever equality alone does not communicate `m`.
- `ortho(A,B,C,D)`: the supporting straight lines `(AB),(CD)` are perpendicular. Render a right-angle square touching both strokes at their actual intersection; near-perpendicular coordinates or a detached square are not evidence.
- `equal_line(A,B,C,D)`: segments `AB,CD` have equal length. When the equality is a stated usable relation, visibly draw both finite support segments and put matching native equality marks across exactly those segments. Reuse one mark pattern only when equality is logically entailed; use a distinct pattern for every unrelated equality class.
- `angle_bisector(A,D,C,A,B)`: ray `AD` bisects `angle CAB`; the duplicated `A` remains the angle vertex. Render the two component angles with matching arcs.
- `parallel(A,B,C,D)`: the supporting straight lines `(AB),(CD)` are parallel. Render the corresponding supporting strokes with the stated extent. Do not add parallel-arrow marks in this harness.
- `line_ratio(A,B,C,D,m)`: `CD = m * AB`. Parameter direction is fixed; `line_ratio(D,C,B,D,4)` means `BD = 4 * DC`. The multiplier is statement data, not a diagram-label obligation; annotate it only on an explicit caller request.

Derived mathematical predicates:

- `equal_angles(A,B,C,D,E,F)` := `angle_relation(A,B,C,D,E,F,1)`.
- `perpendicular_at(P,(AB),(CD))` := `online(P,A,B)` + `online(P,C,D)` + `ortho(A,B,C,D)`.
- `perpendicular_bisector((EM),M,[BC])` := `midpoint(M,B,C)` + `ortho(E,M,B,C)`. The perpendicular bisector is also called the mediator.
- `orthogonal_projection(H,P,(AB))` := `online(H,A,B)` + `ortho(P,H,A,B)`. Use `online_inside(H,A,B)` only when the foot lies inside segment `AB`.
- `altitude([AH],A,[BC])` := `online_inside(H,B,C)` + `ortho(A,H,B,C)`. If the foot is outside the side, replace `online_inside` with the correctly directed `online_extension`.
- `median([AM],A,[BC])` := `midpoint(M,B,C)`.
- `parallel_through((PQ),P,(AB))` := `parallel(P,Q,A,B)`.
- `tangent((PT),T,(O,r))` := `dist(O,T,r)` + `ortho(O,T,P,T)`; `T` is the point of tangency. Draw radius `OT`, the tangent through `T`, and the attached right-angle square at `T`; one-point contact alone is not enough.
- `tangents(P,A,B,(O,r))` := `tangent((PA),A,(O,r))` + `tangent((PB),B,(O,r))` + `equal_line(P,A,P,B)`.

## Triangles and Polygons

Base predicates:

- `is_point_in_triangle(A,B,C,P)`: `P` lies strictly inside triangle `ABC`.
- `is_point_out_triangle(A,B,C,P)`: `P` lies outside triangle `ABC`.
- `is_acute_triangle(A,B,C)`: triangle `ABC` is acute.

Derived mathematical predicates:

- `right_triangle(A,B,C)` := `angle(A,B,C,90)` when `B` is the right-angle vertex.
- `isosceles_triangle(A,B,C)` := `equal_line(A,B,A,C)` when `A` is the apex.
- `equilateral_triangle(A,B,C)` := `equal_line(A,B,B,C)` + `equal_line(B,C,C,A)`.
- `parallelogram(A,B,C,D)` := `parallel(A,B,C,D)` + `parallel(A,D,B,C)`.
- `rectangle(A,B,C,D)` := `parallelogram(A,B,C,D)` + `ortho(A,B,B,C)`.
- `rhombus(A,B,C,D)` := `parallelogram(A,B,C,D)` + `equal_line(A,B,B,C)` + `equal_line(B,C,C,D)` + `equal_line(C,D,D,A)`.
- `square(A,B,C,D)` := `rectangle(A,B,C,D)` + `rhombus(A,B,C,D)`.
- `trapezoid(A,B,C,D; bases AB,CD)` := `parallel(A,B,C,D)`; do not assert that the legs are parallel.
- `isosceles_trapezoid(A,B,C,D; bases AB,CD)` := `trapezoid(A,B,C,D)` + `equal_line(A,D,B,C)`.
- `orthocenter(H,A,B,C)` := `ortho(A,H,B,C)` + `ortho(B,H,A,C)`; the third altitude follows as a theorem.
- `centroid(G,A,B,C)` := `midpoint(M,B,C)` + `online_inside(G,A,M)` + `midpoint(N,A,C)` + `online_inside(G,B,N)`.
- `circumcenter(O,A,B,C)` := `equal_line(O,A,O,B)` + `equal_line(O,B,O,C)` for non-collinear `A,B,C`.
- `incenter(I,A,B,C)` := `angle_bisector(A,I,C,A,B)` + `angle_bisector(B,I,A,B,C)`; the third internal angle bisector follows as a theorem.
- `congruent_triangles(ABC,DEF)` := the required corresponding `equal_line` and `equal_angles` constraints in the declared vertex correspondence.
- `similar_triangles(ABC,DEF,k)` := the required corresponding `line_ratio` and `equal_angles` constraints in the declared vertex correspondence.

An excenter requires external angle bisectors. The base predicates do not encode an external bisector, so do not misuse `angle_bisector` for it.

## Circles and Conics

Base predicate:

- `arc_midpoint(M,A,B)`: `M` is the midpoint of arc `AB`. Constrain `A,B,M` to the same circle with `dist` and preserve whether the selected arc is minor or major. Render the selected arc and matching native equality marks on its `AM` and `MB` halves.

A stated symbolic radius such as `R` or `r` is statement data, not an automatic
visible measurement obligation. Draw a radius only when it is required carrier
geometry (for example, to show a tangent's perpendicular radius), and do not
label it `R` or `r` unless the caller explicitly asks for that measurement in the
diagram. Never replace a requested stated symbol with an arbitrary numeric
working radius. A required radius support does not license a new named point: if
its circumference endpoint is not named by the problem, use an unnamed
coordinate with no point marker or point label. When tangent circles already
share a named contact point, reuse that contact point as the endpoint of both
displayed radii instead of inventing separate circumference points.

Derived mathematical predicates:

- `on_circle(A,(O,r))` := `dist(O,A,r)`.
- `chord([AB],(O,r))` := `dist(O,A,r)` + `dist(O,B,r)`.
- `diameter([AB],(O,r))` := `chord([AB],(O,r))` + `online_inside(O,A,B)` + `equal_line(O,A,O,B)`.
- `secant((PAB),(O,r))` := `online(P,A,B)` + `dist(O,A,r)` + `dist(O,B,r)` for distinct intersections `A,B`.
- `tangent((PT),T,(O,r))` uses the expansion under line relations.
- `cyclic_quadrilateral(A,B,C,D;(O,r))` := `dist(O,A,r)` + `dist(O,B,r)` + `dist(O,C,r)` + `dist(O,D,r)`.
- `central_angle(A,O,B;r,theta)` := `angle(A,O,B,theta)` + `dist(O,A,r)` + `dist(O,B,r)`.
- `inscribed_angle(A,P,B;O,r,theta)` := `angle(A,P,B,theta)` + `dist(O,A,r)` + `dist(O,P,r)` + `dist(O,B,r)`.
- Radius `OM` perpendicular to chord `AB` at `M` := `online_inside(M,A,B)` + `ortho(O,M,A,B)`; the perpendicular-from-center theorem gives `midpoint(M,A,B)`.

Arc equality, circle-circle tangency, ellipse, parabola, and hyperbola are not exactly expressible by the 16 base predicates. Preserve them as explicit semantic constraints; never replace a conic with an unconstrained freehand curve.

## Coordinates, Vectors, and Transformations

- Coordinate assignment `A=(x,y)` is exact input data, not a predicate.
- `central_symmetry(P,Q;O)` := `midpoint(O,P,Q)`.
- `reflection(P,Q;(AB))` := `midpoint(M,P,Q)` + `online(M,A,B)` + `ortho(P,Q,A,B)` for the derived midpoint `M`.
- `rotation(P,Q;O,theta)` without an orientation requirement := `equal_line(O,P,O,Q)` + `angle(P,O,Q,theta)`.
- Translation, signed homothety, and vector equality require directed orientation. The 16 base predicates encode only their undirected length, ratio, collinearity, and parallelism components; do not claim an exact expansion without directed primitives.

## Spatial Geometry

Spatial objects:

- `line(d;A,B)`: spatial line `d` determined by distinct points `A,B`.
- `plane(alpha;A,B,C)`: plane `alpha` determined by non-collinear points `A,B,C`.
- `sphere(S;O,r)`: sphere `S` with center `O` and radius `r`.

Spatial incidence predicates:

- `on_line(P,d)`: point `P` lies on spatial line `d`.
- `on_plane(P,alpha)`: point `P` lies on plane `alpha`.
- `on_sphere(P,S)`: point `P` lies on sphere `S`.
- `coplanar(A,B,C,D)`: points `A,B,C,D` lie in one plane.
- `intersection_of_lines(P,d,e)`: spatial lines `d,e` intersect at `P`.
- `intersection_of_line_and_plane(P,d,alpha)`: line `d` intersects plane `alpha` at `P`.
- `intersection_of_planes(d,alpha,beta)`: distinct planes `alpha,beta` intersect in line `d`.

Spatial relation predicates:

- `parallel_lines(d,e)`: coplanar spatial lines `d,e` do not intersect.
- `perpendicular_lines(d,e;P)`: spatial lines `d,e` intersect at `P` and form a right angle.
- `skew_lines(d,e)`: spatial lines `d,e` are non-coplanar and do not intersect.
- `line_parallel_to_plane(d,alpha)`: line `d` has no common point with plane `alpha` and is parallel to a line contained in `alpha`.
- `line_perpendicular_to_plane(d,alpha;H)`: line `d` meets plane `alpha` at `H` and is perpendicular to every line in `alpha` through `H`.
- `parallel_planes(alpha,beta)`: distinct planes `alpha,beta` have no common point.
- `perpendicular_planes(alpha,beta;d)`: planes `alpha,beta` meet in line `d` and form a right dihedral angle.
- `orthogonal_projection_on_plane(H,P,alpha)`: `H` lies on `alpha` and line `PH` is perpendicular to `alpha`.
- `distance_from_point_to_plane(P,alpha,h)`: `h` is the length of the perpendicular segment from `P` to `alpha`.
- `angle_between_line_and_plane(d,alpha,theta)`: `theta` is the smaller angle, from `0` to `90` degrees, between `d` and its orthogonal projection onto `alpha`.
- `dihedral_angle(alpha,d,beta,theta)`: `theta` is the angle between two half-planes of `alpha,beta` with common edge `d`.

Spatial predicates are not reducible to planar predicates. Never infer a spatial relation from its two-dimensional projection: projection can destroy incidence, angle, length, parallelism, and visibility.

## Coordinate Initialization Rules

1. If a circle is present, prefer its center `O=(0,0)`. If `AB` is a diameter, set `A=(r,0)` and `B=(-r,0)`.
2. For multiple points on a circle, one point may be fixed at `(r,0)` and the remaining points represented by variables. If two radii form a `90`-degree central angle, `(r,0)` and `(0,r)` may be used.
3. For a standalone triangle, fix one vertex at `(0,0)` and represent the remaining points with variables.
4. Use independent variables such as `(a,b)` and `(m,n)` for unknown coordinates. Compute every dependent point from stated constraints; do not introduce another free literal.

## Drawing Orientation and Readability

1. For a freely oriented triangle, construct the two lateral sides, the right-angle legs, or otherwise the two longest sides first. Place their common vertex at `(0,0)` and construct the longer side first, horizontally to `(a,0)`. Put the other endpoint above this starting side: `(0,b)` for a stated right angle, otherwise `(b*cos(theta),b*sin(theta))` for the included angle `theta` measured counterclockwise from the horizontal, or derive it from the given constraints. Join the outer endpoints as the base. Apply this only when it does not conflict with stated geometry.
2. For other named polygon cycles such as `ABCD`, preserve that cyclic order and choose its
otherwise-free posture with the first listed vertex at the upper-left, then place the
remaining vertices clockwise. A single global rotation, reflection, translation, and
positive scale of the diagram is allowed for this conventional
posture; never move one constrained point independently. A fixed angle, direction, or
caller instruction overrides this convention.
3. Do not let a segment, straight line, ray, circle, or label cross through or overlap a non-incident point when an equivalent readable layout has free space. Also avoid intersections between unrelated required strokes at unnamed points: a secant crossing an unrelated radius, median, or connector is a layout defect unless the problem requires that intersection. Permit crossings only when required by a hypothesis, conclusion, or necessary geometric consequence.
4. Keep point markers, labels, right-angle marks, angle arcs, and measurements separate. Move a label first; never distort a constrained point to resolve a collision.
5. Do not draw an unrequested side, diagonal, extension, circle, or auxiliary line. Use `[dashed]` only for a required auxiliary construction or a hidden spatial edge.
6. Preserve extent exactly: a segment is finite, a ray has one origin, a straight line extends in both directions, and an arc must use the stated minor or major branch.
7. Prefer a conventional textbook posture, balanced whitespace, and a scale at which every required relation is immediately legible.

## Named Carriers and Proof Claims

- Draw every named point, line, ray, segment, circle, and auxiliary carrier that
  is needed to state the construction or the claim to be proved. A carrier does
  not become optional merely because a relation about it is a conclusion.
- Do not pre-assert a relation that is only to be proved. For example, draw a
  named circumcircle and a named candidate tangent, but do not add a relation
  mark unless that relation is a given or a construction.

## Stable TikZ Authoring Convention

Use [new_instruction.md](new_instruction.md) as the canonical authoring instruction,
mirrored in the harness's shared TIKZ_INSTRUCTION. It owns source structure,
display scale, dependent-coordinate recipes, point/label placement and relation marks.
This document supplies mathematical definitions and geometric constraints.
