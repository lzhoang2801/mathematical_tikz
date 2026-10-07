"""Observable PDF regressions, independent of live compiler/model services."""
from pathlib import Path

import pymupdf
import pytest

from evaluation.evaluator import evaluate


def diagram(path: Path, *, scale: float = 1, missing_edge: bool = False, wrong_text: bool = False, stretch: float = 1, rotation: bool = False, reflection: bool = False, markers: bool = True, label_shift: float = 0, collide: bool = False, coordinates=None) -> dict:
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=250 * scale, height=180 * scale)
        coords = coordinates if coordinates is not None else [(30, 100), (130, 100), (60, 30)]
        if rotation:
            coords = [(180 - y, x) for x, y in coords]
        if reflection:
            coords = [(180 - x, y) for x, y in coords]
        points = [pymupdf.Point(x * scale * stretch, y * scale) for x, y in coords]
        for i, (a, b) in enumerate(zip(points, points[1:] + points[:1])):
            if not missing_edge or i != 1:
                page.draw_line(a, b, color=(0, 0, 0), width=scale)
        for label, p in zip("ABC", points):
            if markers:
                page.draw_circle(p, 1.5 * scale, color=(0, 0, 0), fill=(0, 0, 0))
            position = points[0] if collide and label == "B" else p
            dx, dy = (0, -10 if label == "C" else 14)
            if rotation:
                dx, dy = (5, 0) if label == "C" else (-12, 0)
            page.insert_text((position.x + dx * scale + label_shift, position.y + dy * scale), label, fontsize=8 * scale)
        page.insert_text((30 * scale, 160 * scale), "8 cm" if wrong_text else "6 cm", fontsize=8 * scale)
        pdf.save(path)
    return {"compile_success": True, "pdf_path": str(path), "labeled_points": {
        label: {"status": "measured", "pdf_x": p.x, "pdf_y": p.y, "evidence_id": "constructed-pdf-fixture"}
        for label, p in zip("ABC", points)
    }}



def rubric(*checks):
    return [{"id": "givens", "dimension": "mathematical_correctness", "checks": list(checks)}]


RIGHT_TRIANGLE = rubric(
    {"op": "perpendicular", "points": ["A", "B", "A", "C"]},
    {"op": "shorter", "points": ["A", "C", "A", "B"]},
)


@pytest.mark.parametrize("options,readability", [
    ({"scale": 1.7}, "match"), ({"reflection": True}, "match"), ({"rotation": True}, "match"),
    ({"rotation": True, "reflection": True}, "review"),
    ({"label_shift": 4}, "match"), ({"markers": False}, "match"),
    ({"coordinates": [(30, 100), (160, 100), (30, 60)]}, "match"),
])
def test_same_givens_accept_similarity_and_non_similar_drawings(tmp_path, options, readability):
    target = diagram(tmp_path / "target.pdf", coordinates=[(30, 100), (130, 100), (30, 30)])
    options = {"coordinates": [(30, 100), (130, 100), (30, 30)], **options}
    output = diagram(tmp_path / "output.pdf", **options)
    result = evaluate(target, output, evaluation_rubric=RIGHT_TRIANGLE)
    assert result["scores"]["compile"] == 1
    assert result["scores"]["mathematical_correctness"] == 100
    assert result["scores"]["content_coverage"] == 100
    assert (result["scores"]["visual_readability"] == 100) == (readability == "match")
    assert not {"status", "dimensions", "metrics", "meaning", "policy", "requirements", "content_structure"} & result.keys()


def test_text_values_do_not_supply_mathematical_or_content_requirements(tmp_path):
    target = diagram(tmp_path / "target.pdf", coordinates=[(30, 100), (130, 100), (30, 30)])
    output = diagram(tmp_path / "output.pdf", coordinates=[(30, 100), (130, 100), (30, 30)], wrong_text=True)
    result = evaluate(target, output, evaluation_rubric=RIGHT_TRIANGLE)
    assert result["scores"]["mathematical_correctness"] == 100
    assert result["scores"]["content_coverage"] == 100


def test_missing_connection_and_broken_givens_fail_independently(tmp_path):
    target = diagram(tmp_path / "target.pdf", coordinates=[(30, 100), (130, 100), (30, 30)])
    missing = diagram(tmp_path / "missing.pdf", coordinates=[(30, 100), (130, 100), (30, 30)], missing_edge=True)
    broken = diagram(tmp_path / "broken.pdf")
    first = evaluate(target, missing, evaluation_rubric=RIGHT_TRIANGLE)
    second = evaluate(target, broken, evaluation_rubric=RIGHT_TRIANGLE)
    assert first["scores"]["mathematical_correctness"] == 100
    assert first["scores"]["content_coverage"] < 100
    assert second["scores"]["mathematical_correctness"] < 100
    assert second["scores"]["content_coverage"] == 100


def test_a_target_error_cannot_become_an_output_requirement(tmp_path):
    target = diagram(tmp_path / "target.pdf")
    output = diagram(tmp_path / "output.pdf", coordinates=[(30, 100), (130, 100), (30, 30)])
    result = evaluate(target, output, evaluation_rubric=RIGHT_TRIANGLE)
    assert any(row["status"] == "fail" for row in result["checks"]["mathematical_correctness"]["target"])
    assert result["scores"]["mathematical_correctness"] == 100
    assert result["scores"]["mathematical_correctness"] == 100


def test_reference_identity_and_missing_checks_cannot_certify_mathematics(tmp_path):
    target = diagram(tmp_path / "target.pdf")
    for checks in (None, [], rubric()):
        result = evaluate(target, target, evaluation_rubric=checks)
        assert result["counts"]["mathematical_correctness"]["passed"] == 0
        assert result["scores"]["content_coverage"] == 100
        assert result["scores"]["mathematical_correctness"] == (0 if checks else None)


def test_readability_is_absolute_and_never_changes_the_point_givens(tmp_path):
    target = diagram(tmp_path / "target.pdf", collide=True)
    result = evaluate(target, target, evaluation_rubric=rubric({"op": "noncollinear", "points": ["A", "B", "C"]}))
    assert result["scores"]["mathematical_correctness"] == 100
    assert result["scores"]["content_coverage"] == 100
    assert result["scores"]["visual_readability"] < 100


def test_text_rules_are_not_geometric_connections_or_carrier_collisions(tmp_path):
    target = diagram(tmp_path / "target.pdf")
    with pymupdf.open(target["pdf_path"]) as pdf:
        pdf[0].draw_line((30, 157), (47, 157), color=(0, 0, 0))
        pdf.saveIncr()
    result = evaluate(target, target, evaluation_rubric=rubric({"op": "noncollinear", "points": ["A", "B", "C"]}))
    assert result["scores"]["content_coverage"] == 100
    assert result["scores"]["visual_readability"] == 100


def test_unresolved_point_bindings_remain_unknown(tmp_path):
    target = diagram(tmp_path / "target.pdf")
    output = diagram(tmp_path / "output.pdf")
    output["labeled_points"]["C"] = {"status": "unknown", "reason": "ambiguous_attachment"}
    result = evaluate(target, output, evaluation_rubric=RIGHT_TRIANGLE)
    assert result["counts"]["mathematical_correctness"]["passed"] == 0
    assert result["scores"]["content_coverage"] == 50
    assert result["counts"]["content_coverage"]["unresolved"] == 3


def test_unsupported_projected_metric_cannot_pass_from_screen_angles(tmp_path):
    target = diagram(tmp_path / "target.pdf", coordinates=[(30, 100), (130, 100), (30, 30)])
    result = evaluate(target, target, evaluation_rubric=RIGHT_TRIANGLE, geometry_space="affine_projection")
    assert result["counts"]["mathematical_correctness"]["unresolved"] == 2


def test_known_failure_dominates_unknown_predicates(tmp_path):
    target = diagram(tmp_path / "target.pdf")
    checks = rubric({"op": "perpendicular", "points": ["A", "B", "A", "C"]},
                    {"op": "unsupported", "points": ["A", "B"]})
    result = evaluate(target, target, evaluation_rubric=checks)
    assert result["scores"]["mathematical_correctness"] == 0
    assert result["scores"]["mathematical_correctness"] == 0


def test_infrastructure_and_compile_failures_have_different_denominators():
    unavailable = evaluate({}, {"compile_success": False, "compile": {"outcome": "unknown"}})
    failed = evaluate({}, {"compile_success": False, "compile": {"outcome": "validation_failed"}})
    assert unavailable["scores"]["compile"] is None
    assert failed["scores"]["compile"] == 0


def test_mathematical_requirements_are_independent_of_target_compilation(tmp_path):
    output = diagram(tmp_path / "output.pdf", coordinates=[(30, 100), (130, 100), (30, 30)])
    result = evaluate({}, output, evaluation_rubric=RIGHT_TRIANGLE)
    assert result["scores"]["mathematical_correctness"] == 100
    assert all(row["status"] == "unknown" for row in result["checks"]["mathematical_correctness"]["target"])


def test_invalid_rubric_is_rejected(tmp_path):
    target = diagram(tmp_path / "target.pdf")
    with pytest.raises(TypeError):
        evaluate(target, target, evaluation_rubric={})
    with pytest.raises(ValueError):
        evaluate(target, target, evaluation_rubric=RIGHT_TRIANGLE + RIGHT_TRIANGLE)


def test_a_ratio_from_the_givens_is_checked_even_when_numeric_labels_match(tmp_path):
    target = diagram(tmp_path / "target.pdf", coordinates=[(30, 100), (130, 100), (30, 30)])
    output = diagram(tmp_path / "output.pdf", coordinates=[(30, 100), (110, 100), (30, 30)])
    fixed = rubric({"op": "length_ratio", "points": ["A", "B", "A", "C"], "value": 10/7})
    result = evaluate(target, output, evaluation_rubric=fixed)
    assert all(row["status"] == "pass" for row in result["checks"]["mathematical_correctness"]["target"])
    assert result["scores"]["mathematical_correctness"] == 0
    assert result["scores"]["content_coverage"] == 100


@pytest.mark.parametrize("mutation,math_status,coverage_status", [
    ("identity", "match", "match"), ("radius", "different", "match"),
    ("center", "different", "match"), ("missing", "unknown", "different"),
    ("style", "match", "different"), ("duplicate", "match", "match"),
    ("transform", "match", "match"), ("ellipse", "unknown", "unknown"),
    ("invalid_definition", "unknown", "unknown"),
])
def test_drawn_circle_dependency_and_presence_are_separate(tmp_path, mutation, math_status, coverage_status):
    from evaluation.tikz_coverage import content_contract
    from evaluation.tikz_observations import read_scene
    import math

    coordinates = [(100, 100), (140, 100), (100, 70)]
    target = diagram(tmp_path / "target.pdf", coordinates=coordinates)
    transformed = {"scale": 1.7, "rotation": True, "reflection": True} if mutation == "transform" else {}
    output = diagram(tmp_path / "output.pdf", coordinates=coordinates, **transformed)
    for role, observation in (("target", target), ("output", output)):
        points = observation["labeled_points"]
        center = (points["A"]["pdf_x"], points["A"]["pdf_y"])
        witness = (points["C"]["pdf_x"], points["C"]["pdf_y"])
        radius = math.dist(center, witness)
        change = mutation if role == "output" else "identity"
        if change == "missing":
            continue
        if change == "radius":
            radius *= 1.25
        if change == "center":
            center = (center[0] + 10, center[1])
        with pymupdf.open(observation["pdf_path"]) as pdf:
            if change == "ellipse":
                pdf[0].draw_oval((center[0]-radius, center[1]-radius/2, center[0]+radius, center[1]+radius/2), dashes="[4 3]")
            else:
                for _ in range(2 if change == "duplicate" else 1):
                    pdf[0].draw_circle(center, radius, dashes="[]" if change == "style" else "[4 3]")
            pdf.saveIncr()
    contract = [row for row in content_contract(read_scene(target)) if row["kind"] != "circle"]
    contract.append({"kind": "circle", "points": ["A"] if mutation == "invalid_definition" else ["A", "C"], "dashed": True})
    result = evaluate(target, output, evaluation_rubric=RIGHT_TRIANGLE, content_requirements=contract)
    assert result["scores"]["mathematical_correctness"] == pytest.approx(100 if math_status == "match" else 200/3)
    assert (result["counts"]["mathematical_correctness"]["unresolved"] == 1) == (math_status == "unknown")
    assert (result["scores"]["content_coverage"] == 100) == (coverage_status == "match")
    if mutation in {"missing", "style"}:
        assert result["scores"]["content_coverage"] == pytest.approx(600/7)
    unspecified = evaluate(target, target, evaluation_rubric=RIGHT_TRIANGLE)
    assert unspecified["scores"]["mathematical_correctness"] == pytest.approx(200/3)
    assert unspecified["counts"]["mathematical_correctness"]["unresolved"] == 1


@pytest.mark.parametrize("swap_style", [False, True])
def test_circle_binding_ignores_draw_order_but_preserves_each_style(tmp_path, swap_style):
    from evaluation.tikz_coverage import content_contract
    from evaluation.tikz_observations import read_scene
    import math

    target = diagram(tmp_path / "target.pdf", coordinates=[(100, 100), (140, 100), (100, 70)])
    output = diagram(tmp_path / "output.pdf", coordinates=[(100, 100), (140, 100), (100, 70)])
    for observation, names in ((target, "AB"), (output, "BA")):
        for name in names:
            point = observation["labeled_points"][name]
            center = (point["pdf_x"], point["pdf_y"])
            radius = math.dist(center, (100, 70))
            dashed = name == "A"
            if observation is output and swap_style:
                dashed = not dashed
            with pymupdf.open(observation["pdf_path"]) as pdf:
                pdf[0].draw_circle(center, radius, dashes="[4 3]" if dashed else "[]")
                pdf.saveIncr()
    contract = [row for row in content_contract(read_scene(target)) if row["kind"] != "circle"]
    contract += [{"kind": "circle", "points": [name, "C"], "dashed": name == "A"} for name in "AB"]
    result = evaluate(target, output, evaluation_rubric=RIGHT_TRIANGLE, content_requirements=contract)
    assert result["scores"]["mathematical_correctness"] == 100
    assert result["scores"]["content_coverage"] == (75 if swap_style else 100)
    independent = evaluate({}, output, evaluation_rubric=RIGHT_TRIANGLE, content_requirements=contract)
    assert independent["scores"]["mathematical_correctness"] == 100
    assert all(row["status"] == "unknown" for row in independent["checks"]["mathematical_correctness"]["target"])


def test_partial_scores_do_not_drop_unresolved_checks_or_weight_rubric_groups(tmp_path):
    target = diagram(tmp_path / "target.pdf")
    checks = [{"op": "noncollinear", "points": ["A", "B", "C"]},
              {"op": "perpendicular", "points": ["A", "B", "A", "C"]},
              {"op": "unsupported", "points": ["A", "B"]}]
    grouped = [{"id": str(i), "dimension": "mathematical_correctness", "checks": [check]} for i, check in enumerate(checks)]
    for givens in (rubric(*checks), grouped, rubric(*checks, checks[0])):
        result = evaluate(target, target, evaluation_rubric=givens)
        assert result["scores"]["mathematical_correctness"] == pytest.approx(100/3)
        assert result["counts"]["mathematical_correctness"] == {"passed": 1, "failed": 1, "unresolved": 1, "total": 3}
    assert evaluate(target, target)["scores"]["mathematical_correctness"] is None


def test_content_denominator_deduplicates_objects_and_retains_unmeasured_circles(tmp_path):
    from evaluation.tikz_coverage import content_contract
    from evaluation.tikz_observations import read_scene
    target = diagram(tmp_path / "target.pdf", coordinates=[(30, 100), (130, 100), (30, 30)])
    contract = content_contract(read_scene(target))
    duplicate = [row for row in contract if row["kind"] == "segment"][0]
    repeated = contract + [{**duplicate, "points": list(reversed(duplicate["points"]))}]
    assert evaluate(target, target, content_requirements=repeated)["counts"]["content_coverage"]["total"] == 6
    # Bare circles each declare another object; exceeding the assignment bound must not drop them.
    circles = contract + [{"kind": "circle"} for _ in range(13)]
    result = evaluate(target, target, evaluation_rubric=RIGHT_TRIANGLE, content_requirements=circles)
    assert result["counts"]["mathematical_correctness"] == {"passed": 2, "failed": 0, "unresolved": 13, "total": 15}
    assert result["counts"]["content_coverage"] == {"passed": 6, "failed": 0, "unresolved": 13, "total": 19}


@pytest.mark.parametrize("geometry_space", [None, "euclidean_2d", "affine_projection"])
def test_taxonomy_metadata_cannot_change_evaluation_scores(tmp_path, geometry_space):
    from evaluation.run import _evaluate_case
    drawing = diagram(tmp_path / "right-triangle.pdf", coordinates=[(30, 100), (130, 100), (30, 30)])
    case = {"evaluation_rubric": RIGHT_TRIANGLE}
    if geometry_space is not None:
        case["geometry_space"] = geometry_space
    baseline = _evaluate_case(case, drawing, drawing)
    assert baseline["scores"]["mathematical_correctness"] == (0 if geometry_space == "affine_projection" else 100)
    assert baseline["counts"]["mathematical_correctness"]["unresolved"] == (2 if geometry_space == "affine_projection" else 0)
    for taxonomy in ([], ["G03"], ["G15"], ["G16"], ["G17"], ["G03", "G17"]):
        assert _evaluate_case({**case, "diagram_types": taxonomy}, drawing, drawing) == baseline
