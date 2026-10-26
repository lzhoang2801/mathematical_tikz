"""Bind painted relation marks to named carriers, independently of their truth."""
from __future__ import annotations

import math
from itertools import combinations

import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

REL_TOL = 0.005


def line_position(a: np.ndarray, b: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    vector, offset = b - a, p - a
    squared = float(vector @ vector)
    if squared == 0:
        return math.inf, math.inf
    return float(offset @ vector / squared), abs(float(vector[0] * offset[1] - vector[1] * offset[0])) / squared


def corner_marks(scene: dict, edges: list[dict]) -> tuple[set[tuple[str, str, str]], set[tuple]]:
    """Find small two-leg corner marks, including visibly non-right corners."""
    points = {name: np.asarray(p) for name, p in scene['points'].items() if p is not None}
    junctions = {}
    font = max((label.get('size', 10.0) for label in scene.get('text', [])), default=math.inf)
    for stroke in scene.get('strokes', []):
        for part in stroke.get('components', [stroke['geometry']]):
            if part.geom_type == 'LineString' and len(part.coords) == 2:
                a, b = map(tuple, part.coords)
                if a != b:
                    junctions.setdefault(a, set()).add(b)
                    junctions.setdefault(b, set()).add(a)
    angles, legs = set(), set()
    for corner, endpoints in junctions.items():
        corner = np.asarray(corner)
        for first, second in combinations(sorted(endpoints), 2):
            a, b = np.asarray(first), np.asarray(second)
            u, v = a - corner, b - corner
            size, product = max(np.linalg.norm(u), np.linalg.norm(v)), np.linalg.norm(u) * np.linalg.norm(v)
            # Collinear paint cannot distinguish a collapsed pic from an ordinary split line.
            if size > 2 * font or abs(float(u[0] * v[1] - u[1] * v[0])) <= REL_TOL * product:
                continue
            if any(min(np.linalg.norm(a - p), np.linalg.norm(b - p)) <= size * REL_TOL for p in points.values()):
                continue
            vertex = a + b - corner
            for name, p in points.items():
                if np.linalg.norm(vertex - p) > size * REL_TOL:
                    continue
                rays = []
                for endpoint in (a, b):
                    candidates = []
                    for edge in edges:
                        e0, e1 = (points[label] for label in edge['points'])
                        base_t, base_error = line_position(e0, e1, p)
                        if base_error > REL_TOL or not -REL_TOL <= base_t <= 1 + REL_TOL:
                            continue
                        for other in edge['points']:
                            if other == name:
                                continue
                            t, error = line_position(p, points[other], endpoint)
                            if error <= REL_TOL and 0 < t < 0.5:
                                candidates.append((np.linalg.norm(points[other] - p), other))
                    if candidates:
                        rays.append(max(candidates)[1])
                if len(rays) == 2 and rays[0] != rays[1]:
                    left, right = sorted(rays)
                    angles.add((left, name, right))
                    legs.update(tuple(sorted((tuple(corner), tuple(endpoint)))) for endpoint in (a, b))
    return angles, legs


def perpendicular(angle: tuple[str, str, str], points: dict) -> bool:
    if any(points.get(name) is None for name in angle):
        return False
    a, vertex, b = (np.asarray(points[name]) for name in angle)
    u, v = a - vertex, b - vertex
    product = np.linalg.norm(u) * np.linalg.norm(v)
    return bool(product > 0 and abs(float(u @ v)) <= REL_TOL * product)


def right_angles(scene: dict, edges: list[dict]) -> set[tuple[str, str, str]]:
    return {angle for angle in corner_marks(scene, edges)[0] if perpendicular(angle, scene['points'])}


def same_angle(expected: tuple[str, str, str], actual: tuple[str, str, str], points: dict) -> bool:
    a, vertex, b = expected
    u, other, v = actual
    if vertex != other or any(points.get(name) is None for name in (*expected, *actual)):
        return False
    def same_ray(first, second):
        x, y = np.asarray(points[first]) - points[vertex], np.asarray(points[second]) - points[vertex]
        product = np.linalg.norm(x) * np.linalg.norm(y)
        return product > 0 and float(x @ y) / product > 1 - REL_TOL**2
    return bool((same_ray(a, u) and same_ray(b, v)) or (same_ray(a, v) and same_ray(b, u)))


def observe_marks(scene: dict, edges: list[dict]) -> dict:
    angles, corner_legs = corner_marks(scene, edges)
    points = {name: np.asarray(p) for name, p in scene['points'].items() if p is not None}
    support = unary_union([edge['geometry'] for edge in edges])
    segments = {}
    for a, b in combinations(sorted(points), 2):
        line = LineString([points[a], points[b]])
        if line.length and line.intersection(support.buffer(line.length * REL_TOL)).length / line.length >= 0.985:
            segments[(a, b)] = line
    def carriers(ink, center, axes, size):
        candidates = {}
        for names, line in segments.items():
            a, b = (points[name] for name in names)
            t, error = line_position(a, b, center)
            direction = (b - a) / line.length
            if (0 < t < 1 and error * line.length <= size * 0.2
                    and ink.distance(line) <= size * 0.02
                    and all(abs(float(axis @ direction)) < 0.3 for axis in axes)):
                candidates[names] = line
        # At subdivided sides, use the shortest centered interval; otherwise keep ambiguity.
        if len(candidates) > 1:
            centered = {names: line for names, line in candidates.items()
                        if np.linalg.norm(center - line.interpolate(0.5, normalized=True).coords[0]) <= size * 0.2}
            if centered:
                candidates = {names: line for names, line in centered.items() if not any(
                    other.length < line.length * (1 - REL_TOL)
                    and other.difference(line.buffer(line.length * REL_TOL)).length < other.length * REL_TOL
                    for key, other in centered.items() if key != names)}
        return candidates

    groups, unresolved = {}, []
    for index, label in enumerate(scene.get('text', [])):
        text = ''.join(label['text'].split()).replace('\u2223', '|').replace('\u2016', '||')
        if not text or set(text) != {'|'}:
            continue
        boxes, ink = label.get('boxes', []), label.get('region')
        if not boxes or ink is None or ink.is_empty:
            unresolved.append(index)
            continue
        center = np.array(ink.centroid.coords[0])
        axes = []
        for box in boxes:
            axis = np.asarray(box['corners'][0]) - box['corners'][2]
            if np.linalg.norm(axis):
                axes.append(axis / np.linalg.norm(axis))
        if not axes:
            unresolved.append(index)
            continue
        candidates = carriers(ink, center, axes, label['size'])
        if len(candidates) != 1:
            unresolved.append(index)
        else:
            groups.setdefault(len(text), set()).add(next(iter(candidates)))
    ticks = {}
    font = max((label.get('size', 10.0) for label in scene.get('text', [])), default=10.0)
    for index, stroke in enumerate(scene.get('strokes', [])):
        if stroke.get('dashed', False):
            continue
        for part_index, part in enumerate(stroke.get('components', [stroke['geometry']])):
            if part.geom_type != 'LineString' or len(part.coords) != 2 or not 0 < part.length <= 2 * font:
                continue
            # A corner leg can cross a diagonal without asserting equal lengths.
            if tuple(sorted(part.coords)) in corner_legs:
                continue
            a, b = map(np.asarray, part.coords)
            if any(min(np.linalg.norm(a - p), np.linalg.norm(b - p)) <= part.length * REL_TOL for p in points.values()):
                continue
            candidates = carriers(part, (a + b) / 2, [(b - a) / part.length], font)
            # A tick crosses its carrier; a corner leg only meets it at an endpoint.
            candidates = {names: line for names, line in candidates.items()
                          if part.crosses(line) and all(line.distance(Point(p)) > part.length * 0.1 for p in (a, b))}
            if len(candidates) > 1:
                unresolved.append(f'stroke:{index}:{part_index}')
            elif candidates:
                parts = ticks.setdefault(next(iter(candidates)), [])
                if not any(part.equals(other) for other in parts):
                    parts.append(part)
    for names, parts in ticks.items():
        clusters = []
        for part in parts:
            touching = [group for group in clusters if any(
                part.centroid.distance(other.centroid) <= 0.75 * min(part.length, other.length)
                for other in group)]
            merged = [part]
            for group in touching:
                merged.extend(group)
                clusters.remove(group)
            clusters.append(merged)
        for group in clusters:
            groups.setdefault(len(group), set()).add(names)
    return {'right_angles': angles, 'equal_segments': list(groups.values()), 'unresolved': unresolved}


def equal_lengths(group: set[tuple[str, str]], points: dict) -> bool:
    if any(points.get(name) is None for segment in group for name in segment):
        return False
    lengths = [np.linalg.norm(np.asarray(points[a]) - points[b]) for a, b in group]
    return bool(lengths and min(lengths) > 0 and max(lengths) - min(lengths) <= REL_TOL * max(lengths))


def mark_truth(marks: dict, points: dict) -> list[bool]:
    return ([perpendicular(angle, points) for angle in sorted(marks['right_angles'])]
            + [equal_lengths(group, points) for group in marks['equal_segments']])


def compare_mark_content(expected: dict, actual: dict, points: dict) -> list[bool]:
    if expected['unresolved']:
        raise ValueError('Reference equality marks are not uniquely bound to painted named segments')
    checks = [any(same_angle(angle, other, points) for other in actual['right_angles']) for angle in sorted(expected['right_angles'])]
    checks += [False for angle in actual['right_angles'] if not any(same_angle(other, angle, points) for other in expected['right_angles'])]
    checks += [group in actual['equal_segments'] for group in expected['equal_segments']]
    checks += [False for group in actual['equal_segments'] if group not in expected['equal_segments']]
    checks += [False] * len(actual['unresolved'])
    return checks
