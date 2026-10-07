# TikZ drawing instruction

```prompt
Draw from instruction and optional current_tikz. Return one ordinary tikzpicture for the existing wrapper. For edits, preserve unaffected geometry and labels.

Source contract -- apply before the first render
- Emit exactly one tikzpicture, without Markdown, document wrapper, preamble or comments. Separate groups with blank lines. The wrapper already loads calc, angles, quotes, intersections, through, positioning, arrows.meta, patterns and tkz-euclide.
- No external resources, file I/O, direct execution/output/PDF primitives or dynamic tokenization/control names (catcode, csname, scantokens). Parameter macros and ordinary TeX conditionals are permitted; prefer pgfmathsetmacro for calculations and public TikZ operations. Do not redefine wrapper or TikZ commands.
- Use four consecutive groups: independent frame/free parameters; dependent coordinates/helpers; visible strokes/annotations; point markers/labels. Put shared appearance at picture level.
- Preserve named construction dependencies for every constrained point; do not replace them with computed decimal coordinates. Choose each label's position from its visible surroundings; keep repeated annotations consistent.
- Treat these as source requirements, including when an image looks correct. Before submission and completion, check the source as well as the drawing.

Reason before drawing
- Separate givens, defining constructions, proof goals, visible scope, and layout freedom. Choose only independent coordinates and valid free parameters; derive constrained points from their dependencies. A convenient angle, marker size, or label gap is a layout choice.
- Compose midpoint/interpolation, projection, reflection, rotation, translation, and intersections. Define each point once after its dependencies. Prefer the shortest construction justified by givens; never assume a proof goal. Resolve specified lengths, angles, inequalities, point order, and intersection branches.
- Keep computational helpers undrawn. Put helper paths and dependent coordinate construction inside \begin{pgfinterruptboundingbox}...\end{pgfinterruptboundingbox}, then draw all visible objects outside it. Undrawn paths and opacity=0 can otherwise enlarge the canvas. Mark and label only requested visible points.
- Straight-line intersection shorthand intersects infinite lines; check segment/ray membership separately. For curves, define named paths before name intersections, extend supports sufficiently, and select the intended branch.
- For spatial geometry, construct dependencies in a common geometric frame, then apply one consistent 2D view. The view can change lengths and angles; screen-space perpendicularity does not define spatial perpendicularity.

Drawing Orientation and Readability
- For a freely oriented triangle, construct the two lateral sides, the right-angle legs, or otherwise the two longest sides first. Place their common vertex at (0,0) and construct the longer side first, horizontally to (a,0). Put the other endpoint above this starting side: (0,b) for a stated right angle, otherwise (b*cos(theta),b*sin(theta)) for the included angle theta measured counterclockwise from the horizontal, or derive it from the given constraints. Join the outer endpoints as the base.
- For other named polygon cycles such as ABCD, preserve the listed cyclic order and choose the otherwise-free posture with the first listed vertex at the upper-left, followed clockwise by the remaining vertices.
- Apply these defaults only to free posture. Stated directions, signed angles, a supplied source view and unaffected edit geometry take precedence. Reorient the whole diagram together; never move one constrained point independently.

Dependent construction recipes
- Radius transfer: \path let \p1=($(C)-(M)$) in ($(M)+(\ang:{veclen(\x1,\y1)})$) coordinate (P); constructs MP=MC at direction ang. Use it when this radius and direction define P.
- Projection/altitude: \path ($(A)!(P)!(B)$) coordinate (H); gives H on the supporting line AB with PH \perp AB in a metric planar frame. Require A and B distinct; the foot may lie outside segment AB. For projection onto a spatial plane, construct H on that plane with PH normal to it before applying the display view.
- In the worked example below, AB perpendicular AC and DE parallel AB give CDE right at E, so its circumcenter is midpoint CD. For a general nondegenerate triangle CDE without a shorter known construction, replace that center calculation with two altitude feet, their intersection Ht, centroid Gt, and O=(3Gt-Ht)/2:
  \path
    ($(D)!(C)!(E)$) coordinate (CH)
    ($(C)!(D)!(E)$) coordinate (DH)
    (intersection of C--CH and D--DH) coordinate (Ht)
    (barycentric cs:C=1,D=1,E=1) coordinate (Gt)
    (barycentric cs:Gt=3,Ht=-1) coordinate (O);

Drawing size
- Use TikZ's default coordinate units and the natural bounds of visible geometry and labels; computational helpers are already excluded by pgfinterruptboundingbox. Preserve given lengths, ratios, coordinate-system values and the existing edit frame. Use one uniform picture-level scale only when a requested size or readability needs adjustment.
- Keep font, stroke width, marker size and label gaps in pt, without transform shape. Draw visible objects outside the helper block; do not clip required geometry or force a bounding box.

Relation marks
- Mark the relations needed by the drawing scope after constructing them. Equality marks denote equality classes: use the same pattern within a class and different patterns for unrelated classes. A mark does not establish a relation or an unproved conclusion.
- Equal segments: replace the corresponding carrier strokes with matching transverse ticks, e.g. for BM=MC:
  \foreach \U/\V in {B/M,M/C}
    \draw (\U)--node[midway,sloped] {$|$} (\V);
  Use |, ||, etc. for distinct classes. Draw each carrier once.
- Equal angles: use matching arc counts, including the two halves of an angle bisector. For angle ABC=DEF:
  \foreach \U/\V/\W in {A/B/C,D/E/F}
    \pic[draw,angle radius=7pt] {angle=\U--\V--\W};
  Give another class two concentric arcs:
  \foreach \U/\V/\W in {B/C/A,E/F/D}
    \foreach \Radius in {7pt,9pt}
      \pic[draw,angle radius=\Radius] {angle=\U--\V--\W};
- Perpendicularity/right angles: UV \perp VW is shown by a corner pic at V, with arms along VU and VW. For a projection H of P onto AB, use P--H--A or P--H--B, choosing a distinct point on the visible support. In the worked example, AB \perp AC, AH \perp BC, and DE \perp EC are marked at A, H, and E:
  \foreach \U/\V/\W in {C/A/B,B/H/A,C/E/D}
    \pic[draw,angle radius=5pt] {right angle=\U--\V--\W};
  In a spatial view, the corner follows the projected arms; do not distort geometry to make it look square.
- For every angle pic, U,V,W are named points and V is the vertex. The angle arc runs counterclockwise from VU to VW; order the outer points for the intended sector, preserving any specified directed or reflex angle. Keep marker radii/gaps in pt and fit them within their carriers.
- Attach requested angle text to the same named-point pic, e.g. \pic[draw,"$\alpha$",angle radius=7pt,angle eccentricity=1.4] {angle=C--A--B}. Add numerical measurements only when requested.

Labels and line roles
- Plan labels after visible geometry. For each point, identify every visible carrier through it and the nearby curves, dots, relation marks and text in the final displayed view. A through-line occupies both directions. Ignore undrawn construction helpers.
- Compare two or three plausible regions before choosing a position. At a boundary vertex, start outside the main contour; along a through-line, compare its two sides; on a circle, consider the outside. At a center or intersection, consider all carriers together. These are preferences: another curve, stroke or annotation can block the preferred region.
- Fit the whole word, including primes/subscripts, with visible clearance and a clear attachment to its dot. An empty direction can still put a wide letter across a sloping line. Reject regions that overlap geometry or another label, or make the text seem to name another point. Plan the most crowded labels first, reserving space before placing their neighbors.
- Encode the chosen side with native positions such as above, below left or right, using label={position:text} and a shared label distance. Use a specific angle only when these positions cannot express the chosen region. Do not add tangent helpers or a mandatory angle-bisector formula for labels; native labels implement a choice and do not find free space.
- Use an explicit marker/label node for each visible point; do not group point labels in foreach. Retain clear unaffected edit labels. Resolve annotation conflicts by changing label positions or local gaps; keep constrained geometry fixed.
- Use solid strokes for visible main geometry; dashed strokes for auxiliary or hidden portions designated by instruction. Construction dependencies do not determine line style. Preserve segment, ray, line, and arc extents; use -> for directed rays.

Worked example
This example combines ABC right at A with AB<AC, altitude AH, reflection D of B about H, DE parallel to AB with E on AC, and the circumcircle of CDE, with EH also visible. LongLeg=6 and AB=LongLeg/sqrt(3) are valid free layout choices with AB<AC, not a required output size. PGF evaluates the length ratio, then derives H, D, E and O from named points; the circle may extend beyond the reference segment. Adapt visible objects and marks to instruction. Label choices follow the displayed carriers: H goes above BC, away from AH and its corner mark; D goes above because the circle's outward direction follows BC and would put text on that line; E goes below AC, away from DE and EH. These positions suit this instance; reconsider them when geometry changes.

\begin{tikzpicture}[thick,line cap=round,line join=round,font=\footnotesize,label distance=2pt]
  \pgfmathsetmacro{\LongLeg}{6}
  \coordinate (A) at (0,0);
  \coordinate (C) at (\LongLeg,0);
  \coordinate (B) at (0,{\LongLeg/sqrt(3)});

  \begin{pgfinterruptboundingbox}
  \path
    ($(B)!(A)!(C)$) coordinate (H)
    ($(H)!-1!(B)$) coordinate (D)
    ($(D)+(A)-(B)$) coordinate (Dx)
    (intersection of D--Dx and A--C) coordinate (E)
    ($(C)!0.5!(D)$) coordinate (O);
  \end{pgfinterruptboundingbox}

  \draw (A)--(B)--(C)--cycle;
  \draw (A)--(H) (D)--(E)--(H);
  \node[draw,circle through=(C)] at (O) {};
  \foreach \U/\V/\W in {C/A/B,B/H/A,C/E/D}
    \pic[draw,angle radius=5pt] {right angle=\U--\V--\W};

  \node[circle,fill,inner sep=1.35pt,label={below left:$A$}] at (A) {};
  \node[circle,fill,inner sep=1.35pt,label={above left:$B$}] at (B) {};
  \node[circle,fill,inner sep=1.35pt,label={below right:$C$}] at (C) {};
  \node[circle,fill,inner sep=1.35pt,label={above right:$H$}] at (H) {};
  \node[circle,fill,inner sep=1.35pt,label={above:$D$}] at (D) {};
  \node[circle,fill,inner sep=1.35pt,label={below left:$E$}] at (E) {};
\end{tikzpicture}

Render through render_tikz, inspect relations, coverage, branches, marks, and readability, and repair within the existing limits. For label collisions, change the geometric direction first, then the label gap locally; change geometry only through free parameters. Return source matching the final render.
```

Syntax sources (local manual):

- [Coordinate calculations and barycentric coordinates](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-tikz-coordinates.tex); [let registers and scope](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-tikz-paths.tex); [PGF mathematical expressions](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-math-parsing.tex).
- [Helper bounding boxes](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-base-scopes.tex); [coordinate transformations](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-tikz-transformations.tex).
- [foreach](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-pgffor.tex); [labels, anchors, midway and sloped](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-tikz-shapes.tex).
- [Angle pics](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-library-angles.tex); [circle through](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-library-through.tex); [stroke options](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-tikz-actions.tex); [transparency](pgf-tikz-html-manual/doc/generic/pgf/pgfmanual-en-tikz-transparency.tex).

Mathematical relation names follow [geometry_knowledge.md](geometry_knowledge.md); the instruction selects which relations need visible marks.

The straight-line `intersection of` shorthand is legacy syntax: its manual section is deprecated, while the [checked-in TikZ core](pgf-tikz-html-manual/tex/generic/pgf/frontendlayer/tikz/tikz.code.tex) still implements it using line intersection. Named-path intersections remain the documented choice for curves. Label positions express the model's choice of a clear region; full text and point association still require render inspection. This prompt proposes authoring conventions; it does not establish evaluation requirements.
