"""Predicate calibration without a model or compiler; live artifacts are separate."""
import json
import math

import pytest

from tools.spec_first_example import EXAMPLE, check_geometry

SPEC = json.loads((EXAMPLE / "spec.json").read_text(encoding="utf-8"))
POINTS = {"A": (0, 0), "B": (4, 0), "C": (0, 3), "H": (1.44, 1.92)}


@pytest.mark.parametrize("scale,angle,reflection", [(1, 0, 1), (7, 0.8, 1), (0.3, 2, -1)])
def test_correct_geometry_is_invariant_to_similarity(scale, angle, reflection):
    co, si = math.cos(angle), math.sin(angle)
    points = {name: (8 + scale * (co * x - si * y), -3 + reflection * scale * (si * x + co * y))
              for name, (x, y) in POINTS.items()}
    assert all(row["pass"] for row in check_geometry(points, SPEC).values())


def test_foot_on_hypotenuse_is_not_enough():
    checks = check_geometry({**POINTS, "H": (2, 1.5)}, SPEC)
    assert checks["H_on_BC"]["pass"] and checks["H_inside_BC"]["pass"]
    assert not checks["AH_perpendicular_BC"]["pass"]


def test_wrong_ratio_with_correct_altitude_still_fails():
    t = 16 / (16 + 2.5**2)
    checks = check_geometry({**POINTS, "C": (0, 2.5), "H": (4 - 4 * t, 2.5 * t)}, SPEC)
    assert checks["AH_perpendicular_BC"]["pass"]
    assert not checks["ratio_AC_AB"]["pass"]
    assert not checks["ratio_BC_AB"]["pass"]


@pytest.mark.parametrize("replacement", [None, (float("nan"), 0), (float("inf"), 0)])
def test_missing_or_nonfinite_evidence_never_passes(replacement):
    assert not check_geometry({**POINTS, "H": replacement}, SPEC)["measured_points"]["pass"]


def test_collapsed_points_do_not_divide_by_zero():
    assert not check_geometry({name: (0, 0) for name in POINTS}, SPEC)["distinct_points"]["pass"]
