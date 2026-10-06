"""Compare point proportions and evaluate mathematical relations in one frame."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any

import numpy as np
from shapely.geometry import LineString, Point

REL_TOL = 0.005
ANGLE_TOL = math.sin(math.radians(1))
_PREDICATE_ARITY = {
    "perpendicular": 4, "parallel": 4, "equal_length": 4, "length_ratio": 4,
    "shorter": 4, "midpoint": 3, "on_circle": 3, "outside_circle": 3,
    "collinear": 3, "between": 3, "same_ray": 3, "minor_arc": 4,
    "tangent": 4, "tangent_circumcircle": 5, "concyclic": 4,
}

# Bound the quadratic distance matrices and their serialized evidence.
MAX_POINT_LABELS = 64
MAX_WITNESSES = 8


def _read_points(value: Any) -> tuple[set[str], dict[str, tuple[float, float]], list[str], dict[str, str], str | None]:
    if not isinstance(value, Mapping):
        return set(), {}, [], {}, "point_bindings_not_a_mapping"
    keys: set[str] = set()
    points: dict[str, tuple[float, float]] = {}
    unresolved: list[str] = []
    invalid: dict[str, str] = {}
    mapping_error = None
    for label, pair in value.items():
        if not isinstance(label, str) or not label:
            mapping_error = "point_labels_must_be_nonempty_strings"
            continue
        keys.add(label)
        if pair is None:
            unresolved.append(label)
            continue
        if (
            isinstance(pair, (str, bytes, bytearray))
            or not isinstance(pair, Sequence)
            or len(pair) != 2
            or any(isinstance(item, bool) or not isinstance(item, Real) for item in pair)
        ):
            unresolved.append(label)
            invalid[label] = "coordinate_must_be_a_pair_of_finite_numbers"
            continue
        try:
            x, y = float(pair[0]), float(pair[1])
        except (OverflowError, ValueError):
            unresolved.append(label)
            invalid[label] = "coordinate_cannot_be_represented_as_finite_float"
            continue
        if not math.isfinite(x) or not math.isfinite(y):
            unresolved.append(label)
            invalid[label] = "coordinate_is_not_finite"
            continue
        points[label] = (x, y)
    return keys, points, sorted(set(unresolved)), invalid, mapping_error


def _distance_data(
    points: Mapping[str, tuple[float, float]], labels: list[str]
) -> tuple[list[list[float]], float, str | None]:
    raw = [[0.0] * len(labels) for _ in labels]
    extent = 0.0
    for i, left in enumerate(labels):
        for j in range(i + 1, len(labels)):
            try:
                distance = math.dist(points[left], points[labels[j]])
            except OverflowError:
                return [], 0.0, "pair_distance_overflow"
            if not math.isfinite(distance):
                return [], 0.0, "pair_distance_overflow"
            raw[i][j] = raw[j][i] = distance
            extent = max(extent, distance)
    if extent == 0:
        return [[0.0] * len(labels) for _ in labels], 0.0, None
    normalized = [[distance / extent for distance in row] for row in raw]
    if any(raw[i][j] > 0 and normalized[i][j] == 0 for i in range(len(labels)) for j in range(len(labels))):
        return normalized, extent, "normalized_distance_underflow"
    return normalized, extent, None


def _distance_uncertainty(coordinate_radius: float) -> float:
    """Bound normalized-distance error from coordinate error after diameter scaling."""
    if coordinate_radius == 0:
        return 0.0
    if coordinate_radius >= 0.5:
        return 1.0
    return min(1.0, 4.0 * coordinate_radius / (1.0 - 2.0 * coordinate_radius))


def _threshold_status(error: float, tolerance: float, uncertainty: float) -> str:
    if error + uncertainty <= tolerance:
        return "match"
    if max(0.0, error - uncertainty) > tolerance:
        return "different"
    return "unknown"


def _ratio_status(
    target: float, output: float, target_bound: float, output_bound: float, tolerance: float
) -> tuple[str, float | None, float | None]:
    target_low, target_high = max(0.0, target - target_bound), min(1.0, target + target_bound)
    output_low, output_high = max(0.0, output - output_bound), min(1.0, output + output_bound)
    if target_high == output_high == 0:
        return "match", 0.0, 0.0
    if (target_high == 0 and output_low > 0) or (output_high == 0 and target_low > 0):
        return "different", None, None
    if min(target_low, output_low) == 0:
        return "unknown", None, None
    log_low = math.log(output_low) - math.log(target_high)
    log_high = math.log(output_high) - math.log(target_low)
    nearest = 0.0 if log_low <= 0 <= log_high else min(abs(log_low), abs(log_high))
    farthest = max(abs(log_low), abs(log_high))
    status = "match" if farthest <= tolerance else "different" if nearest > tolerance else "unknown"
    observed = abs(math.log(output) - math.log(target))
    return status, observed, farthest


def _insert_witness(witnesses: list[dict[str, Any]], item: dict[str, Any], key: str) -> None:
    witnesses.append(item)

    def rank(row: dict[str, Any]) -> tuple[int, float]:
        priority = {"different": 2, "unknown": 1, "match": 0}.get(row.get("status"), -1)
        value = row.get(key)
        residual = math.inf if value is None and priority == 2 else float(value or 0.0)
        return priority, residual

    witnesses.sort(key=rank, reverse=True)
    del witnesses[MAX_WITNESSES:]


def _valid_nonnegative(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return False
    return math.isfinite(number) and number >= 0


def compare_point_geometry(
    target: Mapping[str, Sequence[float] | None],
    output: Mapping[str, Sequence[float] | None],
    *,
    distance_tolerance: float = 0.005,
    relative_tolerance: float = 0.02,
    target_uncertainty: float = 0.0,
    output_uncertainty: float = 0.0,
) -> dict[str, Any]:
    """Compare labeled point proportions through complete normalized distances.

    Required relations are checked by evaluate_checks; reflection policy belongs
    to the shared similarity alignment, not this distance comparison.

    Uncertainty values are maximum Euclidean point-coordinate radii divided by
    their own configuration's observed diameter. Zero asserts negligible
    numerical error; it is not an empirical calibration. A None value records
    a visible label whose point coordinate could not be bound.
    """
    target_keys, target_points, target_unresolved, target_invalid, target_error = _read_points(target)
    output_keys, output_points, output_unresolved, output_invalid, output_error = _read_points(output)
    missing, extra = sorted(target_keys - output_keys), sorted(output_keys - target_keys)
    labels = sorted(target_points.keys() & output_points.keys())
    result: dict[str, Any] = {
        "status": "unknown",
        "labels": labels,
        "missing": missing,
        "extra": extra,
        "unresolved_target": target_unresolved,
        "unresolved_output": output_unresolved,
        "invalid_target": target_invalid,
        "invalid_output": output_invalid,
        "normalization": "each pairwise distance matrix divided by its own diameter",
        "tolerances": {
            "max_abs_normalized_distance": distance_tolerance,
            "max_abs_log_normalized_pair_distance": relative_tolerance,
            "coordinate_uncertainty": "Euclidean point-coordinate radius divided by that side's observed diameter",
            "calibration": "caller supplied; defaults are experimental and not human calibrated",
        },
        "uncertainty": {
            "target_coordinate_radius": target_uncertainty,
            "output_coordinate_radius": output_uncertainty,
            "target_normalized_distance_bound": None,
            "output_normalized_distance_bound": None,
        },
        "target_distance_matrix": None,
        "output_distance_matrix": None,
        "global_distance": {"status": "unknown", "max_abs_error": None, "worst_pair": None},
        "local_ratios": {"status": "unknown", "max_abs_log_error": None, "worst_pair": None, "largest_residuals": []},
        "limitations": [],
    }
    if target_error:
        result["limitations"].append(target_error)
    if output_error:
        result["limitations"].append(output_error)
    if not all(_valid_nonnegative(value) for value in (
        target_uncertainty, output_uncertainty, distance_tolerance, relative_tolerance
    )):
        result["limitations"].append("invalid_tolerance_or_uncertainty")
        result["status"] = "different" if missing or extra else "unknown"
        return result
    target_uncertainty = float(target_uncertainty)
    output_uncertainty = float(output_uncertainty)
    distance_tolerance = float(distance_tolerance)
    relative_tolerance = float(relative_tolerance)
    if len(target_keys | output_keys) > MAX_POINT_LABELS:
        result["limitations"].append(f"point_count_exceeds_bound_{MAX_POINT_LABELS}")
        result["status"] = "different" if missing or extra else "unknown"
        return result
    if len(labels) < 2:
        result["limitations"].append("fewer_than_two_resolved_corresponding_points")
        result["status"] = "different" if missing or extra else "unknown"
        return result

    target_matrix, target_extent, target_problem = _distance_data(target_points, labels)
    output_matrix, output_extent, output_problem = _distance_data(output_points, labels)
    if target_problem or output_problem:
        result["limitations"].append(target_problem or output_problem or "point_distance_extraction_failed")
        result["status"] = "different" if missing or extra else "unknown"
        return result
    if target_extent == 0 or output_extent == 0:
        if (target_extent == 0) != (output_extent == 0):
            result["global_distance"] = {
                "status": "different",
                "max_abs_error": None,
                "worst_pair": None,
                "reason": "one_configuration_collapses_all_matched_points",
            }
            result["status"] = "different"
        else:
            result["limitations"].append("both_configurations_have_zero_diameter")
            result["status"] = "different" if missing or extra else "unknown"
        return result

    result["target_distance_matrix"] = target_matrix
    result["output_distance_matrix"] = output_matrix
    target_bound = _distance_uncertainty(target_uncertainty)
    output_bound = _distance_uncertainty(output_uncertainty)
    result["uncertainty"]["target_normalized_distance_bound"] = target_bound
    result["uncertainty"]["output_normalized_distance_bound"] = output_bound
    if target_uncertainty >= 0.5 or output_uncertainty >= 0.5:
        result["limitations"].append("coordinate_uncertainty_can_collapse_a_point_configuration")

    deltas = [
        [abs(target_matrix[i][j] - output_matrix[i][j]) for j in range(len(labels))]
        for i in range(len(labels))
    ]
    pair_indices = [(i, j) for i in range(len(labels)) for j in range(i + 1, len(labels))]
    worst_i, worst_j = max(pair_indices, key=lambda pair: deltas[pair[0]][pair[1]])
    global_error = deltas[worst_i][worst_j]
    global_bound = target_bound + output_bound
    global_status = _threshold_status(global_error, distance_tolerance, global_bound)
    result["global_distance"] = {
        "status": global_status,
        "max_abs_error": global_error,
        "worst_pair": [labels[worst_i], labels[worst_j]],
        "uncertainty_bound": global_bound,
    }

    ratio_states, ratio_witnesses = [], []
    max_log_error, worst_ratio_pair, unresolved_ratios = -1.0, None, 0
    for i, j in pair_indices:
        left, right = labels[i], labels[j]
        state, observed, upper = _ratio_status(
            target_matrix[i][j], output_matrix[i][j], target_bound, output_bound, relative_tolerance
        )
        ratio_states.append(state)
        unresolved_ratios += observed is None
        if observed is not None and observed >= max_log_error:
            max_log_error, worst_ratio_pair = observed, [left, right]
        _insert_witness(
            ratio_witnesses,
            {
                "pair": [left, right],
                "target_normalized_distance": target_matrix[i][j],
                "output_normalized_distance": output_matrix[i][j],
                "abs_log_error": observed,
                "uncertainty_upper_bound": upper,
                "status": state,
            },
            "abs_log_error",
        )
    ratio_status = "different" if "different" in ratio_states else "unknown" if "unknown" in ratio_states else "match"
    result["local_ratios"] = {
        "status": ratio_status,
        "max_abs_log_error": max_log_error if worst_ratio_pair and not unresolved_ratios else None,
        "evaluated_pairs": len(pair_indices) - unresolved_ratios,
        "unresolved_pairs": unresolved_ratios,
        "worst_pair": worst_ratio_pair,
        "largest_residuals": ratio_witnesses,
        "meaning": "relative change for each labeled point pair; derived from the same distance matrices",
    }

    statuses = [global_status, ratio_status]
    if missing or extra or "different" in statuses:
        result["status"] = "different"
    elif (
        target_unresolved
        or output_unresolved
        or target_invalid
        or output_invalid
        or target_error
        or output_error
        or "unknown" in statuses
    ):
        result["status"] = "unknown"
        if target_unresolved or output_unresolved:
            result["limitations"].append("one_or_more_labeled_point_coordinates_are_unresolved")
    else:
        result["status"] = "match"
    return result


def _curve(points: list[tuple[float, float]], tolerance: float = 0.08, depth: int = 0) -> list[tuple[float, float]]:
    a, b, c, d = np.asarray(points, dtype=float)
    chord = LineString([a, d]) if np.linalg.norm(d - a) else Point(a)
    if max(chord.distance(Point(b)), chord.distance(Point(c))) <= tolerance:
        return [tuple(a), tuple(d)]
    if depth >= 12:
        raise ValueError("Curve subdivision limit reached")
    ab, bc, cd = (a + b) / 2, (b + c) / 2, (c + d) / 2
    abc, bcd = (ab + bc) / 2, (bc + cd) / 2
    middle = (abc + bcd) / 2
    return _curve([a, ab, abc, middle], tolerance, depth + 1)[:-1] + _curve([middle, bcd, cd, d], tolerance, depth + 1)


def path_parts(drawing: Mapping[str, Any]) -> list[list[tuple[float, float]]]:
    """Flatten native or serialized vector paths in the supplied coordinate frame."""
    parts = []
    for item in drawing.get("items", []):
        kind = item[0]
        if kind == "l":
            points = [tuple(map(float, item[1])), tuple(map(float, item[2]))]
        elif kind == "c":
            points = _curve([tuple(map(float, point)) for point in item[1:]])
        elif kind == "re":
            x0, y0, x1, y1 = map(float, item[1])
            points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        elif kind == "qu":
            quad = item[1]
            corners = [quad.ul, quad.ur, quad.lr, quad.ll] if hasattr(quad, "ul") else [quad[0], quad[1], quad[3], quad[2]]
            points = [tuple(map(float, point)) for point in corners]
            points.append(points[0])
        else:
            raise ValueError(f"Unsupported vector path item: {kind}")
        if not all(math.isfinite(value) for point in points for value in point):
            raise ValueError("Vector path contains nonfinite coordinates")
        if parts and math.dist(parts[-1][-1], points[0]) < 1e-5:
            parts[-1].extend(points[1:])
        else:
            parts.append(points)
    if drawing.get("closePath") and parts and parts[-1][0] != parts[-1][-1]:
        parts[-1].append(parts[-1][0])
    return parts


def _point(point_map: Mapping[str, Any], label: str) -> tuple[float, float, str, str]:
    point = point_map.get(label)
    if not isinstance(point, Mapping) or point.get("status") != "measured":
        raise ValueError(f"Point {label!r} has no resolved coordinate measurement")
    x, y = point.get("x"), point.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise TypeError(f"Point {label!r} has invalid coordinates")
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError(f"Point {label!r} has non-finite coordinates")
    unit, frame = point.get("unit"), point.get("frame")
    if not isinstance(unit, str) or not isinstance(frame, str):
        raise TypeError(f"Point {label!r} lacks its unit or coordinate frame")
    return float(x), float(y), unit, frame


def _check_geometry(check: dict[str, Any], point_map: Mapping[str, Any]) -> dict[str, Any]:
    operation = check.get("op")
    labels = check.get("points")
    if not isinstance(operation, str) or not isinstance(labels, list):
        return {"status": "unknown", "reason": "invalid_check"}
    if operation not in _PREDICATE_ARITY:
        return {"status": "unknown", "reason": "unsupported_check"}
    if len(labels) != _PREDICATE_ARITY[operation]:
        return {"status": "unknown", "reason": "wrong_point_arity"}
    if not isinstance(point_map, Mapping):
        return {"status": "unknown", "reason": "point_measurements_unavailable"}
    try:
        points = [_point(point_map, label) for label in labels]
    except (TypeError, ValueError) as error:
        return {"status": "unknown", "reason": str(error)}
    units = {point[2] for point in points}
    frames = {point[3] for point in points}
    if len(units) != 1 or len(frames) != 1:
        return {"status": "unknown", "reason": "incompatible_point_frames_or_units"}
    p = [(point[0], point[1]) for point in points]

    def sub(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
        return a[0] - b[0], a[1] - b[1]

    def dot(a: tuple[float, float], b: tuple[float, float]) -> float:
        return a[0] * b[0] + a[1] * b[1]

    def cross(a: tuple[float, float], b: tuple[float, float]) -> float:
        return a[0] * b[1] - a[1] * b[0]

    def norm(a: tuple[float, float]) -> float:
        return math.hypot(a[0], a[1])

    def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
        return norm(sub(a, b))

    scale = max((dist(a, b) for a in p for b in p), default=0.0)
    if scale <= 1e-9:
        return {"status": "fail", "reason": "degenerate_configuration", "residual": 1.0}
    value = check.get("value", 1.0)
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return {"status": "unknown", "reason": "invalid_check_value"}

    threshold = REL_TOL
    conditions = {}
    try:
        if operation in {"perpendicular", "parallel", "equal_length", "length_ratio", "shorter"}:
            a, b = sub(p[1], p[0]), sub(p[3], p[2])
            da, db = norm(a), norm(b)
            if min(da, db) < scale * 1e-6:
                raise ValueError("zero_length_segment")
            if operation in {"perpendicular", "parallel"}:
                residual = abs((dot if operation == "perpendicular" else cross)(a, b)) / (da * db)
                threshold = ANGLE_TOL
                passed = residual <= threshold
            elif operation == "shorter":
                conditions = {"length_ratio": da / db, "max_ratio_exclusive": 1 - 1e-5}
                passed = conditions["length_ratio"] < conditions["max_ratio_exclusive"]
                residual, threshold = None, None
            else:
                target = value if operation == "length_ratio" else 1.0
                residual = abs(da / db - target)
                threshold = REL_TOL * abs(target)
                passed = residual <= threshold
        elif operation == "midpoint":
            midpoint = ((p[1][0] + p[2][0]) / 2, (p[1][1] + p[2][1]) / 2)
            residual = dist(p[0], midpoint) / scale
            passed = residual <= threshold
        elif operation in {"on_circle", "outside_circle"}:
            radius = dist(p[1], p[2])
            if radius < scale * 1e-6:
                raise ValueError("zero_radius")
            ratio = dist(p[0], p[1]) / radius
            if operation == "on_circle":
                residual = abs(ratio - 1)
                passed = residual <= threshold
            else:
                conditions = {"radius_ratio": ratio, "min_ratio_exclusive": 1 + 1e-5}
                passed = ratio > conditions["min_ratio_exclusive"]
                residual, threshold = None, None
        elif operation in {"collinear", "between", "same_ray"}:
            a, b = (
                (sub(p[1], p[0]), sub(p[2], p[0]))
                if operation == "collinear"
                else (sub(p[0], p[1]), sub(p[2], p[1]))
            )
            if min(norm(a), norm(b)) < scale * 1e-6:
                raise ValueError("undefined_line")
            residual = abs(cross(a, b)) / (norm(b) * scale)
            parameter = dot(a, b) / dot(b, b)
            if operation != "collinear":
                conditions = {"line_parameter": parameter, "min_parameter_exclusive": 1e-5,
                              "max_parameter_exclusive": 1 - 1e-5 if operation == "between" else None}
            passed = residual <= threshold and (
                operation == "collinear"
                or (1e-5 < parameter < 1 - 1e-5 if operation == "between" else parameter > 1e-5)
            )
        elif operation == "minor_arc":
            point, center, start, end = p
            radius = dist(center, start)
            if radius < scale * 1e-6:
                raise ValueError("zero_radius")
            angles = [math.atan2(x[1] - center[1], x[0] - center[0]) for x in (point, start, end)]

            def wrap(angle: float) -> float:
                return (angle + math.pi) % (2 * math.pi) - math.pi

            whole = wrap(angles[2] - angles[1])
            if abs(abs(whole) - math.pi) < 1e-5 or abs(whole) < 1e-5:
                raise ValueError("minor_arc_undefined")
            part = wrap(angles[0] - angles[1])
            residual = max(abs(dist(point, center) / radius - 1), abs(dist(end, center) / radius - 1))
            conditions = {"point_sweep_radians": part, "arc_sweep_radians": whole,
                          "same_direction": part * whole > 0, "inside_open_arc": abs(part) < abs(whole) - 1e-5}
            passed = residual <= threshold and conditions["same_direction"] and conditions["inside_open_arc"]
        elif operation in {"tangent", "tangent_circumcircle"}:
            if operation == "tangent":
                center, witness, a, b = p
                radius = dist(center, witness)
            else:
                a, b, c, d, e = p
                dx, dy = sub(d, c)
                ex, ey = sub(e, c)
                determinant = 2 * (dx * ey - dy * ex)
                if abs(determinant) < scale * scale * 1e-6:
                    raise ValueError("collinear_circumcircle_witnesses")
                ux = ((dx * dx + dy * dy) * ey - (ex * ex + ey * ey) * dy) / determinant
                uy = (dx * (ex * ex + ey * ey) - ex * (dx * dx + dy * dy)) / determinant
                center = c[0] + ux, c[1] + uy
                radius = dist(center, c)
            direction = sub(b, a)
            if min(radius, norm(direction)) < scale * 1e-6:
                raise ValueError("undefined_tangent_line_or_circle")
            residual = abs(abs(cross(direction, sub(center, a))) / (norm(direction) * radius) - 1)
            passed = residual <= threshold
        elif operation == "concyclic":
            a, b, c, d = p
            bx, by = sub(b, a)
            cx, cy = sub(c, a)
            determinant = 2 * (bx * cy - by * cx)
            if abs(determinant) < scale * scale * 1e-6:
                raise ValueError("collinear_circle_witnesses")
            ux = ((bx * bx + by * by) * cy - (cx * cx + cy * cy) * by) / determinant
            uy = (bx * (cx * cx + cy * cy) - cx * (bx * bx + by * by)) / determinant
            center = a[0] + ux, a[1] + uy
            residual = abs(dist(center, d) / dist(center, a) - 1)
            conditions = {"minimum_point_distance": min(dist(x, y) for index, x in enumerate(p) for y in p[index + 1 :]),
                          "min_distance_exclusive": scale * 1e-5}
            passed = residual <= threshold and conditions["minimum_point_distance"] > conditions["min_distance_exclusive"]
    except (ZeroDivisionError, ValueError) as error:
        return {"status": "unknown", "reason": str(error)}

    return {
        "status": "pass" if passed else "fail",
        "residual": residual,
        "tolerance": threshold,
        "conditions": conditions,
        "unit": next(iter(units)),
        "frame": next(iter(frames)),
        "evidence_ids": [point_map[label].get("evidence_id") for label in labels],
    }


def evaluate_checks(checks: list[dict[str, Any]], points: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Evaluate fixed mathematical predicates using resolved coordinates only."""
    if not isinstance(checks, list):
        raise TypeError("checks must be a list")
    if not isinstance(points, Mapping):
        raise TypeError("points must be a mapping")
    results = []
    for check in checks:
        result = _check_geometry(check, points) if isinstance(check, dict) else {"status": "unknown", "reason": "invalid_check"}
        result["evidence_scope"] = "coordinate geometry only; does not establish emitted stroke or visible depiction"
        results.append({"check": check, **result})
    return results
