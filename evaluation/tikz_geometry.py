"""Evaluate frozen mathematical relations on measured point coordinates."""

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
    "tangent": 4, "tangent_circumcircle": 5, "concyclic": 4, "distinct": 2,
    "equal_vector": 4, "directed_ratio": 3, "noncollinear": 3,
    "orientation_sign": 3,
}
_GEOMETRY_SPACES = {"euclidean_2d", "affine_projection"}
_AFFINE_PROJECTION_OPS = {
    "collinear", "parallel", "midpoint", "between", "same_ray", "distinct",
    "affine_combination", "equal_vector", "directed_ratio", "noncollinear",
    "orientation_sign",
}
_AREA_TOL = 1e-12

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


def path_parts(drawing: Mapping[str, Any], *, curve_tolerance: float = 0.08) -> list[list[tuple[float, float]]]:
    """Flatten native or serialized vector paths in the supplied coordinate frame."""
    parts = []
    for item in drawing.get("items", []):
        kind = item[0]
        if kind == "l":
            points = [tuple(map(float, item[1])), tuple(map(float, item[2]))]
        elif kind == "c":
            points = _curve([tuple(map(float, point)) for point in item[1:]], tolerance=curve_tolerance)
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



def measure_circle(part: Sequence[tuple[float, float]]) -> dict[str, Any] | None:
    """Measure a closed circular stroke, never a circle inferred from named points."""
    if len(part) < 16 or not LineString(part).is_ring:
        return None
    raw = np.asarray(part[:-1], dtype=float)
    origin = raw.mean(axis=0)
    scale = float(np.max(np.abs(raw - origin)))
    if not math.isfinite(scale) or scale <= 0:
        return None
    xy = (raw - origin) / scale
    try:
        parameters, _, rank, _ = np.linalg.lstsq(np.column_stack((2 * xy, np.ones(len(xy)))), (xy * xy).sum(axis=1), rcond=None)
    except np.linalg.LinAlgError as error:
        raise ValueError("Circle measurement did not converge") from error
    radius_squared = float(parameters[2] + parameters[:2] @ parameters[:2])
    if rank != 3 or radius_squared <= 0:
        return None
    radius = math.sqrt(radius_squared)
    # Include chord interiors so a sparse polygon cannot masquerade as a circle.
    samples = np.concatenate((xy, (xy + np.roll(xy, -1, axis=0)) / 2))
    residual = float(np.max(np.abs(np.linalg.norm(samples - parameters[:2], axis=1) / radius - 1)))
    if not math.isfinite(residual) or residual > REL_TOL:
        return None
    return {"center": (origin + parameters[:2] * scale).tolist(), "radius": radius * scale,
            "radial_residual": residual, "unit": "pdf_pt", "frame": "original_pdf"}


def _point(point_map: Mapping[str, Any], label: str) -> tuple[float, float, str, str]:
    point = point_map.get(label)
    if not isinstance(point, Mapping) or point.get("status") != "measured":
        raise ValueError(f"Point {label!r} has no resolved coordinate measurement")
    x, y = point.get("x"), point.get("y")
    if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise TypeError(f"Point {label!r} has invalid coordinates")
    try:
        x, y = float(x), float(y)
    except OverflowError as error:
        raise ValueError(f"Point {label!r} has unrepresentable coordinates") from error
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError(f"Point {label!r} has non-finite coordinates")
    unit, frame = point.get("unit"), point.get("frame")
    if not isinstance(unit, str) or not isinstance(frame, str):
        raise TypeError(f"Point {label!r} lacks its unit or coordinate frame")
    return float(x), float(y), unit, frame


def _normalize_coordinates(
    coordinates: Sequence[tuple[float, float]],
) -> tuple[list[tuple[float, float]], float]:
    """Use a local unit-diameter frame; page translation and scale are immaterial."""
    if not coordinates:
        return [], 0.0
    ox, oy = coordinates[0]
    translated = [(x - ox, y - oy) for x, y in coordinates]
    if not all(math.isfinite(value) for point in translated for value in point):
        # Subtraction can overflow for opposite finite extremes; rescale first.
        magnitude = max(abs(value) for point in coordinates for value in point)
        scaled = [(x / magnitude, y / magnitude) for x, y in coordinates]
        ox, oy = scaled[0]
        translated = [(x - ox, y - oy) for x, y in scaled]
    magnitude = max(abs(value) for point in translated for value in point)
    if magnitude == 0:
        return [(0.0, 0.0) for _ in coordinates], 0.0
    normalized = [(x / magnitude, y / magnitude) for x, y in translated]
    diameter = max(math.dist(a, b) for a in normalized for b in normalized)
    return [(x / diameter, y / diameter) for x, y in normalized], diameter


def _normalized_configuration(
    point_map: Mapping[str, Any], unit: str, frame: str
) -> dict[str, tuple[float, float]] | None:
    """Return measured points in one common, unit-diameter frame."""
    coordinates: dict[str, tuple[float, float]] = {}
    for label in point_map:
        try:
            x, y, point_unit, point_frame = _point(point_map, label)
        except (TypeError, ValueError):
            continue
        if point_unit == unit and point_frame == frame:
            coordinates[label] = (x, y)
    if len(coordinates) < 2:
        return None
    labels = list(coordinates)
    normalized, extent = _normalize_coordinates(list(coordinates.values()))
    if extent == 0:
        return None
    return dict(zip(labels, normalized))


def _check_geometry(
    check: dict[str, Any],
    point_map: Mapping[str, Any],
    *,
    geometry_space: str = "euclidean_2d",
) -> dict[str, Any]:
    operation = check.get("op")
    labels = check.get("points")
    if not isinstance(operation, str) or not isinstance(labels, list):
        return {"status": "unknown", "reason": "invalid_check"}
    if operation != "affine_combination" and operation not in _PREDICATE_ARITY:
        return {"status": "unknown", "reason": "unsupported_check"}
    if operation == "affine_combination":
        if len(labels) < 2:
            return {"status": "unknown", "reason": "wrong_point_arity"}
    elif len(labels) != _PREDICATE_ARITY[operation]:
        return {"status": "unknown", "reason": "wrong_point_arity"}
    if geometry_space not in _GEOMETRY_SPACES:
        return {"status": "unknown", "reason": "unsupported_geometry_space"}
    if geometry_space == "affine_projection" and operation not in _AFFINE_PROJECTION_OPS:
        return {"status": "unknown", "reason": "unsupported_predicate_in_geometry_space"}
    if not isinstance(point_map, Mapping):
        return {"status": "unknown", "reason": "point_measurements_unavailable"}
    weights = None
    if operation == "affine_combination":
        raw_weights = check.get("weights")
        if (
            not isinstance(raw_weights, list)
            or len(raw_weights) != len(labels) - 1
            or any(isinstance(weight, bool) or not isinstance(weight, Real) for weight in raw_weights)
        ):
            return {"status": "unknown", "reason": "invalid_affine_weights"}
        try:
            weights = [float(weight) for weight in raw_weights]
            weight_sum = math.fsum(weights)
        except (OverflowError, ValueError):
            return {"status": "unknown", "reason": "invalid_affine_weights"}
        if not all(math.isfinite(weight) for weight in weights) or not math.isfinite(weight_sum):
            return {"status": "unknown", "reason": "invalid_affine_weights"}
        if not math.isclose(weight_sum, 1.0, rel_tol=1e-12, abs_tol=1e-12):
            return {"status": "unknown", "reason": "affine_weights_must_sum_to_one"}
        # Absorb harmless serialization error while retaining translation invariance.
        if len(weights) == 1:
            weights[0] = 1.0
        else:
            weights = [weight / weight_sum for weight in weights]
            weights[-1] = 1.0 - math.fsum(weights[:-1])
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

    if operation == "distinct":
        configuration = _normalized_configuration(
            point_map, next(iter(units)), next(iter(frames))
        )
        if configuration is None:
            return {"status": "unknown", "reason": "configuration_scale_unavailable"}
        p = [configuration[label] for label in labels]
    else:
        p, extent = _normalize_coordinates(p)
        if extent == 0 and operation not in {"affine_combination", "equal_vector", "midpoint"}:
            return {"status": "fail", "reason": "degenerate_configuration", "residual": 1.0}
    scale = 1.0
    raw_value = check.get("value", 1.0)
    if isinstance(raw_value, bool) or not isinstance(raw_value, Real):
        return {"status": "unknown", "reason": "invalid_check_value"}
    try:
        value = float(raw_value)
    except (OverflowError, ValueError):
        return {"status": "unknown", "reason": "invalid_check_value"}
    if not math.isfinite(value):
        return {"status": "unknown", "reason": "invalid_check_value"}
    if operation == "orientation_sign" and value not in (-1.0, 1.0):
        return {"status": "unknown", "reason": "orientation_sign_value_must_be_plus_or_minus_one"}

    threshold = REL_TOL
    conditions = {}
    try:
        if operation == "distinct":
            separation_ratio = dist(p[0], p[1]) / scale
            conditions = {"separation_ratio": separation_ratio, "min_ratio_exclusive": 1e-5}
            passed = separation_ratio > conditions["min_ratio_exclusive"]
            residual, threshold = None, None
        elif operation == "affine_combination":
            expected = (
                math.fsum(weight * point[0] for weight, point in zip(weights, p[1:])),
                math.fsum(weight * point[1] for weight, point in zip(weights, p[1:])),
            )
            residual = dist(p[0], expected) / scale
            conditions = {"weights": weights, "weight_sum": math.fsum(weights)}
            passed = residual <= threshold
        elif operation == "equal_vector":
            first_vector, second_vector = sub(p[1], p[0]), sub(p[3], p[2])
            vector_scale = max(norm(first_vector), norm(second_vector))
            residual = norm(sub(first_vector, second_vector)) / vector_scale if vector_scale else 0.0
            passed = residual <= threshold
        elif operation == "directed_ratio":
            offset, direction = sub(p[0], p[1]), sub(p[2], p[1])
            direction_norm = norm(direction)
            if direction_norm < scale * 1e-6:
                raise ValueError("zero_length_segment")
            observed_ratio = dot(offset, direction) / dot(direction, direction)
            line_residual = abs(cross(offset, direction)) / dot(direction, direction)
            ratio_residual = abs(observed_ratio - value)
            residual = max(line_residual, ratio_residual)
            conditions = {
                "observed_ratio": observed_ratio,
                "requested_ratio": value,
                "line_residual_ratio": line_residual,
            }
            passed = line_residual <= threshold and ratio_residual <= threshold
        elif operation in {"noncollinear", "orientation_sign"}:
            signed_area = cross(sub(p[1], p[0]), sub(p[2], p[0]))
            area = abs(signed_area)
            conditions = {
                "signed_area_ratio": signed_area,
                "min_abs_area_ratio_exclusive": _AREA_TOL,
            }
            if operation == "noncollinear":
                residual = area
                threshold = _AREA_TOL
                passed = area > threshold
            else:
                if area <= _AREA_TOL:
                    return {"status": "unknown", "reason": "orientation_undefined_or_nearly_collinear"}
                conditions["expected_sign"] = value
                residual = area
                threshold = _AREA_TOL
                passed = (1.0 if signed_area > 0 else -1.0) == value
        elif operation in {"perpendicular", "parallel", "equal_length", "length_ratio", "shorter"}:
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
    except (OverflowError, ZeroDivisionError, ValueError) as error:
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


def evaluate_checks(
    checks: list[dict[str, Any]],
    points: Mapping[str, Any],
    *,
    geometry_space: str = "euclidean_2d",
) -> list[dict[str, Any]]:
    """Evaluate fixed 2D predicates in Euclidean or affine-projection space."""
    if not isinstance(checks, list):
        raise TypeError("checks must be a list")
    if not isinstance(points, Mapping):
        raise TypeError("points must be a mapping")
    results = []
    for check in checks:
        if not isinstance(check, dict):
            result = {"status": "unknown", "reason": "invalid_check"}
            selected_space = geometry_space
        else:
            selected_space = check.get("geometry_space", geometry_space)
            if not isinstance(selected_space, str) or not selected_space:
                result = {"status": "unknown", "reason": "invalid_geometry_space"}
            elif selected_space not in _GEOMETRY_SPACES:
                result = {"status": "unknown", "reason": "unsupported_geometry_space"}
            else:
                result = _check_geometry(check, points, geometry_space=selected_space)
        result["geometry_space"] = selected_space
        results.append({"check": check, **result})
    return results
