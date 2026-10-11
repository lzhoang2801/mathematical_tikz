import math

import pytest

from tools.spec_first_0410 import check_math, realize, same_ray


@pytest.mark.parametrize("R,r", [(3, 1.5), (4, 1), (4, 2.4), (2, 2), (1, 3.5)])
def test_family_constraints_and_conclusions(R, r):
    points = realize(R, r)
    assert all(row["pass"] for row in check_math(points, {"R": R, "r": r}, 1e-9).values())
    assert points["I"] == pytest.approx([R, math.sqrt(R * r)])
    assert points["K"] == pytest.approx([r, -math.sqrt(R * r)])


def test_wrong_midpoint_can_look_like_it_is_on_DE():
    points = realize(3, 1.5)
    points["K"] = [0.42 * a + 0.58 * b for a, b in zip(points["D"], points["E"])]
    result = check_math(points, {"R": 3, "r": 1.5})
    assert result["tangent_at_C"]["pass"]
    assert not result["K_midpoint_DE"]["pass"]
    assert not result["conclusion_right_angle_K"]["pass"]


def test_on_circle_is_not_sufficient_for_tangency():
    points = realize(3, 1.5)
    points["C"][1] *= -1
    result = check_math(points, {"R": 3, "r": 1.5})
    assert result["C_on_circle_Op"]["pass"]
    assert not result["tangent_at_C"]["pass"]


@pytest.mark.parametrize("value", [0, -1, math.nan, math.inf])
def test_invalid_radii_are_rejected(value):
    with pytest.raises(ValueError, match="finite and positive"):
        realize(3, value)


def test_missing_observation_does_not_pass():
    points = realize(3, 1.5)
    points["K"] = None
    assert not check_math(points, {"R": 3, "r": 1.5})["resolved_points"]["pass"]


def test_marker_can_name_either_endpoint_on_the_same_ray():
    points = realize(3, 1.5)
    assert same_ray(points, "B", "O", "D", 0.005)
    assert same_ray(points, "C", "O'", "E", 0.005)
    assert not same_ray(points, "O", "B", "D", 0.005)
    assert not same_ray(points, "B", "B", "O", 0.005)
