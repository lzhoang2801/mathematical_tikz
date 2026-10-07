"""Separate constructed-object geometry from point and stroke coverage."""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from shapely.geometry import LineString
from shapely.ops import unary_union

from evaluation.tikz_geometry import REL_TOL

PATH_TOLERANCE = 0.006
COVERAGE_MINIMUM = 0.985


def _status(states: list[str]) -> str:
    return "different" if "different" in states else "unknown" if "unknown" in states else "match"


def _segments(scene: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {**stroke, "geometry": part}
        for stroke in scene["strokes"]
        for part in stroke.get("components", [stroke["geometry"]])
        if part.geom_type == "LineString" and len(part.coords) == 2 and part.length > 0
    ]


def _bound_edges(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """Bind actual endpoints, without inferring incidental point-on-line givens."""
    edges = []
    for segment in _segments(scene):
        endpoints = []
        for xy in segment["geometry"].coords:
            matches = [name for name, point in scene["points"].items()
                       if point is not None and math.dist(xy, point) <= min(0.1, segment["geometry"].length * 0.001)]
            if len(matches) != 1:
                break
            endpoints.append(matches[0])
        if len(endpoints) == 2 and endpoints[0] != endpoints[1]:
            edges.append({"kind": "segment", "points": sorted(endpoints), "dashed": segment.get("dashed", False)})
    return edges


def content_contract(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """The reviewed target supplies point/segment identities and circle presence, not inferred circle givens."""
    points = [{"kind": "point", "points": [name]} for name in sorted(scene["points"])]
    edges = {(tuple(row["points"]), row["dashed"]) for row in _bound_edges(scene)}
    return (points + [{"kind": "segment", "points": list(names), "dashed": dashed} for names, dashed in sorted(edges)]
            + [{"kind": "circle", "dashed": circle["dashed"]} for circle in scene.get("circles", [])])


def _line(requirement: dict[str, Any], points: dict[str, Any]) -> LineString:
    names = requirement.get("points")
    if requirement.get("kind") != "segment" or not isinstance(names, list) or len(names) != 2:
        raise ValueError("A connection requires two named points")
    if not isinstance(requirement.get("dashed", False), bool):
        raise ValueError("The dashed flag must be Boolean")
    if set(requirement) - {"kind", "points", "dashed"}:
        raise ValueError("Only point identity and solid/dashed connections are in scope")
    if any(not isinstance(name, str) or not name or points.get(name) is None for name in names):
        raise ValueError("A required point binding is unavailable")
    coordinates = [points[name] for name in names]
    if any(len(point) != 2 or not all(math.isfinite(value) for value in point) for point in coordinates):
        raise ValueError("A required point binding is invalid")
    line = LineString(coordinates)
    if line.length == 0:
        raise ValueError("A required connection has coincident endpoints")
    return line


def _fraction(line: LineString, support: Any) -> float:
    return min(1.0, line.intersection(support.buffer(line.length * PATH_TOLERANCE)).length / line.length)


def carrier_scene(scene: dict[str, Any], contract: list[dict[str, Any]]) -> dict[str, Any]:
    """Keep actual carrier strokes for text collisions, excluding unrelated text rules."""
    lines = []
    for requirement in contract + _bound_edges(scene):
        if requirement.get("kind") != "segment":
            continue
        try:
            lines.append(_line(requirement, scene["points"]))
        except (TypeError, ValueError, OverflowError):
            continue
    support = unary_union(lines)
    strokes = [stroke for stroke in _segments(scene) if _fraction(stroke["geometry"], support) >= COVERAGE_MINIMUM]
    return {**scene, "strokes": strokes + scene.get("curves", [])}



def _circles(contract: list[dict[str, Any]], scene: dict[str, Any], geometry_space: str) -> dict[str, Any]:
    """Bind distinct emitted circles to frozen constructions in this scene's frame."""
    requested = [row for row in contract if row.get("kind") == "circle"]
    observed = scene.get("circles", [])
    size = max(len(requested), len(observed))
    uncertain = bool(scene.get("unsupported"))
    # ponytail: exact assignment is bounded to 12 circles; use a polynomial solver if real cases exceed this.
    if size > 12:
        return {"status": "unknown", "mathematical_status": "unknown",
                "required_count": len(requested), "observed_count": len(observed),
                "requirements": [{"requirement": row, "status": "unknown", "mathematical_status": "unknown",
                                  "residual": None, "tolerance": REL_TOL, "reason": "Circle assignment limit exceeded (12)"}
                                 for row in requested]}
    definitions = []
    for row in requested:
        names = row.get("points", [])
        try:
            if geometry_space != "euclidean_2d" or len(names) != 2:
                raise ValueError("A Euclidean circle requires explicit center and radius-witness points")
            center, witness = [scene["points"][name] for name in names]
            radius = math.dist(center, witness)
            if not math.isfinite(radius) or radius <= 0:
                raise ValueError("Circle radius is degenerate")
            definitions.append((center, radius))
        except (KeyError, TypeError, ValueError, OverflowError):
            definitions.append(None)
    costs = {}
    for i in range(size):
        for j in range(size):
            error = 0.0
            style_error = 0
            if i < len(requested) and j < len(observed):
                definition = definitions[i]
                if definition is not None:
                    center, radius = definition
                    error = max(math.dist(center, observed[j]["center"]) / radius, abs(observed[j]["radius"] / radius - 1))
                if not math.isfinite(error):
                    definitions[i] = None
                    error = 0.0
                style_error = int(requested[i].get("dashed", False) != observed[j]["dashed"])
            costs[i, j] = (error, style_error)

    @lru_cache(maxsize=None)
    def assign(i: int, used: int) -> tuple[int, int, float, tuple[int, ...]]:
        if i == size:
            return 0, 0, 0.0, ()
        candidates = []
        for j in range(size):
            if not used & (1 << j):
                failures, remaining_style, remaining_error, remaining = assign(i + 1, used | (1 << j))
                error, style_error = costs[i, j]
                candidates.append((int(error > REL_TOL) + failures, style_error + remaining_style,
                                   error + remaining_error, (j,) + remaining))
        return min(candidates)

    _, _, _, assignment = assign(0, 0)
    rows = []
    for i, declaration in enumerate(requested):
        j = assignment[i]
        circle = observed[j] if j < len(observed) else None
        residual = costs[i, j][0] if circle is not None and definitions[i] is not None else None
        math_status = ("unknown" if residual is None or uncertain else "match" if residual <= REL_TOL else "different")
        coverage = ("different" if circle is None or circle["dashed"] != declaration.get("dashed", False) else "match")
        rows.append({"requirement": declaration, "status": "unknown" if uncertain else coverage,
                     "mathematical_status": math_status, "residual": residual, "tolerance": REL_TOL,
                     "observed": circle, "reason": "Construction or curve evidence unavailable" if math_status == "unknown" else None})
    count_status = ("different" if len(observed) > len(requested) else "unknown" if uncertain else
                    "different" if len(observed) < len(requested) else "match")
    return {"status": _status([count_status, *[row["status"] for row in rows]]),
            "mathematical_status": _status([row["mathematical_status"] for row in rows]),
            "required_count": len(requested), "observed_count": len(observed), "requirements": rows}


def compare_content(
    target: dict[str, Any], output: dict[str, Any], *,
    content_requirements: list[dict[str, Any]] | None = None,
    geometry_space: str = "euclidean_2d",
) -> dict[str, Any]:
    """Check the same point/connection contract in the output's own coordinates."""
    contract = content_contract(target) if content_requirements is None else content_requirements
    if not isinstance(contract, list) or not all(isinstance(row, dict) for row in contract):
        raise TypeError("content_requirements must be a list of point, segment or circle declarations")
    required, invalid, normalized, seen = set(), [], [], set()
    for row in contract:
        kind = row.get("kind")
        names = row.get("points", [] if kind == "circle" else None)
        arity = {"point": 1, "segment": 2, "circle": 2 if names else 0}.get(kind) if isinstance(kind, str) else None
        if (not isinstance(names, list) or len(names) != arity
                or any(not isinstance(name, str) or not name for name in names)
                or set(row) - ({"kind", "points"} if kind == "point" else {"kind", "points", "dashed"})
                or (kind != "point" and not isinstance(row.get("dashed", False), bool))):
            invalid.append(len(normalized))
        else:
            key = (kind, tuple(sorted(names) if kind == "segment" else names), row.get("dashed", False))
            if names and key in seen:
                continue
            seen.add(key)
            required.update(names)
        normalized.append(row)
    contract = normalized
    missing = sorted(required - output["points"].keys())
    extra = sorted(output["points"].keys() - required)
    unresolved = sorted(name for name in required & output["points"].keys() if output["points"][name] is None)
    points = {"status": "different" if missing or extra else "unknown" if unresolved or invalid else "match",
              "required": sorted(required), "missing": missing, "extra": extra, "unresolved": unresolved}
    segments = _segments(output)
    support = {dashed: unary_union([row["geometry"] for row in segments if row.get("dashed", False) == dashed])
               for dashed in (False, True)}
    expected = {False: [], True: []}
    rows = []
    for index, declaration in enumerate(contract):
        if declaration.get("kind") == "circle" or (declaration.get("kind") == "point" and index not in invalid):
            continue
        row = {"id": index, "requirement": declaration}
        try:
            if index in invalid:
                raise ValueError("Unsupported point/connection declaration")
            line = _line(declaration, output["points"])
            dashed = declaration.get("dashed", False)
            expected[dashed].append(line)
            fraction = _fraction(line, support[dashed])
            row.update(status="match" if fraction >= COVERAGE_MINIMUM else "different", covered_fraction=fraction)
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            row.update(status="unknown", reason=str(error))
        rows.append(row)
    extras = []
    for edge in _bound_edges(output):
        line = _line(edge, output["points"])
        fraction = _fraction(line, unary_union(expected[False] + expected[True]))
        if fraction < COVERAGE_MINIMUM and edge not in extras:
            extras.append(edge)
    uncertain = invalid or unresolved or any(row["status"] == "unknown" for row in rows)
    connections = {
        "status": _status([row["status"] for row in rows] + (["unknown" if uncertain else "different"] if extras else [])),
        "requirements": rows, "extra_connections": extras,
    }
    limitations = output.get("unsupported", [])
    circles = _circles([row for i, row in enumerate(contract) if i not in invalid], output, geometry_space)
    target_circles = _circles([row for i, row in enumerate(contract) if i not in invalid], target, geometry_space)
    for index in invalid:
        if contract[index].get("kind") == "circle":
            for result in (circles, target_circles):
                result["status"] = result["mathematical_status"] = "unknown"
                result["required_count"] += 1
                result["requirements"].append({"requirement": contract[index], "status": "unknown", "mathematical_status": "unknown",
                                               "residual": None, "tolerance": REL_TOL, "reason": "Unsupported circle declaration"})
    checks = {"points": points, "connections": connections, "circles": circles}
    return {"status": _status([row["status"] for row in checks.values()] + (["unknown"] if limitations else [])),
            "checks": checks, "contract": contract, "limitations": limitations,
            "target_circles": target_circles}
