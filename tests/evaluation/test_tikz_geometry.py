"""Regression tests for frozen point predicates and admissible configurations."""

import math

import pytest

from evaluation.tikz_geometry import evaluate_checks


def transformed(points, *, scale=2.3, angle=0.71, reflection=False):
    cosine, sine = math.cos(angle), math.sin(angle)
    result = {}
    for label, (x, y) in points.items():
        if reflection:
            x = -x
        result[label] = (
            17 + scale * (cosine * x - sine * y),
            -8 + scale * (sine * x + cosine * y),
        )
    return result


def test_fixed_predicates_use_measured_points_and_report_actual_ordering_conditions():
    points = {
        label: {"status": "measured", "x": x, "y": y, "unit": "pdf_pt", "frame": "original_pdf", "evidence_id": label}
        for label, (x, y) in {"A": (0, 10), "H": (0, 0), "B": (-10, 0), "C": (10, 0)}.items()
    }
    checks = [
        {"op": "perpendicular", "points": ["A", "H", "B", "C"]},
        {"op": "shorter", "points": ["H", "B", "B", "C"]},
        {"op": "outside_circle", "points": ["C", "B", "H"]},
        {"op": "between", "points": ["C", "B", "H"]},
    ]
    perpendicular, shorter, outside, between = evaluate_checks(checks, points)
    assert perpendicular["status"] == "pass" and perpendicular["evidence_ids"] == ["A", "H", "B", "C"]
    assert shorter["status"] == outside["status"] == "pass"
    assert shorter["residual"] is None and shorter["tolerance"] is None
    assert shorter["conditions"]["length_ratio"] < shorter["conditions"]["max_ratio_exclusive"]
    assert outside["residual"] is None and outside["tolerance"] is None
    assert outside["conditions"]["radius_ratio"] > outside["conditions"]["min_ratio_exclusive"]
    assert between["status"] == "fail" and between["residual"] == 0
    assert between["conditions"]["line_parameter"] > between["conditions"]["max_parameter_exclusive"]
    points["H"] = {"status": "unknown"}
    assert evaluate_checks(checks[:1], points)[0]["status"] == "unknown"
    coincident = {"A": {"status": "measured", "x": 0, "y": 0, "unit": "pdf_pt", "frame": "original_pdf"}}
    unknown, malformed = evaluate_checks([
        {"op": "not_implemented", "points": ["A"]},
        {"op": "perpendicular", "points": ["A"]},
    ], coincident)
    assert unknown["status"] == "unknown" and unknown["reason"] == "unsupported_check"
    assert malformed["status"] == "unknown" and malformed["reason"] == "wrong_point_arity"


def test_distinct_is_explicit_and_normalized_to_the_observed_configuration():
    check = {"op": "distinct", "points": ["A", "B"]}
    for factor in (1e-6, 1.0, 1e6):
        observed = {
            label: {"status": "measured", "x": x * factor, "y": y * factor, "unit": "pt", "frame": "pdf"}
            for label, (x, y) in {"A": (0, 0), "B": (1, 0), "C": (0, 1)}.items()
        }
        result = evaluate_checks([check], observed)[0]
        assert result["status"] == "pass"
        assert result["conditions"]["separation_ratio"] == pytest.approx(1 / 2**0.5)

    coincident = {
        label: {"status": "measured", "x": x, "y": y, "unit": "pt", "frame": "pdf"}
        for label, (x, y) in {"A": (0, 0), "B": (0, 0), "C": (0, 1)}.items()
    }
    result = evaluate_checks([check], coincident)[0]
    assert result["status"] == "fail"
    assert result["conditions"]["separation_ratio"] == 0

    # Coincident labels are not rejected unless their pair is an explicit requirement.
    coincident["B"] = {"status": "measured", "x": 1, "y": 0, "unit": "pt", "frame": "pdf"}
    coincident.update({
        label: {"status": "measured", "x": x, "y": y, "unit": "pt", "frame": "pdf"}
        for label, (x, y) in {"M": (0.5, 0.5), "I": (0.5, 0.5)}.items()
    })
    unrelated = evaluate_checks([{"op": "perpendicular", "points": ["A", "C", "A", "B"]}], coincident)[0]
    assert unrelated["status"] == "pass"


def test_distinct_is_unknown_without_a_configuration_diameter():
    observed = {
        label: {"status": "measured", "x": 0, "y": 0, "unit": "pt", "frame": "pdf"}
        for label in ("A", "B")
    }
    result = evaluate_checks([{"op": "distinct", "points": ["A", "B"]}], observed)[0]
    assert result["status"] == "unknown"
    assert result["reason"] == "configuration_scale_unavailable"


def test_required_short_segment_relation_is_checked_explicitly_beyond_distance_tolerance():
    epsilon = 1e-4
    target = {"A": (0, 0), "B": (epsilon, epsilon), "C": (1, 0), "D": (1 + epsilon, -epsilon)}
    output = {**target, "B": (epsilon, -epsilon)}
    check = {"op": "perpendicular", "points": ["A", "B", "C", "D"]}
    for points, expected in ((target, "pass"), (output, "fail")):
        observed = {
            label: {"status": "measured", "x": x, "y": y, "unit": "pdf_pt", "frame": "original_pdf", "evidence_id": label}
            for label, (x, y) in points.items()
        }
        result = evaluate_checks([check], observed)[0]
        assert result["status"] == expected
        assert result["evidence_ids"] == ["A", "B", "C", "D"]
        assert result["residual"] == pytest.approx(0 if expected == "pass" else 1, abs=1e-12)


def _measured(points):
    return {
        label: {
            "status": "measured",
            "x": x,
            "y": y,
            "unit": "pdf_pt",
            "frame": "original_pdf",
            "evidence_id": label,
        }
        for label, (x, y) in points.items()
    }


def test_affine_prism_dependencies_accept_different_bases_and_shears():
    checks = [
        {"op": "noncollinear", "points": ["A", "B", "C"]},
        {"op": "equal_vector", "points": ["A", "A1", "B", "B1"]},
        {"op": "equal_vector", "points": ["A", "A1", "C", "C1"]},
        {"op": "affine_combination", "points": ["M", "A", "B"], "weights": [0.5, 0.5]},
    ]
    configurations = [
        {"A": (0, 0), "B": (4, 0), "C": (1, 3), "A1": (2, 1), "B1": (6, 1), "C1": (3, 4), "M": (2, 0)},
        {"A": (10, -5), "B": (15, -4), "C": (12, 2), "A1": (7, -1), "B1": (12, 0), "C1": (9, 6), "M": (12.5, -4.5)},
    ]

    for configuration in configurations:
        results = evaluate_checks(checks, _measured(configuration), geometry_space="affine_projection")
        assert [result["status"] for result in results] == ["pass"] * len(checks)
        assert all(result["geometry_space"] == "affine_projection" for result in results)

    wrong_child = {**configurations[0], "B1": (6.2, 1)}
    results = evaluate_checks(checks[1:3], _measured(wrong_child), geometry_space="affine_projection")
    assert [result["status"] for result in results] == ["fail", "pass"]


def test_affine_projection_does_not_claim_screen_metric_truth():
    points = _measured({"A": (0, 0), "B": (1, 0), "C": (0, 0), "D": (0, 1)})
    check = {"op": "perpendicular", "points": ["A", "B", "C", "D"]}

    projected = evaluate_checks([check], points, geometry_space="affine_projection")[0]
    euclidean = evaluate_checks([check], points)[0]

    assert projected["status"] == "unknown"
    assert projected["reason"] == "unsupported_predicate_in_geometry_space"
    assert euclidean["status"] == "pass"

    # A check-level space overrides the call default and is reported in evidence.
    overridden = evaluate_checks(
        [{**check, "geometry_space": "affine_projection"}], points
    )[0]
    assert overridden["status"] == "unknown"
    assert overridden["geometry_space"] == "affine_projection"


@pytest.mark.parametrize(
    ("geometry_space", "reason"),
    [("xyz", "unsupported_geometry_space"), (None, "invalid_geometry_space")],
)
def test_invalid_geometry_space_is_unknown_without_a_geometry_claim(geometry_space, reason):
    points = _measured({"A": (0, 0), "B": (1, 0), "C": (0, 1)})
    result = evaluate_checks(
        [{"op": "noncollinear", "points": ["A", "B", "C"]}],
        points,
        geometry_space=geometry_space,
    )[0]

    assert result["status"] == "unknown"
    assert result["reason"] == reason


def test_unrepresentable_predicate_value_is_unknown_not_an_exception():
    points = _measured({"A": (0, 0), "B": (1, 0), "C": (0, 1)})
    result = evaluate_checks(
        [{"op": "orientation_sign", "points": ["A", "B", "C"], "value": 10**1000}],
        points,
        geometry_space="affine_projection",
    )[0]

    assert result["status"] == "unknown"
    assert result["reason"] == "invalid_check_value"


@pytest.mark.parametrize("factor", [1e-200, 1e200])
def test_fixed_predicates_are_similarity_scale_invariant(factor):
    raw = {"A": (0, 0), "B": (4, 0), "C": (0, 3), "M": (2, 0)}
    scaled = {label: (x * factor, y * factor) for label, (x, y) in raw.items()}
    checks = [
        {"op": "perpendicular", "points": ["A", "B", "A", "C"]},
        {"op": "midpoint", "points": ["M", "A", "B"]},
    ]

    results = evaluate_checks(checks, _measured(scaled))
    assert [result["status"] for result in results] == ["pass", "pass"]


@pytest.mark.parametrize(
    ("weights", "reason"),
    [
        ([True, 0.0], "invalid_affine_weights"),
        ([0.5], "invalid_affine_weights"),
        ([0.5, "0.5"], "invalid_affine_weights"),
        ([0.4, 0.4], "affine_weights_must_sum_to_one"),
        ([math.nan, math.inf], "invalid_affine_weights"),
    ],
)
def test_affine_combination_rejects_malformed_weights_as_unknown(weights, reason):
    points = _measured({"M": (0.5, 0.5), "A": (0, 0), "B": (1, 1)})
    result = evaluate_checks(
        [{"op": "affine_combination", "points": ["M", "A", "B"], "weights": weights}],
        points,
        geometry_space="affine_projection",
    )[0]

    assert result["status"] == "unknown"
    assert result["reason"] == reason


def test_orientation_sign_makes_reflection_policy_explicit():
    original = {"A": (0, 0), "B": (1, 0), "C": (0, 1)}
    reflected = {label: (-x, y) for label, (x, y) in original.items()}
    ccw = {"op": "orientation_sign", "points": ["A", "B", "C"], "value": 1}
    cw = {"op": "orientation_sign", "points": ["A", "B", "C"], "value": -1}

    assert evaluate_checks([ccw], _measured(original), geometry_space="affine_projection")[0]["status"] == "pass"
    assert evaluate_checks([ccw], _measured(reflected), geometry_space="affine_projection")[0]["status"] == "fail"
    assert evaluate_checks([cw], _measured(reflected), geometry_space="affine_projection")[0]["status"] == "pass"


def test_unrepresentable_coordinate_is_unknown_not_an_exception():
    points = _measured({"A": (10**1000, 0), "B": (1, 0), "M": (0.5, 0)})
    result = evaluate_checks([{"op": "midpoint", "points": ["M", "A", "B"]}], points)[0]
    assert result["status"] == "unknown"


def test_distant_vector_origins_do_not_hide_a_wrong_vector():
    check = {"op": "equal_vector", "points": ["A", "B", "C", "D"]}
    points = _measured({"A": (0, 0), "B": (0, 1), "C": (1e8, 0), "D": (1e8, 2)})
    assert evaluate_checks([check], points, geometry_space="affine_projection")[0]["status"] == "fail"
    points["D"]["y"] = 1
    assert evaluate_checks([check], points, geometry_space="affine_projection")[0]["status"] == "pass"


def test_similarity_and_reflection_preserve_declared_ratios():
    points = {"A": (0, 0), "B": (4, 0), "C": (0, 3)}
    check = {"op": "length_ratio", "points": ["A", "B", "A", "C"], "value": 4/3}
    for reflected in (False, True):
        assert evaluate_checks([check], _measured(transformed(points, reflection=reflected)))[0]["status"] == "pass"
