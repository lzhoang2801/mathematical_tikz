# Mathematical diagrams in geometry

A mathematical geometry diagram represents geometric objects and the relationships that define a configuration. Points, lines, circles, polygons, planes and solids are connected by incidence, order, parallelism, perpendicularity, tangency, metric relations and constructions. Labels, line styles and relation marks make that configuration readable.

This project works with geometry in grades 6–12. Its diagrams cover plane geometry, vectors and coordinate geometry, transformations, and spatial geometry. The [task contract](<K-12 Mathematical Diagrams with TikZ.md#task-inputs>) defines the inputs and outputs for Generate, Edit and Reconstruct.

## Geometry taxonomy

This taxonomy summarizes the geometric configurations considered during initial source preparation. Its codes serve as reference labels within this overview of the input corpus.

| Code | Geometry family | Objects and relationships |
| --- | --- | --- |
| G01 | Points, lines, segments and curves | Named points, collinearity, intersections, order and midpoint relations. |
| G02 | Rays and angles | Ray origins and directions, angle sectors, bisectors and angle measures. |
| G03 | Triangles and associated constructions | Altitudes, medians, bisectors, perpendicular bisectors and their intersections. |
| G04 | Congruent triangles | Vertex correspondence, equal segments, equal angles and right-triangle configurations. |
| G05 | Similar triangles and Thales configurations | Parallel transversals, corresponding vertices, segment ratios and homothety relations. |
| G06 | Metric relations in right triangles | Altitude projections, Pythagorean relations, trigonometric ratios and geometric lengths. |
| G07 | Quadrilaterals | Side and diagonal relations in squares, rectangles, parallelograms, rhombi and trapezoids. |
| G08 | Regular polygons | Equal sides and angles, centers, symmetry axes and associated circles. |
| G09 | Circles and circle constructions | Centers, radii, diameters, chords, arcs and point positions relative to a circle. |
| G10 | Circle angles and cyclic quadrilaterals | Central and inscribed angles, intercepted arcs and concyclic vertices. |
| G11 | Tangency and line–circle configurations | Contact points, tangent radii, secants and specified intersection branches. |
| G12 | Vectors | Directed segments, equal vectors, vector sums and triangle/parallelogram constructions. |
| G13 | Plane coordinate geometry | Coordinate axes, points, lines, circles and conics with their geometric defining objects. |
| G14 | Plane transformations | Translation, reflection, rotation and homothety with corresponding objects. |
| G15 | Polyhedra and solids of revolution | Prisms, pyramids, cylinders, cones, spheres, bases, axes and sections. |
| G16 | Spatial geometry | Points, lines, planes, sections, projections and spatial incidence, angle and distance relations. |
| G17 | Spatial coordinate geometry | Oxyz axes, vectors, points, lines, planes, spheres and coordinate projections. |

Spatial diagrams use solid and dashed strokes to show visibility in the chosen projection. Construction constraints belong to the spatial configuration; the projected drawing must represent those objects consistently.

## Mathematical content

Preparing a diagram requires three decisions:

| Component | Purpose |
| --- | --- |
| Source facts | Establish the premises, named objects, construction definitions and branch conditions. |
| Construction constraints | Determine where dependent objects lie and which geometric relationships must hold. |
| Visible information | Communicate the requested configuration through geometry, labels, strokes, marks and measurements. |

A relation may be communicated by the configuration itself. A mark records a relation visibly; its placement must agree with the geometry. For example, an altitude foot must lie on its defining carrier and produce perpendicular lines, while an angle mark must identify the intended angle.

Generate uses a complete configuration and its requested constructions. Edit uses the actual starting diagram and a defined change, retaining unaffected objects and relationships. Reconstruct reproduces the geometry visible in its input image. Task inputs and message roles follow the [canonical contract](<K-12 Mathematical Diagrams with TikZ.md#task-inputs>).

## Givens and auxiliary constructions

Separate original givens, definitions of new objects and conclusions to be proved. Dependent points are constructed from their parents and defining carriers. Record segment, ray or supporting-line distinctions and the branch of an intersection.

Useful auxiliary geometry exposes a relationship in the configuration: an altitude, a median, a parallel through a point, a reflection, a tangent radius, a section or a projection. Its role comes from a later problem part, a checked solution construction or a deliberate synthetic addition.

Instruction variety comes from different compatible configurations and purposeful constructions. Related Generate/Edit targets may share a diagram and original source problem while retaining their own task inputs.

## Source preparation

The processed curriculum corpus is located at `C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums`.

| Grades | Source artifacts |
| --- | --- |
| 6–9 | `book.final.md`, `layout.final.json`, `toc.final.json` and adjacent `images/`. |
| 10–12 | `full.md`, `layout.json` and adjacent `images/`. |

A source unit is a complete example, practice problem or exercise, including subparts that define constructions. The source ledger stores its original text and a file/line/page locator. Each dataset candidate keeps only a source reference so that its original problem can be recovered and related samples can share one split. Figure-dependent facts require the cited diagram.

The current authoring pool is [selection.jsonl](../dataset/audit_givens/selection.jsonl). Source manifests under [dataset-selection/](dataset-selection/) preserve corpus records and their audit decisions. The source inventory is [dataset-selection.json](dataset-selection.json); [prepare_dataset_selection.py](../tools/prepare_dataset_selection.py) checks its source locations.

Dataset production, review, checkpoint recovery and export follow [dataset conventions](../dataset/CONVENTIONS.md). Related source problems and diagram variants keep a shared split assignment.

## Review and evaluation

Review the input and target as a pair: source/configuration fidelity, defining geometric relations, required visible content and readable layout. A reviewed pair preserves the exact target code and its verified render.

The four evaluation dimensions are compilation, mathematical correctness, content coverage and visual readability. Executable checks measure supported observed geometry; independent source review establishes alignment with the task input. The implemented scoring boundary and supported observations are documented in [evaluation.md](evaluation.md).

Information-selection studies can compare accepted representations by removing a label, mark or auxiliary while retaining the geometric configuration. Record which relationship becomes ambiguous or unavailable to the reader, and distinguish these changes from changes that make the geometry false.

Source refresh commands and corpus-preservation rules are recorded in [AGENTS.md](../AGENTS.md).
