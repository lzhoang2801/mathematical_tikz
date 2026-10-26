"""Executable authoring requirements; separate from target/output similarity scores."""
from __future__ import annotations

import math
import re
from itertools import combinations
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from shapely.geometry import LineString
from shapely.ops import unary_union

from evaluation.tikz_coverage import COVERAGE_MINIMUM, PATH_TOLERANCE, connections
from evaluation.tikz_marks import mark_truth, observe_marks, same_angle
from evaluation.tikz_readability import inspect_readability


class Relation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    kind: Literal['midpoint', 'on_line', 'on_segment', 'on_ray', 'between', 'perpendicular',
                  'parallel', 'equal_length', 'length_ratio', 'shorter', 'angle', 'on_circle', 'distinct',
                  'equal_angle', 'inside_angle', 'same_side', 'opposite_side', 'noncollinear',
                  'noncoplanar', 'on_plane', 'perpendicular_plane', 'parallel_plane', 'equal_vector', 'inside_triangle',
                  'perpendicular_planes', 'plane_angle', 'dihedral_angle']
    points: list[str] = Field(min_length=2, max_length=6)
    value: float | None = Field(default=None, allow_inf_nan=False)
    role: Literal['given', 'construction', 'consequence'] = 'construction'

    @model_validator(mode='after')
    def arguments(self):
        count = 6 if self.kind in {'equal_angle','perpendicular_planes','plane_angle'} else 5 if self.kind in {
            'perpendicular_plane', 'parallel_plane'} else 2 if self.kind == 'distinct' else 4 if self.kind in {
            'perpendicular', 'parallel', 'equal_length', 'length_ratio', 'shorter',
            'inside_angle', 'same_side', 'opposite_side', 'noncoplanar', 'on_plane', 'equal_vector', 'inside_triangle','dihedral_angle'} else 3
        if len(self.points) != count:
            raise ValueError(f'{self.kind} needs {count} point names')
        if self.kind in {'equal_angle','perpendicular_planes','plane_angle'}:
            if len(set(self.points[:3])) != 3 or len(set(self.points[3:])) != 3:
                raise ValueError('Each angle or plane triple needs three distinct point names')
        elif count == 5:
            if self.points[0] == self.points[1] or len(set(self.points[2:])) != 3:
                raise ValueError('A line needs two distinct endpoints and a plane needs three distinct points')
        elif self.kind in {'inside_angle', 'same_side', 'opposite_side', 'noncoplanar', 'on_plane', 'inside_triangle','dihedral_angle'}:
            if len(set(self.points)) != 4:
                raise ValueError(f'{self.kind} needs four distinct point names')
        elif count == 4:
            if self.points[0] == self.points[1] or self.points[2] == self.points[3]:
                raise ValueError('Both carriers must have distinct endpoints')
        elif len(set(self.points)) != count:
            raise ValueError(f'{self.kind} needs distinct point names')
        numeric = self.kind in {'length_ratio', 'angle','plane_angle','dihedral_angle'}
        if numeric != (self.value is not None):
            raise ValueError('Only length_ratio, angle, plane_angle and dihedral_angle require a numeric value')
        if self.value is not None and (self.value <= 0 or self.kind in {'angle','dihedral_angle'} and self.value >= 180 or self.kind=='plane_angle' and self.value>90):
            raise ValueError('Ratios must be positive; angles must be strictly between 0 and 180 degrees; full-plane angles cannot exceed 90 degrees')
        return self


class Segment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    points: tuple[str, str]
    dashed: bool = False
    arrow: bool = False


class Circle(BaseModel):
    model_config = ConfigDict(extra='forbid')
    center: str
    through: str
    dashed: bool = False


class AngleMark(BaseModel):
    model_config = ConfigDict(extra='forbid')
    points: tuple[str, str, str]
    value: float = Field(gt=0, lt=180, allow_inf_nan=False)


class Requirements(BaseModel):
    model_config = ConfigDict(extra='forbid')
    relations: list[Relation] = Field(min_length=1)
    points: list[str] = Field(min_length=2)
    segments: list[Segment] = Field(default_factory=list)
    circles: list[Circle] = Field(default_factory=list)
    right_angles: list[tuple[str, str, str]] = Field(default_factory=list)
    equal_segments: list[list[tuple[str, str]]] = Field(default_factory=list, max_length=3)
    equal_angles: list[list[tuple[str, str, str]]] = Field(default_factory=list, max_length=3)
    angle_labels: list[AngleMark] = Field(default_factory=list)

    @model_validator(mode='after')
    def references(self):
        ids = [row.id for row in self.relations]
        if len(ids) != len(set(ids)) or len(self.points) != len(set(self.points)):
            raise ValueError('Requirement IDs and visible point names must be unique')
        referenced = {name for row in self.relations for name in row.points}
        referenced.update(name for row in self.segments for name in row.points)
        referenced.update(name for row in self.circles for name in (row.center, row.through))
        referenced.update(name for row in self.right_angles for name in row)
        referenced.update(name for group in self.equal_segments for segment in group for name in segment)
        referenced.update(name for group in self.equal_angles for angle in group for name in angle)
        referenced.update(name for angle in self.angle_labels for name in angle.points)
        if referenced - set(self.points):
            raise ValueError(f'Requirements reference unlisted points: {sorted(referenced - set(self.points))}')
        if any(a == b for a, b in (row.points for row in self.segments)):
            raise ValueError('A segment needs distinct endpoints')
        if any(row.center == row.through for row in self.circles):
            raise ValueError('A circle needs a nonzero radius')
        if any(len(set(angle)) != 3 for angle in self.right_angles):
            raise ValueError('A right-angle mark needs three distinct points')
        if any(len(group) < 2 or any(a == b for a, b in group) for group in self.equal_segments):
            raise ValueError('An equality class needs at least two nonzero segments')
        if any(len(group) < 2 or any(len(set(angle)) != 3 for angle in group) for group in self.equal_angles):
            raise ValueError('An angle equality class needs at least two nondegenerate angles')
        if any(len(set(angle.points)) != 3 for angle in self.angle_labels):
            raise ValueError('An angle label needs three distinct points')
        return self


def relation_residual(relation: Relation, points: dict[str, np.ndarray]) -> float:
    """Dimensionless residual, normalized by the relevant carrier, not page extent."""
    p = [points[name] for name in relation.points]
    kind = relation.kind
    norm = np.linalg.norm
    if kind in {'perpendicular_planes','plane_angle','dihedral_angle'}:
        if any(len(q)!=3 for q in p):
            raise ValueError('Plane predicates require spatial xyz coordinates')
        if kind=='dihedral_angle':
            a,b,c,d=p
            direction=c-b
            if norm(direction)<1e-8:
                return math.inf
            direction/=norm(direction)
            u,v=a-b-((a-b)@direction)*direction,d-b-((d-b)@direction)*direction
        else:
            a,b,c,d,e,f=p
            u,v=np.cross(b-a,c-a),np.cross(e-d,f-d)
            if min(norm(b-a),norm(c-a),norm(e-d),norm(f-d))<1e-8:
                return math.inf
            if norm(u)<1e-8*norm(b-a)*norm(c-a) or norm(v)<1e-8*norm(e-d)*norm(f-d):
                return math.inf
        if min(norm(u),norm(v))<1e-8:
            return math.inf
        cosine=float(np.clip(u@v/(norm(u)*norm(v)),-1,1))
        if kind=='perpendicular_planes':
            return abs(cosine)
        actual=math.acos(abs(cosine) if kind=='plane_angle' else cosine)
        return abs(actual-math.radians(relation.value))/math.pi
    if kind == 'distinct':
        return 0.0 if norm(p[0] - p[1]) > 1e-8 else math.inf
    if kind == 'noncollinear':
        a, b, c = p
        matrix = np.column_stack((b - a, c - a))
        return 0.0 if min(norm(b - a), norm(c - a)) > 1e-8 and np.linalg.cond(matrix) < 1e8 else math.inf
    if kind == 'inside_triangle':
        point, a, b, c = p
        matrix = np.column_stack((b - a, c - a))
        if np.linalg.cond(matrix) > 1e8:
            return math.inf
        coefficients = np.linalg.lstsq(matrix, point - a, rcond=None)[0]
        if min(*coefficients, 1 - sum(coefficients)) <= 1e-6:
            return math.inf
        return float(norm(matrix @ coefficients - (point - a)) / max(norm(b - a), norm(c - a)))
    if kind in {'noncoplanar', 'on_plane', 'perpendicular_plane', 'parallel_plane'}:
        if len(p[0]) != 3:
            raise ValueError('Plane predicates require spatial xyz coordinates')
        a, b, c = p[-3:]
        u, v = b - a, c - a
        normal = np.cross(u, v)
        if min(norm(u), norm(v)) < 1e-8 or norm(normal) <= 1e-8 * norm(u) * norm(v):
            return math.inf
        normal /= norm(normal)
        distance = abs(float((p[0] - a) @ normal)) / max(norm(u), norm(v))
        if kind == 'on_plane':
            return distance
        if kind == 'noncoplanar':
            return 0.0 if distance > 1e-8 else math.inf
        direction = p[1] - p[0]
        if norm(direction) < 1e-8:
            return math.inf
        cosine = float(direction @ normal / norm(direction))
        if kind == 'parallel_plane':
            return abs(cosine) if distance > 1e-8 else math.inf
        return float(norm(direction / norm(direction) - math.copysign(1, cosine) * normal))
    if kind == 'equal_angle':
        a, v, b, c, w, d = p
        u1, u2, v1, v2 = a - v, b - v, c - w, d - w
        if min(norm(u1), norm(u2), norm(v1), norm(v2)) <= 1e-8:
            return math.inf
        first = math.acos(float(np.clip(u1 @ u2 / (norm(u1) * norm(u2)), -1, 1)))
        second = math.acos(float(np.clip(v1 @ v2 / (norm(v1) * norm(v2)), -1, 1)))
        return abs(first - second) / math.pi
    if kind == 'inside_angle':
        x, vertex, a, b = p
        u, v, w = a - vertex, b - vertex, x - vertex
        if min(norm(u), norm(v), norm(w)) <= 1e-8:
            return math.inf
        matrix = np.column_stack((u / norm(u), v / norm(v)))
        if np.linalg.cond(matrix) > 1e8:
            return math.inf
        coefficients = np.linalg.lstsq(matrix, w / norm(w), rcond=None)[0]
        return float(norm(matrix @ coefficients - w / norm(w))) if min(coefficients) > 1e-6 else math.inf
    if kind in {'same_side', 'opposite_side'}:
        x, y, a, b = p
        if len(a) != 2:
            raise ValueError('Side-of-line checks require planar coordinates')
        v, u, w = b - a, x - a, y - a
        if min(norm(v), norm(u), norm(w)) <= 1e-8:
            return math.inf
        first = float(v[0] * u[1] - v[1] * u[0]) / (norm(v) * norm(u))
        second = float(v[0] * w[1] - v[1] * w[0]) / (norm(v) * norm(w))
        sign = 1 if kind == 'same_side' else -1
        return 0.0 if sign * first * second > 1e-6 else math.inf
    if kind in {'midpoint', 'on_line', 'on_segment', 'on_ray', 'between'}:
        x, a, b = p
        direction = b - a
        length = norm(direction)
        if length <= 1e-8:
            return math.inf
        if kind == 'midpoint':
            return float(norm(x - (a + b) / 2) / length)
        t = float((x - a) @ direction / length**2)
        distance = float(norm(x - a - t * direction) / length)
        if kind == 'on_line':
            return distance
        if kind == 'on_ray':
            return max(distance, -t)
        if kind == 'between' and not 1e-6 < t < 1 - 1e-6:
            return math.inf
        return max(distance, -t, t - 1)
    if kind == 'on_circle':
        if len(p[0]) != 2:
            raise ValueError('A spatial circle requires its plane; radial distance alone defines a sphere')
        x, center, through = p
        radius = norm(through - center)
        return float(abs(norm(x - center) / radius - 1)) if radius > 1e-8 else math.inf
    if kind == 'angle':
        a, vertex, b = p
        u, v = a - vertex, b - vertex
    else:
        a, b, c, d = p
        u, v = b - a, d - c
    nu, nv = norm(u), norm(v)
    if min(nu, nv) <= 1e-8:
        return math.inf
    cosine = float(np.clip(u @ v / (nu * nv), -1, 1))
    if kind == 'perpendicular':
        return abs(cosine)
    if kind == 'parallel':
        return float(norm(u / nu - math.copysign(1, cosine) * v / nv))
    if kind == 'equal_vector':
        return float(norm(u - v) / max(nu, nv))
    if kind in {'equal_length', 'length_ratio'}:
        ratio = relation.value if kind == 'length_ratio' else 1.0
        return float(abs(nu / nv / ratio - 1))
    if kind == 'shorter':
        return 0.0 if nu < nv * (1 - 1e-6) else math.inf
    return abs(math.acos(cosine) - math.radians(relation.value)) / math.pi


def check_relations(requirements: Requirements, points: dict, *, tolerance: float = 0.006) -> list[dict]:
    result = []
    for relation in requirements.relations:
        coordinates = [points.get(name) for name in relation.points]
        if any(p is None or len(p) not in (2, 3) or not np.isfinite(p).all() for p in coordinates):
            result.append({'id': relation.id, 'role': relation.role, 'status': 'unverified', 'reason': 'unresolved point'})
            continue
        if len({len(p) for p in coordinates}) != 1:
            raise ValueError('Cannot mix planar and spatial coordinates in a relation')
        residual = relation_residual(relation, {name: np.asarray(points[name], dtype=float) for name in relation.points})
        result.append({'id': relation.id, 'role': relation.role,
                       'status': 'pass' if residual <= tolerance else 'fail',
                       'residual': residual if math.isfinite(residual) else None})
    return result


def check_scene(requirements: Requirements, scene: dict, *, world_points: dict | None = None,
                projected_points: dict | None = None) -> dict:
    """Check requested facts and painted objects in independently observed PGF."""
    points = scene['points']
    if (world_points is None) != (projected_points is None):
        raise ValueError('Spatial checking requires both world_points and projected_points in cm')
    truth = world_points if world_points is not None else points
    checks = []
    if world_points is not None:
        complete = set(world_points) == set(projected_points) == set(requirements.points) and all(
            world_points[name] is not None and len(world_points[name]) == 3 and np.isfinite(world_points[name]).all()
            and projected_points[name] is not None and len(projected_points[name]) == 2
            and np.isfinite(projected_points[name]).all() and points.get(name) is not None
            and len(points[name]) == 2 and np.isfinite(points[name]).all() for name in requirements.points)
        error = None
        if complete:
            expected = np.array([projected_points[name] for name in requirements.points]) * (72.27 / 2.54)
            offsets = np.array([points[name] for name in requirements.points]) - expected
            error = float(np.linalg.norm(offsets - np.median(offsets, axis=0), axis=1).max())
        checks.append({'id': 'projection_binding', 'status': 'unverified' if not complete else 'pass' if error <= 0.15 else 'fail',
                       'max_error_tex_pt': error})
        if checks[-1]['status'] != 'pass':
            checks.extend({'id': row.id, 'role': row.role, 'status': 'unverified',
                           'reason': 'World witness is not bound to this compiled projection'} for row in requirements.relations)
            return {'status': 'held', 'checks': checks}
    checks.extend(check_relations(requirements, truth))
    checks.append({'id': 'observations', 'status': 'unverified' if scene['unsupported'] or scene['unresolved'] else 'pass',
                   'unsupported': scene['unsupported'], 'unresolved': scene['unresolved']})
    checks.append({'id': 'point_names', 'status': 'pass' if set(points) == set(requirements.points) else 'fail',
                   'missing': sorted(set(requirements.points) - set(points)),
                   'extra': sorted(set(points) - set(requirements.points))})
    strokes = {style: unary_union([stroke['geometry'] for stroke in scene['strokes']
                                  if stroke['dashed'] == style]) for style in (False, True)}
    for segment in requirements.segments:
        coordinates = [points.get(name) for name in segment.points]
        fraction = 0.0
        if all(p is not None for p in coordinates):
            line = LineString(coordinates)
            if line.length:
                fraction = line.intersection(strokes[segment.dashed].buffer(line.length * PATH_TOLERANCE)).length / line.length
        checks.append({'id': 'segment:' + '-'.join(segment.points),
                       'status': 'pass' if fraction >= COVERAGE_MINIMUM else 'fail'})
        if segment.arrow:
            present = False
            if all(p is not None for p in coordinates):
                a, b = map(np.asarray, coordinates)
                length = np.linalg.norm(b - a)
                present = length > 0 and any(
                    arrow['dashed'] == segment.dashed
                    and np.linalg.norm(np.asarray(arrow['tip']) - b) <= max(1.0, arrow['width'])
                    and float((b - a) @ arrow['direction']) / length > 0.999
                    for arrow in scene.get('arrows', []))
            checks.append({'id': 'arrow:' + '-'.join(segment.points), 'status': 'pass' if present else 'fail'})
    for circle in requirements.circles:
        center, through = points.get(circle.center), points.get(circle.through)
        matched = False
        if center is not None and through is not None:
            center, through = np.asarray(center), np.asarray(through)
            radius = float(np.linalg.norm(through - center))
            matched = radius > 1e-8 and any(
                np.linalg.norm(np.asarray(candidate['center']) - center) / radius <= 0.006
                and abs(candidate['radius'] / radius - 1) <= 0.006
                and candidate['dashed'] == circle.dashed for candidate in scene['circles'])
        checks.append({'id': 'circle:' + circle.center + '-' + circle.through, 'status': 'pass' if matched else 'fail'})
    # Required mark presence is measured from paint; semantic truth is checked separately.
    marks = observe_marks(scene, connections(scene))
    checks.append({'id': 'mark_bindings', 'status': 'unverified' if marks['unresolved'] else 'pass',
                   'unresolved': marks['unresolved']})
    checks.extend({'id': 'mark_truth:' + str(index), 'status': 'pass' if valid else 'fail'}
                  for index, valid in enumerate(mark_truth(marks, truth)))
    for a, vertex, b in requirements.right_angles:
        relation = Relation(id=f'right_angle:{a}-{vertex}-{b}', kind='angle', points=[a, vertex, b], value=90)
        checked = check_relations(Requirements(relations=[relation], points=[a, vertex, b]), truth)[0]
        present = any(same_angle((a, vertex, b), angle, truth) for angle in marks['right_angles'])
        checks.append({**checked, 'status': checked['status'] if present else 'fail', 'painted': present})
    for group in requirements.equal_segments:
        a, b = group[0]
        for c, d in group[1:]:
            relation = Relation(id=f'equality:{a}-{b}:{c}-{d}', kind='equal_length', points=[a, b, c, d])
            req = Requirements(points=list(dict.fromkeys(relation.points)), relations=[relation])
            checks.extend(check_relations(req, truth))
        expected = {tuple(sorted(segment)) for segment in group}
        present = expected in marks['equal_segments']
        for a, b in group:
            checks.append({'id': f'equality_mark:{a}-{b}', 'status': 'pass' if present else 'fail'})
    arc_ink = unary_union([curve['geometry'] for curve in scene['curves'] if not curve['dashed']])
    for number, group in enumerate(requirements.equal_angles, 1):
        for angle in group[1:]:
            relation = Relation(id='equal_angle:' + '-'.join(group[0]) + ':' + '-'.join(angle),
                                kind='equal_angle', points=list(group[0] + angle))
            checks.extend(check_relations(Requirements(points=list(dict.fromkeys(relation.points)), relations=[relation]), truth))
        for angle in group:
            present = False
            if all(points.get(name) is not None for name in angle):
                a, vertex, b = (np.asarray(points[name]) for name in angle)
                u, v = a - vertex, b - vertex
                first, last = math.atan2(u[1], u[0]), math.atan2(v[1], v[0])
                span = (last - first) % math.tau
                if span > math.pi:
                    first, span = last, math.tau - span
                fractions = []
                for index in range(number):
                    radius = 7 + 2 * index
                    theta = np.linspace(first, first + span, 65)
                    arc = LineString(vertex + radius * np.column_stack((np.cos(theta), np.sin(theta))))
                    fractions.append(arc.intersection(arc_ink.buffer(0.25)).length / arc.length if arc.length else 0)
                present = all(fraction >= COVERAGE_MINIMUM for fraction in fractions)
            checks.append({'id': 'equal_angle_mark:' + '-'.join(angle), 'status': 'pass' if present else 'fail'})
    for angle in requirements.angle_labels:
        relation = Relation(id='angle_label:' + '-'.join(angle.points), kind='angle', points=list(angle.points), value=angle.value)
        checked = check_relations(Requirements(points=list(angle.points), relations=[relation]), truth)[0]
        present = False
        if all(points.get(name) is not None for name in angle.points):
            a, vertex, b = (np.asarray(points[name]) for name in angle.points)
            u, v = a - vertex, b - vertex
            first, last = math.atan2(u[1], u[0]), math.atan2(v[1], v[0])
            span = (last - first) % (2 * math.pi)
            if span > math.pi:
                first, span = last, 2 * math.pi - span
            for label in scene['text']:
                if len(label.get('bbox', [])) != 4:
                    continue
                numeric = re.fullmatch(r'([0-9]+(?:[.,][0-9]+)?)\s*[\u00b0\u25e6\u2218]', label['text'].strip())
                if not numeric or abs(float(numeric[1].replace(',', '.')) - angle.value) > 1e-8:
                    continue
                center = np.array([(label['bbox'][0] + label['bbox'][2]) / 2,
                                   (label['bbox'][1] + label['bbox'][3]) / 2]) - vertex
                if 0 < np.linalg.norm(center) < 4 * label['size'] and (math.atan2(center[1], center[0]) - first) % (2 * math.pi) <= span:
                    present = True
        checks.append({**checked, 'status': checked['status'] if present else 'fail', 'painted': present})
    readable = inspect_readability(scene)
    checks.extend({'id': 'label:' + str(index), **label} for index, label in enumerate(readable['labels']))
    font = max((label['size'] for label in scene['text']), default=10.0)
    crowded = [{'points': [a, b], 'distance_em': float(np.linalg.norm(np.asarray(p) - q)) / font}
               for (a, p), (b, q) in combinations(points.items(), 2)
               if p is not None and q is not None and np.linalg.norm(np.asarray(p) - q) < 1.5 * font]
    checks.append({'id': 'point_spacing', 'status': 'fail' if crowded else 'pass', 'crowded': crowded})
    return {'status': 'pass' if all(row['status'] == 'pass' for row in checks) else 'held', 'checks': checks}
