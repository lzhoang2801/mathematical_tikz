"""Measure rendered geometry and compare observable construction relations."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from functools import lru_cache
from itertools import combinations
from typing import Any

import numpy as np
from shapely.geometry import LineString, Point

from evaluation.tikz_coverage import connections

REL_TOL = 0.005


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


def _assign_circles(errors: list[list[float]], target: list[dict], output: list[dict]) -> tuple:
    """Match distinct circles, preferring geometry, then dash style, then residual."""
    size = max(len(target), len(output))

    @lru_cache(maxsize=None)
    def assign(i: int, used: int) -> tuple:
        if i == len(target):
            return 0, 0, 0.0, ()
        candidates = []
        for j in range(size):
            if used & (1 << j):
                continue
            failures, style, residual, tail = assign(i + 1, used | (1 << j))
            error = errors[i][j] if j < len(output) else math.inf
            wrong_style = j >= len(output) or target[i]['dashed'] != output[j]['dashed']
            candidates.append((failures + int(error > REL_TOL), style + int(wrong_style),
                               residual + error, (j,) + tail))
        return min(candidates)

    return assign(0, 0)



def _line_position(a: np.ndarray, b: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    vector, offset = b - a, p - a
    squared = float(vector @ vector)
    if squared == 0:
        return math.inf, math.inf
    return float(offset @ vector / squared), abs(float(vector[0] * offset[1] - vector[1] * offset[0])) / squared


def _right_angles(scene: dict[str, Any], edges: list[dict]) -> set[tuple[str, str, str]]:
    """Bind a small square corner marker to its vertex and two painted named rays."""
    points = {name: np.asarray(p) for name, p in scene['points'].items()}
    junctions = {}
    for stroke in scene.get('strokes', []):
        for part in stroke.get('components', [stroke['geometry']]):
            if part.geom_type == 'LineString' and len(part.coords) == 2:
                a, b = map(tuple, part.coords)
                if a != b:
                    junctions.setdefault(a, set()).add(b)
                    junctions.setdefault(b, set()).add(a)
    angles = set()
    for corner, endpoints in junctions.items():
        corner = np.asarray(corner)
        for first, second in combinations(sorted(endpoints), 2):
            a, b = np.asarray(first), np.asarray(second)
            u, v = a - corner, b - corner
            size = max(np.linalg.norm(u), np.linalg.norm(v))
            if abs(float(u @ v)) > REL_TOL * np.linalg.norm(u) * np.linalg.norm(v):
                continue
            vertex = a + b - corner
            for name, p in points.items():
                if np.linalg.norm(vertex - p) > size * REL_TOL:
                    continue
                rays = []
                for endpoint in (a, b):
                    candidates = []
                    for edge in edges:
                        for other in edge['points']:
                            if other == name:
                                continue
                            q = points[other]
                            t, error = _line_position(p, q, endpoint)
                            e0, e1 = (points[label] for label in edge['points'])
                            base_t, base_error = _line_position(e0, e1, p)
                            if error <= REL_TOL and 0 < t < 0.5 and base_error <= REL_TOL and -REL_TOL <= base_t <= 1 + REL_TOL:
                                candidates.append((np.linalg.norm(q - p), other))
                    if candidates:
                        rays.append(max(candidates)[1])
                if len(rays) == 2 and rays[0] != rays[1]:
                    left, right = sorted(rays)
                    angles.add((left, name, right))
    return angles


def _circle_error(reference: dict, drawn: dict, points: dict, produced: dict, edges: list[dict]) -> float:
    """Compare a circle's relations, allowing its radius to follow changed free points."""
    center, other = np.asarray(reference['center']), np.asarray(drawn['center'])
    radius, actual_radius = reference['radius'], drawn['radius']
    errors = []
    for name, p in points.items():
        distance = np.linalg.norm(p - center) / radius
        if distance <= REL_TOL or abs(distance - 1) <= REL_TOL:
            actual = np.linalg.norm(produced[name] - other) / actual_radius if name in produced else math.inf
            errors.append(float(actual if distance <= REL_TOL else abs(actual - 1)))
    for a, b in combinations(points, 2):
        if abs(np.linalg.norm(points[b] - points[a]) / radius - 1) <= REL_TOL:
            errors.append(abs(np.linalg.norm(produced[b] - produced[a]) / actual_radius - 1)
                          if a in produced and b in produced else math.inf)
    for edge in edges:
        a, b = edge['points']
        _, error = _line_position(points[a], points[b], center)
        if abs(error * np.linalg.norm(points[b] - points[a]) / radius - 1) <= REL_TOL:
            if a not in produced or b not in produced:
                errors.append(math.inf)
            else:
                _, actual = _line_position(produced[a], produced[b], other)
                errors.append(abs(actual * np.linalg.norm(produced[b] - produced[a]) / actual_radius - 1)
                              if math.isfinite(actual) else math.inf)
    if not errors and points:
        raise ValueError('Reference circle has no named center, boundary point, radius segment or tangent')
    return float(max(errors, default=0.0))


def compare_geometry(target: dict[str, Any], output: dict[str, Any]) -> tuple[list[bool], list[int | None]]:
    """One vote per observed relation; all requirements come from the target alone."""
    points = {name: np.asarray(p, dtype=float) for name, p in target['points'].items()}
    produced = {name: np.asarray(p, dtype=float) for name, p in output['points'].items() if p is not None and name in points}
    pairs = list(combinations(sorted(points), 2))
    extent = max((np.linalg.norm(points[b] - points[a]) for a, b in pairs), default=0.0)
    actual_extent = max((np.linalg.norm(produced[b] - produced[a]) for a, b in pairs if a in produced and b in produced), default=0.0)
    checks = []
    for a, b in pairs:
        coincident = np.linalg.norm(points[b] - points[a]) <= extent * 1e-8
        checks.append(a in produced and b in produced and
                      (np.linalg.norm(produced[b] - produced[a]) <= actual_extent * 1e-8) == coincident)

    nondegenerate = []
    for names in combinations(points, 3):
        a, b = max(combinations(names, 2), key=lambda pair: np.linalg.norm(points[pair[1]] - points[pair[0]]))
        c = next(name for name in names if name not in (a, b))
        if np.linalg.norm(points[b] - points[a]) <= extent * 1e-8:
            continue
        t, error = _line_position(points[a], points[b], points[c])
        complete = all(name in produced for name in names)
        actual_t, actual_error = _line_position(produced[a], produced[b], produced[c]) if complete else (math.inf, math.inf)
        if error <= REL_TOL:
            # A midpoint is a relation; a generic foot's division ratio is not fixed.
            midpoint = abs(t - 0.5) <= REL_TOL
            checks.append(complete and actual_error <= REL_TOL and (not midpoint or abs(actual_t - 0.5) <= REL_TOL))
        else:
            nondegenerate.append(complete and math.isfinite(actual_error) and actual_error > 1e-6)
    if nondegenerate:
        checks.append(all(nondegenerate))

    edges = connections(target) if target.get('strokes') else []
    for edge in edges:
        a, b = edge['points']
        for name in points.keys() - {a, b}:
            t, error = _line_position(points[a], points[b], points[name])
            if error <= REL_TOL and 0 < t < 1:
                actual_t, actual_error = (_line_position(produced[a], produced[b], produced[name])
                                          if all(p in produced for p in (a, b, name)) else (math.inf, math.inf))
                checks.append(actual_error <= REL_TOL and -REL_TOL <= actual_t <= 1 + REL_TOL)
    for first, second in combinations(edges, 2):
        a, b = first['points']
        c, d = second['points']
        u, v = points[b] - points[a], points[d] - points[c]
        lengths = np.linalg.norm(u), np.linalg.norm(v)
        cross = abs(float(u[0] * v[1] - u[1] * v[0])) / (lengths[0] * lengths[1])
        if cross <= REL_TOL and _line_position(points[a], points[b], points[c])[1] > REL_TOL:
            if not all(name in produced for name in (a, b, c, d)):
                checks.append(False)
                continue
            actual_u, actual_v = produced[b] - produced[a], produced[d] - produced[c]
            actual_lengths = np.linalg.norm(actual_u), np.linalg.norm(actual_v)
            valid = min(actual_lengths) > 0
            if valid:
                valid = abs(float(actual_u[0] * actual_v[1] - actual_u[1] * actual_v[0])) <= REL_TOL * actual_lengths[0] * actual_lengths[1]
                if abs(lengths[0] / lengths[1] - 1) <= REL_TOL:
                    sign = 1 if float(u @ v) > 0 else -1
                    valid = valid and np.linalg.norm(actual_u - sign * actual_v) <= REL_TOL * max(actual_lengths)
            checks.append(bool(valid))
    for a, vertex, b in sorted(_right_angles(target, edges)):
        if not all(name in produced for name in (a, vertex, b)):
            checks.append(False)
            continue
        u, v = produced[a] - produced[vertex], produced[b] - produced[vertex]
        product = np.linalg.norm(u) * np.linalg.norm(v)
        checks.append(product > 0 and abs(float(u @ v)) <= REL_TOL * product)

    circles, drawn = target.get('circles', []), output.get('circles', [])
    if not circles:
        return [bool(check) for check in checks], []
    # ponytail: exact circle assignment is bounded to 12; use a polynomial solver if needed.
    if len(circles) > 12:
        raise ValueError('Reference exceeds the 12-circle matching limit')
    if len(circles) > 1 and extent == 0:
        raise ValueError('Multiple reference circles require two distinct named points')
    for circle in circles:
        _circle_error(circle, circle, points, points, edges)
    if len(drawn) > 12:
        return [bool(check) for check in checks] + [False] * len(circles), [None] * len(circles)
    errors = [[_circle_error(circle, item, points, produced, edges) for item in drawn] for circle in circles]
    indices = _assign_circles(errors, circles, drawn)[-1]
    matches = [j if j < len(drawn) else None for j in indices]
    checks += [j is not None and errors[i][j] <= REL_TOL for i, j in enumerate(matches)]
    return [bool(check) for check in checks], matches
