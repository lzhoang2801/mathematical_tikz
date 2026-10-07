"""Compare named points and painted solid/dashed connections and circles."""
from __future__ import annotations

from itertools import combinations
from typing import Any

from shapely.geometry import LineString
from shapely.ops import unary_union

PATH_TOLERANCE = 0.006
COVERAGE_MINIMUM = 0.985


def _segments(scene: dict[str, Any]) -> list[dict[str, Any]]:
    return [{**stroke, 'geometry': part} for stroke in scene['strokes']
            for part in stroke.get('components', [stroke['geometry']])
            if part.geom_type == 'LineString' and len(part.coords) == 2 and part.length > 0]


def _line(edge: dict[str, Any], points: dict[str, Any]) -> LineString | None:
    coordinates = [points.get(name) for name in edge['points']]
    if any(point is None for point in coordinates):
        return None
    line = LineString(coordinates)
    return line if line.length > 0 else None


def _fraction(line: LineString, support: Any) -> float:
    return min(1.0, line.intersection(support.buffer(line.length * PATH_TOLERANCE)).length / line.length)


def connections(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """Merge collinear painted pieces into maximal named connections of each style."""
    segments = _segments(scene)
    support = {dashed: unary_union([row['geometry'] for row in segments if row.get('dashed', False) == dashed])
               for dashed in (False, True)}
    candidates = []
    for names in combinations(sorted(scene['points']), 2):
        edge = {'points': names}
        line = _line(edge, scene['points'])
        if line is not None:
            for dashed in (False, True):
                if _fraction(line, support[dashed]) >= COVERAGE_MINIMUM:
                    candidates.append({**edge, 'dashed': dashed, 'geometry': line})
    result = []
    for edge in sorted(candidates, key=lambda row: row['geometry'].length, reverse=True):
        if not any(old['dashed'] == edge['dashed'] and _fraction(edge['geometry'], old['geometry']) >= COVERAGE_MINIMUM
                   for old in result):
            result.append(edge)
    return result


def carrier_scene(scene: dict[str, Any], reference_connections: list[dict[str, Any]]) -> dict[str, Any]:
    """Keep actual diagram carriers for collisions, excluding unrelated text rules."""
    lines = [_line(edge, scene['points']) for edge in reference_connections + connections(scene)]
    support = unary_union([line for line in lines if line is not None])
    strokes = [row for row in _segments(scene) if _fraction(row['geometry'], support) >= COVERAGE_MINIMUM]
    return {**scene, 'strokes': strokes + scene.get('curves', [])}


def compare_content(target: dict[str, Any], output: dict[str, Any], circle_matches: list[int | None]) -> list[bool]:
    """Target units plus extra observed objects form the coverage denominator."""
    points = output['points']
    checks = [points.get(name) is not None for name in target['points']]
    checks += [False] * len(points.keys() - target['points'].keys())
    segments = _segments(output)
    support = {dashed: unary_union([row['geometry'] for row in segments if row.get('dashed', False) == dashed])
               for dashed in (False, True)}
    expected = []
    for edge in connections(target):
        line = _line(edge, points)
        checks.append(line is not None and _fraction(line, support[edge['dashed']]) >= COVERAGE_MINIMUM)
        if line is not None:
            expected.append(line)
    expected_support = unary_union(expected)
    checks += [False for edge in connections(output) if _fraction(edge['geometry'], expected_support) < COVERAGE_MINIMUM]
    circles, drawn = target.get('circles', []), output.get('circles', [])
    checks += [j is not None and circles[i]['dashed'] == drawn[j]['dashed'] for i, j in enumerate(circle_matches)]
    checks += [False] * max(0, len(drawn) - len(circles))
    checks += [False] * len(output.get('unsupported', []))
    return checks
