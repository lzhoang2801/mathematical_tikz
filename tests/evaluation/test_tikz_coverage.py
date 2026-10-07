"""Point/connection coverage is independent of target proportions and label text."""
import pytest
from shapely.geometry import LineString

from evaluation.tikz_coverage import compare_content


def scene(points, edges):
    return {"points": points, "strokes": [
        {"path": i, "geometry": LineString(edge[:2]), "components": [LineString(edge[:2])],
         "dashed": edge[2] if len(edge) == 3 else False, "width": 1}
        for i, edge in enumerate(edges)
    ], "unsupported": []}


def triangle(points):
    return scene(points, [(points[a], points[b]) for a, b in (("A", "B"), ("B", "C"), ("C", "A"))])


def test_valid_different_shapes_keep_the_same_point_connections():
    target = triangle({"A": (0, 0), "B": (100, 0), "C": (0, 60)})
    output = triangle({"A": (20, 20), "B": (170, 20), "C": (70, 90)})
    assert compare_content(target, output)["status"] == "match"


def test_incidental_target_collinearity_does_not_add_a_requirement():
    target = scene({"A": (0, 0), "B": (100, 0), "C": (50, 0)}, [((0, 0), (100, 0))])
    output = scene({"A": (0, 0), "B": (100, 0), "C": (50, 90)}, [((0, 0), (100, 0))])
    result = compare_content(target, output)
    assert result["status"] == "match"
    assert len(result["checks"]["connections"]["requirements"]) == 1


@pytest.mark.parametrize("mutation", ["missing", "extra", "dash"])
def test_missing_extra_and_wrong_style_connections_fail(mutation):
    points = {"A": (0, 0), "B": (100, 0), "C": (50, 80), "D": (150, 80)}
    edges = [(points["A"], points["B"]), (points["B"], points["C"])]
    changed = list(edges)
    if mutation == "missing":
        changed.pop()
    elif mutation == "extra":
        changed.append((points["C"], points["D"]))
    else:
        changed[0] = (*changed[0], True)
    assert compare_content(scene(points, edges), scene(points, changed))["status"] == "different"


def test_split_or_repeated_lines_do_not_change_coverage():
    points = {"A": (0, 0), "B": (100, 0)}
    target = scene(points, [((0, 0), (100, 0))])
    output = scene(points, [((0, 0), (50, 0)), ((50, 0), (100, 0)), ((0, 0), (50, 0))])
    assert compare_content(target, output)["status"] == "match"


def test_short_required_edge_cannot_disappear_in_a_global_average():
    points = {"A": (0, 0), "B": (100, 0), "C": (0, 10), "D": (0.1, 10)}
    target = scene(points, [((0, 0), (100, 0)), ((0, 10), (0.1, 10))])
    output = scene(points, [((0, 0), (100, 0))])
    assert compare_content(target, output)["status"] == "different"


def test_nonpoint_text_rules_do_not_create_geometry_requirements():
    points = {"A": (0, 0), "B": (100, 0)}
    target = scene(points, [((0, 0), (100, 0)), ((40, 30), (45, 30))])
    output = scene(points, [((0, 0), (100, 0))])
    assert compare_content(target, output)["status"] == "match"


def test_missing_extra_and_unresolved_point_identities_are_distinct():
    target = triangle({"A": (0, 0), "B": (100, 0), "C": (50, 80)})
    output = triangle({"A": (0, 0), "B": (100, 0), "C": (50, 80)})
    output["points"]["C"] = None
    assert compare_content(target, output)["status"] == "unknown"
    output["points"].pop("C")
    assert compare_content(target, output)["checks"]["points"]["missing"] == ["C"]
    output["points"]["D"] = (50, 80)
    assert compare_content(target, output)["checks"]["points"]["extra"] == ["D"]


@pytest.mark.parametrize("requirement", [
    {"kind": "ellipse", "points": ["A", "B"]},
    {"kind": ["circle"], "points": ["A", "B"]},
    {"kind": "circle", "points": ["A"]},
    {"kind": "segment", "points": ["A"]},
    {"kind": "segment", "points": ["A", "B"], "dashed": "false"},
])
def test_unsupported_contracts_stay_unknown(requirement):
    drawing = scene({"A": (0, 0), "B": (100, 0)}, [((0, 0), (100, 0))])
    result = compare_content(drawing, drawing, content_requirements=[
        {"kind": "point", "points": ["A"]}, {"kind": "point", "points": ["B"]}, requirement,
    ])
    assert result["status"] == "unknown"
