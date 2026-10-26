"""Calibration for painted relation marks and their named carriers."""
from __future__ import annotations

import math

import pytest
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from evaluation.requirements import Relation, Requirements, check_scene
from evaluation.tikz_coverage import compare_content, connections
from evaluation.tikz_geometry import compare_geometry
from evaluation.tikz_marks import compare_mark_content, observe_marks


def _transform(points, *, scale=1.0, angle=0.0, reflect=False):
    cosine, sine = math.cos(angle), math.sin(angle)
    return {
        name: (
            9 + scale * (cosine * (-x if reflect else x) - sine * y),
            -6 + scale * (sine * (-x if reflect else x) + cosine * y),
        )
        for name, (x, y) in points.items()
    }


def _scene(points, edges, *, ticks=None, vector_ticks=None, corners=(),
           parallel_glyphs=False, collapsed_corners=(), font=1.0):
    """Construct native-observation-like Shapely evidence, without parsing helpers."""
    strokes = []

    def add_path(parts, *, width=0.025):
        strokes.append({
            "geometry": unary_union(parts), "components": parts,
            "width": width, "dashed": False,
        })

    for first, second in edges:
        add_path([LineString([points[first], points[second]])])

    text = []
    for name, point in points.items():
        x, y = point
        text.append({"text": name, "size": font, "bbox": [x - .2, y - .2, x + .2, y + .2], "glyphs": []})

    # Native text boxes retain the vertical axis used to attach bar marks.
    # is perpendicular to the carrier; the adversarial variant is parallel.
    for names, count in (ticks or {}).items():
        a, b = (points[name] for name in names)
        direction = (b[0] - a[0], b[1] - a[1])
        length = math.hypot(*direction)
        tangent = (direction[0] / length, direction[1] / length)
        normal = (-tangent[1], tangent[0])
        long_axis, short_axis = (tangent, normal) if parallel_glyphs else (normal, tangent)
        center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        boxes = []
        for index in range(count):
            offset = (index - (count - 1) / 2) * .12 * font
            cx, cy = center[0] + offset * tangent[0], center[1] + offset * tangent[1]
            corners_xy = []
            for long_sign, short_sign in ((-1, -1), (-1, 1), (1, 1), (1, -1)):
                corners_xy.append((
                    cx + long_sign * .25 * font * long_axis[0] + short_sign * .035 * font * short_axis[0],
                    cy + long_sign * .25 * font * long_axis[1] + short_sign * .035 * font * short_axis[1],
                ))
            boxes.append({"corners": [corners_xy[j] for j in (2,3,1,0)]})
        ink = unary_union([Polygon([box["corners"][j] for j in (0,1,3,2)]) for box in boxes])
        text.append({"text": "|" * count, "size": font, "bbox": list(ink.bounds), "boxes": boxes, "region": ink})

    # Vector ticks are ordinary, short, drawn Shapely strokes crossing a
    # carrier. They must be observed like bar glyphs, independent of encoding.
    for names, count in (vector_ticks or {}).items():
        a, b = (points[name] for name in names)
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        normal = (-dy / length, dx / length)
        tangent = (dx / length, dy / length)
        center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        for index in range(count):
            offset = (index - (count - 1) / 2) * .12 * font
            cx, cy = center[0] + offset * tangent[0], center[1] + offset * tangent[1]
            part = LineString([
                (cx - .25 * font * normal[0], cy - .25 * font * normal[1]),
                (cx + .25 * font * normal[0], cy + .25 * font * normal[1]),
            ])
            add_path([part])

    for first, vertex, second in corners:
        origin = points[vertex]
        ends = [
            (origin[0] + .1 * (points[name][0] - origin[0]),
             origin[1] + .1 * (points[name][1] - origin[1]))
            for name in (first, second)
        ]
        bend = (ends[0][0] + ends[1][0] - origin[0], ends[0][1] + ends[1][1] - origin[1])
        add_path([LineString([ends[0], bend]), LineString([bend, ends[1]])])

    for first, vertex, second in collapsed_corners:
        origin = points[vertex]
        direction = (points[second][0] - origin[0], points[second][1] - origin[1])
        length = math.hypot(*direction)
        unit = (direction[0] / length, direction[1] / length)
        start = (origin[0] - .4 * unit[0], origin[1] - .4 * unit[1])
        bend = (origin[0] - .2 * unit[0], origin[1] - .2 * unit[1])
        end = origin
        add_path([LineString([start, bend]), LineString([bend, end])])

    return {
        "points": dict(points), "strokes": strokes, "text": text,
        "circles": [], "arcs": [], "curves": [],
        "unsupported": [], "unresolved": [], "bounds": [-40, -40, 60, 60], "paint_issues": [], "paint": [],
    }


def _equal_pair_scene(*, ticks=True, vector=False, swapped=False, transform=False):
    points = {
        "A": (0, 0), "B": (4, 0), "C": (0, 5), "D": (4, 5),
        "E": (0, 10), "F": (7, 10), "G": (0, 16), "H": (7, 16),
    }
    if transform:
        points = _transform(points, scale=1.7, angle=.61, reflect=True)
    first, second = ({"AB": 1, "CD": 1}, {"EF": 2, "GH": 2})
    if swapped:
        first, second = ({"AB": 2, "CD": 2}, {"EF": 1, "GH": 1})
    glyphs = {**first, **second} if ticks and not vector else None
    vectors = {**first, **second} if ticks and vector else None
    return _scene(points, [("A", "B"), ("C", "D"), ("E", "F"), ("G", "H")],
                  ticks=glyphs, vector_ticks=vectors, font=1.7 if transform else 1.0)


def test_missing_ticks_loses_content_but_does_not_change_geometric_truth():
    target = _equal_pair_scene()
    output = _equal_pair_scene(ticks=False)

    math_checks, matches = compare_geometry(target, output)
    content_checks = compare_content(target, output, matches)

    assert all(math_checks)
    assert content_checks.count(False) == 2  # One missing mark for each required class.


def test_tick_classes_survive_similarity_and_tick_id_renumbering():
    target = _equal_pair_scene()
    output = _equal_pair_scene(vector=True, swapped=True, transform=True)
    expected = observe_marks(target, connections(target))
    actual = observe_marks(output, connections(output))

    assert not expected["unresolved"] and not actual["unresolved"]
    assert all(compare_geometry(target, output)[0])
    assert all(compare_mark_content(expected, actual, output["points"]))


def test_centered_tick_binds_to_full_segment_when_intermediate_points_subdivide_it():
    points = {"A": (0, 0), "E": (4, 0), "K": (7, 0), "C": (10, 0),
              "B": (0, 5), "D": (10, 5)}
    picture = _scene(points, [("A", "C"), ("B", "D")], vector_ticks={"AC": 1, "BD": 1})

    marks = observe_marks(picture, connections(picture))

    assert not marks["unresolved"]
    assert marks["equal_segments"] == [{("A", "C"), ("B", "D")}]


def test_corner_leg_crossing_carrier_at_numeric_endpoint_noise_is_not_a_tick():
    points = {"A": (-10, 0), "V": (0, 0), "B": (0, 10)}
    picture = _scene(points, [("A", "V"), ("V", "B")])
    parts = [
        LineString([(-.2, -1e-6), (-.2, .2)]),
        LineString([(-.2, .2), (0, .2)]),
    ]
    picture["strokes"].append({"geometry": unary_union(parts), "components": parts,
                               "width": .025, "dashed": False})

    marks = observe_marks(picture, connections(picture))

    assert ("A", "V", "B") in marks["right_angles"]
    assert not marks["equal_segments"]


def test_ticks_on_three_equal_subsegments_do_not_mark_the_containing_side():
    points = {"A": (0, 0), "D": (3, 0), "E": (6, 0), "B": (9, 0)}
    picture = _scene(points, [("A", "B")], ticks={"AD": 1, "DE": 1, "EB": 1})

    marks = observe_marks(picture, connections(picture))

    assert not marks["unresolved"]
    assert marks["equal_segments"] == [{("A", "D"), ("D", "E"), ("B", "E")}]


def test_oblique_corner_legs_crossing_diagonals_are_not_equality_ticks():
    points = {"A": (0, 0), "B": (100, 10), "D": (25, 50),
              "A'": (-15, 85), "C": (125, 60), "D'": (10, 135)}
    picture = _scene(points, [("A", "B"), ("A", "D"), ("A", "A'"), ("A", "C"), ("A", "D'")],
                     ticks={"AB": 1, "AD": 1, ("A", "A'"): 1},
                     corners=[("B", "A", "D"), ("B", "A", "A'"), ("D", "A", "A'")], font=10)

    marks = observe_marks(picture, connections(picture))

    assert len(marks["right_angles"]) == 3
    assert marks["equal_segments"] == [{("A", "B"), ("A", "D"), ("A", "A'")}]
    assert not marks["unresolved"]


@pytest.mark.parametrize("mutation", ["wrong_carrier", "parallel_glyph", "ambiguous_carrier"])
def test_tick_evidence_must_bind_to_one_correctly_oriented_named_carrier(mutation):
    if mutation == "ambiguous_carrier":
        points = {"A": (0, 0), "B": (4, 0), "C": (0, 0), "D": (4, 0)}
        picture = _scene(points, [("A", "B"), ("C", "D")], ticks={"AB": 1})
        assert observe_marks(picture, connections(picture))["unresolved"]
        return

    target = _equal_pair_scene()
    if mutation == "wrong_carrier":
        output = _scene(target["points"], [("A", "B"), ("C", "D"), ("E", "F"), ("G", "H")],
                        ticks={"AB": 1, "EF": 1})
    else:
        output = _scene(target["points"], [("A", "B"), ("C", "D"), ("E", "F"), ("G", "H")],
                        ticks={"AB": 1, "CD": 1}, parallel_glyphs=True)

    checks = compare_content(target, output, compare_geometry(target, output)[1])
    assert not all(checks)


def test_false_equal_length_and_oblique_corner_marks_fail_requirements():
    points = {"A": (0, 0), "B": (4, 0), "C": (0, 5), "D": (5, 5),
              "X": (-4, 10), "V": (0, 10), "Y": (2, 13.464)}
    picture = _scene(points, [("A", "B"), ("C", "D"), ("V", "X"), ("V", "Y")],
                     ticks={"AB": 1, "CD": 1}, corners=[("X", "V", "Y")])
    requirements = Requirements(
        points=list(points),
        relations=[
            Relation(id="equal", kind="equal_length", points=["A", "B", "C", "D"]),
            Relation(id="right", kind="angle", points=["X", "V", "Y"], value=90),
        ],
        right_angles=[("X", "V", "Y")],
        equal_segments=[[('A', 'B'), ('C', 'D')]],
    )
    checks = check_scene(requirements, picture)["checks"]
    indexed = {row["id"]: row["status"] for row in checks}

    assert indexed["equality:A-B:C-D"] == "fail"
    assert indexed["equality_mark:A-B"] == "pass"  # Painted marks do not prove their truth.
    assert indexed["right_angle:X-V-Y"] == "fail"
    assert indexed["mark_truth:0"] == "fail"
    assert indexed["mark_truth:1"] == "fail"


@pytest.mark.parametrize("collapsed", [False, True])
def test_missing_or_collapsed_right_angle_marker_loses_content(collapsed):
    points = {"A": (-4, 0), "V": (0, 0), "B": (0, 4)}
    target = _scene(points, [("A", "V"), ("V", "B")], corners=[("A", "V", "B")])
    output = _scene(points, [("A", "V"), ("V", "B")],
                    collapsed_corners=[("A", "V", "B")] if collapsed else ())

    math_checks, matches = compare_geometry(target, output)
    content_checks = compare_content(target, output, matches)

    assert all(math_checks)
    assert not all(content_checks)
    observed = observe_marks(output, connections(output))
    assert not observed["right_angles"]
