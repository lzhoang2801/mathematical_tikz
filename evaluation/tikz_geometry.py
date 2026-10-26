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
from evaluation.tikz_marks import REL_TOL, line_position as _line_position, mark_truth, observe_marks


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



def measure_circular_path(part: Sequence[tuple[float, float]]) -> dict[str, Any] | None:
    """Fit an emitted circle or circular arc, retaining its actual path interval."""
    if len(part) < 16:
        return None
    closed = LineString(part).is_ring
    raw = np.asarray(part[:-1] if closed else part, dtype=float)
    origin = raw.mean(axis=0)
    scale = float(np.max(np.abs(raw - origin)))
    if not math.isfinite(scale) or scale <= 0:
        return None
    xy = (raw - origin) / scale
    try:
        parameters, _, rank, _ = np.linalg.lstsq(np.column_stack((2 * xy, np.ones(len(xy)))), (xy * xy).sum(axis=1), rcond=None)
    except np.linalg.LinAlgError as error:
        raise ValueError("Circular path measurement did not converge") from error
    radius_squared = float(parameters[2] + parameters[:2] @ parameters[:2])
    if rank != 3 or radius_squared <= 0:
        return None
    radius = math.sqrt(radius_squared)
    # Test chord interiors as well: a sparse polygon is not a circular stroke.
    adjacent = np.concatenate((xy, xy[:1])) if closed else xy
    samples = np.concatenate((xy, (adjacent[:-1] + adjacent[1:]) / 2))
    residual = float(np.max(np.abs(np.linalg.norm(samples - parameters[:2], axis=1) / radius - 1)))
    angles = np.unwrap(np.arctan2(adjacent[:, 1] - parameters[1], adjacent[:, 0] - parameters[0]))
    sweep = float(angles[-1] - angles[0])
    if (not math.isfinite(residual) or residual > REL_TOL or abs(sweep) < math.pi / 12
            or abs(sweep) > 2 * math.pi + REL_TOL or np.any(np.diff(angles) * sweep < -1e-8)):
        return None
    return {"center": (origin + parameters[:2] * scale).tolist(), "radius": radius * scale,
            "closed": closed, "start": list(part[0]), "end": list(part[-1]), "sweep": sweep,
            "radial_residual": residual}


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



def _arc_position(path: dict, point: np.ndarray) -> float:
    """Fraction along a measured arc; endpoint tolerance is symmetric at the wrap."""
    center = np.asarray(path['center'])
    start, offset = np.asarray(path['start']) - center, point - center
    angle = math.atan2(float(start[0] * offset[1] - start[1] * offset[0]), float(start @ offset))
    angle *= 1 if path['sweep'] > 0 else -1
    if angle < -REL_TOL:
        angle += 2 * math.pi
    return angle / abs(path['sweep'])


def _circular_error(reference: dict, drawn: dict, points: dict, produced: dict, edges: list[dict]) -> float:
    """A circular object's relations may follow moving free points."""
    if reference.get('closed', True) != drawn.get('closed', True):
        return math.inf
    center, other = np.asarray(reference['center']), np.asarray(drawn['center'])
    radius, actual_radius = reference['radius'], drawn['radius']
    errors, boundary = [], []
    for name, p in points.items():
        distance = np.linalg.norm(p - center) / radius
        on_arc = reference.get('closed', True) or -REL_TOL <= _arc_position(reference, p) <= 1 + REL_TOL
        if distance <= REL_TOL or (abs(distance - 1) <= REL_TOL and on_arc):
            actual = np.linalg.norm(produced[name] - other) / actual_radius if name in produced else math.inf
            errors.append(float(actual if distance <= REL_TOL else abs(actual - 1)))
            if distance > REL_TOL:
                boundary.append(name)
    for a, b in combinations(points, 2):
        if abs(np.linalg.norm(points[b] - points[a]) / radius - 1) <= REL_TOL:
            errors.append(abs(np.linalg.norm(produced[b] - produced[a]) / actual_radius - 1)
                          if a in produced and b in produced else math.inf)
    for edge in edges:
        a, b = edge['points']
        t, error = _line_position(points[a], points[b], center)
        foot = points[a] + t * (points[b] - points[a])
        on_arc = reference.get('closed', True) or -REL_TOL <= _arc_position(reference, foot) <= 1 + REL_TOL
        if on_arc and abs(error * np.linalg.norm(points[b] - points[a]) / radius - 1) <= REL_TOL:
            if a not in produced or b not in produced:
                errors.append(math.inf)
            else:
                actual_t, actual = _line_position(produced[a], produced[b], other)
                errors.append(abs(actual * np.linalg.norm(produced[b] - produced[a]) / actual_radius - 1)
                              if math.isfinite(actual) else math.inf)
                if not drawn.get('closed', True) and math.isfinite(actual_t):
                    position = _arc_position(drawn, produced[a] + actual_t * (produced[b] - produced[a]))
                    errors.append(max(0, -position, position - 1))
    if not reference.get('closed', True):
        endpoints = [sorted(name for name, p in points.items()
                            if np.linalg.norm(p - reference[end]) / radius <= REL_TOL) for end in ('start', 'end')]
        if not all(endpoints):
            raise ValueError('Reference arc endpoints must be bound to named points')
        if not all(names[0] in produced for names in endpoints):
            return math.inf
        a, b = (produced[names[0]] for names in endpoints)
        direct = max(np.linalg.norm(a - drawn['start']), np.linalg.norm(b - drawn['end']))
        reverse = max(np.linalg.norm(a - drawn['end']), np.linalg.norm(b - drawn['start']))
        errors.append(min(direct, reverse) / actual_radius)
        order = sorted(boundary, key=lambda name: _arc_position(reference, points[name]))
        if any(name not in produced for name in order):
            return math.inf
        positions = [_arc_position(drawn, produced[name]) for name in order]
        if reverse < direct:
            positions = [1 - position for position in positions]
        errors += [max(0, -position, position - 1) for position in positions]
        errors += [max(0, a - b) for a, b in zip(positions, positions[1:])]
        expected_span, actual_span = abs(reference['sweep']) - math.pi, abs(drawn['sweep']) - math.pi
        if abs(expected_span) <= REL_TOL:
            errors.append(abs(actual_span))
        elif expected_span * actual_span <= 0:
            errors.append(math.inf)
    if not errors and points:
        raise ValueError('Reference circular path has no named center, boundary point, radius segment or tangent')
    return float(max(errors, default=0.0))


def _line_groups(points: dict[str, np.ndarray]) -> list[tuple[str, ...]]:
    """One maximal named line, regardless of path splitting or the number of triples."""
    groups = set()
    for a, b in combinations(points, 2):
        if np.linalg.norm(points[b] - points[a]) == 0:
            continue
        names = frozenset(name for name, p in points.items() if _line_position(points[a], points[b], p)[1] <= REL_TOL)
        if len(names) >= 3:
            groups.add(names)
    return sorted(tuple(sorted(group)) for group in groups if not any(group < other for other in groups))


def compare_geometry(target: dict[str, Any], output: dict[str, Any]) -> tuple[list[bool], list[int | None]]:
    """Canonical target relations, with degeneracy checked inside each relation."""
    points = {name: np.asarray(p, dtype=float) for name, p in target['points'].items()}
    produced = {name: np.asarray(p, dtype=float) for name, p in output['points'].items() if p is not None and name in points}
    pairs = list(combinations(sorted(points), 2))
    extent = max((np.linalg.norm(points[b] - points[a]) for a, b in pairs), default=0.0)
    actual_extent = max((np.linalg.norm(produced[b] - produced[a]) for a, b in pairs if a in produced and b in produced), default=0.0)
    checks = []
    coincident = {frozenset(name for name, q in points.items() if np.linalg.norm(p - q) <= extent * 1e-8)
                  for p in points.values()}
    for names in sorted(tuple(sorted(group)) for group in coincident if len(group) > 1):
        checks.append(all(name in produced for name in names) and
                      all(np.linalg.norm(produced[b] - produced[a]) <= actual_extent * 1e-8
                          for a, b in combinations(names, 2)))

    edges = connections(target) if target.get('strokes') else []
    for names in _line_groups(points):
        complete = all(name in produced for name in names)
        on_line = False
        if complete:
            a, b = max(combinations(names, 2), key=lambda pair: np.linalg.norm(produced[pair[1]] - produced[pair[0]]))
            on_line = all(_line_position(produced[a], produced[b], produced[name])[1] <= REL_TOL for name in names)
        # Keep segment membership, but do not freeze the total order of free feet.
        for edge in edges:
            u, v = edge['points']
            if u not in names or v not in names:
                continue
            for name in set(names) - {u, v}:
                position, _ = _line_position(points[u], points[v], points[name])
                if 1e-8 < position < 1 - 1e-8:
                    actual, _ = _line_position(produced[u], produced[v], produced[name]) if complete else (math.inf, math.inf)
                    on_line = on_line and 1e-8 < actual < 1 - 1e-8
        checks.append(on_line)
        for u, v in combinations(names, 2):
            if np.linalg.norm(points[v] - points[u]) <= extent * 1e-8:
                continue
            for name in set(names) - {u, v}:
                if np.linalg.norm(2 * points[name] - points[u] - points[v]) <= REL_TOL * np.linalg.norm(points[v] - points[u]):
                    checks.append(all(n in produced for n in (u, v, name)) and
                                  np.linalg.norm(produced[v] - produced[u]) > actual_extent * 1e-8 and
                                  np.linalg.norm(2 * produced[name] - produced[u] - produced[v]) <=
                                  REL_TOL * np.linalg.norm(produced[v] - produced[u]))

    directions = []
    for names in sorted({tuple(edge['points']) for edge in edges}):
        a, b = names
        vector = points[b] - points[a]
        unit = vector / np.linalg.norm(vector)
        for group in directions:
            u, v = group[0]
            other = points[v] - points[u]
            if abs(float(unit[0] * other[1] - unit[1] * other[0])) <= REL_TOL * np.linalg.norm(other):
                group.append(names)
                break
        else:
            directions.append([names])
    for group in directions:
        if len(group) < 2:
            continue
        a, b = group[0]
        if all(_line_position(points[a], points[b], points[u])[1] <= REL_TOL for u, _ in group):
            continue
        vectors = [produced[v] - produced[u] if u in produced and v in produced else np.zeros(2) for u, v in group]
        lengths = [np.linalg.norm(vector) for vector in vectors]
        checks.append(min(lengths) > 0 and all(abs(float(vectors[0][0] * v[1] - vectors[0][1] * v[0])) <=
                                               REL_TOL * lengths[0] * length for v, length in zip(vectors[1:], lengths[1:])))
        equal_groups = []
        for index, (u, v) in enumerate(group):
            length = np.linalg.norm(points[v] - points[u])
            for expected, indices in equal_groups:
                if abs(length / expected - 1) <= REL_TOL:
                    indices.append(index)
                    break
            else:
                equal_groups.append((length, [index]))
        for _, indices in equal_groups:
            if len(indices) > 1:
                anchor = indices[0]
                a, b = group[anchor]
                expected = points[b] - points[a]
                equal = min(lengths[i] for i in indices) > 0
                for index in indices[1:]:
                    u, v = group[index]
                    sign = 1 if expected @ (points[v] - points[u]) > 0 else -1
                    equal = equal and np.linalg.norm(vectors[index] - sign * vectors[anchor]) <= REL_TOL * max(lengths[index], lengths[anchor])
                checks.append(equal)

    marks = observe_marks(target, edges)
    if marks['unresolved']:
        raise ValueError('Reference equality marks are not uniquely bound to painted named segments')
    if not all(mark_truth(marks, points)):
        raise ValueError('Reference relation marks contradict its measured geometry')
    checks.extend(mark_truth(marks, produced))

    circles = target.get('circles', []) + target.get('arcs', [])
    drawn = output.get('circles', []) + output.get('arcs', [])
    matches = []
    if circles:
        # shortcut: exact assignment is bounded to 12 objects; use a polynomial solver for larger scenes.
        if len(circles) > 12:
            raise ValueError('Reference exceeds the 12-circular-path matching limit')
        if len(circles) > 1 and extent == 0:
            raise ValueError('Multiple reference circular paths require two distinct named points')
        for circle in circles:
            _circular_error(circle, circle, points, points, edges)
        if len(drawn) > 12:
            matches = [None] * len(circles)
            checks += [False] * len(circles)
        else:
            errors = [[_circular_error(circle, item, points, produced, edges) for item in drawn] for circle in circles]
            matches = [j if j < len(drawn) else None for j in _assign_circles(errors, circles, drawn)[-1]]
            checks += [j is not None and errors[i][j] <= REL_TOL for i, j in enumerate(matches)]
    if not checks and points:
        expected = np.array(list(points.values()))
        actual = np.array(list(produced.values()))
        complete = len(actual) == len(expected)
        checks = [complete and np.linalg.matrix_rank(actual - actual[0], tol=actual_extent * 1e-8) >=
                  np.linalg.matrix_rank(expected - expected[0], tol=extent * 1e-8)]
    drawn_marks = observe_marks(output, connections(output) if output.get('strokes') else [])
    checks += [False for valid in mark_truth(drawn_marks, output['points']) if not valid]
    checks += [False] * len(drawn_marks['unresolved'])
    return [bool(check) for check in checks], matches
