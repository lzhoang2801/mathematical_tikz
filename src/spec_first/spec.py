"""Compile a bounded mathematical specification into exact construction operations.

The model supplies no coordinates, camera, dash flags or TikZ. Relation lowering,
finite configuration search, branch checks and stroke semantics run before TeX.
Passing this module certifies the supplied spec, not its completeness against prose.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations, pairwise
import math
import random
from time import perf_counter
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, FiniteFloat

from spec_first.construction import Construction, StrictModel, realize
from spec_first.instruction_constraints import UNIT_CM, scan_instruction
from spec_first.metric_expression import metric_measure
from spec_first.planar_solver import forward_points, solve_parameters
from spec_first.relation_presentation import (
    bind_sectors, equality_groups, metric_and_parallel_strokes,
    sector_strokes, selected_relations,
)
from spec_first.spatial_construction import SpatialConstruction, realize_spatial, validate_solid
from spec_first.spatial_construction import _right_angle_options

SpecName = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9]*(?:_[0-9]+)?'{0,2}$", max_length=24)]


class SpecPoint(StrictModel):
    name: SpecName
    visible: bool = True


class Relation(StrictModel):
    kind: Literal['midpoint', 'interpolation', 'projection', 'reflection', 'intersection',
                  'on_line', 'on_segment', 'on_ray', 'same_side', 'inside_angle',
                  'equal_length', 'equal_angle', 'perpendicular', 'parallel', 'distinct',
                  'noncollinear', 'centroid', 'parallelogram', 'partition', 'parallel_section',
                  'length', 'length_ratio', 'shorter', 'angle', 'on_plane',
                  'perpendicular_planes', 'plane_angle', 'dihedral_angle']
    points: list[SpecName] = Field(min_length=2, max_length=17)
    values: list[FiniteFloat] = Field(default_factory=list, max_length=8)
    unit: Literal['', 'mm', 'cm', 'm'] = ''
    expression: str = Field(default='', max_length=160, description='For length only: exact symbolic expression such as a/(2√3); use values=[] instead of a numeric approximation. One positive shared parameter, constant arithmetic and square roots are supported.')
    source_quote: str = Field(min_length=1, max_length=1500, description='Exact supporting excerpt from the instruction; audit provenance, not proof of semantic equivalence.')
    mark: bool | None = Field(default=None, description='Explicit source request/suppression only: true requires a visible cue, false suppresses it, null lets the deterministic presentation policy select cues. Never use this field to choose layout.')


class DrawObject(StrictModel):
    kind: Literal['segment', 'polyline', 'polygon', 'line', 'ray', 'circle', 'angle', 'plane_angle', 'dihedral_angle']
    points: list[SpecName] = Field(min_length=2, max_length=12)
    label: str = Field(default='', pattern=r"^[A-Za-z]?$", description='Optional line/ray label or unknown angle letter. An angle uses [A,V,B] for the non-reflex sector AVB; no numeric answer is inferred.')


class Solid(StrictModel):
    kind: Literal['tetrahedron', 'pyramid', 'parallelepiped']
    vertices: list[SpecName] = Field(min_length=4, max_length=8, description='Tetrahedron: apex then 3 base vertices. Pyramid: apex then cyclic base. Parallelepiped: cyclic base then corresponding top vertices.')
    source_quote: str = Field(min_length=1, max_length=1500)


class LengthLabel(StrictModel):
    points: list[SpecName] = Field(min_length=2, max_length=2)
    value: FiniteFloat | None = Field(default=None, gt=0)
    expression: str = Field(default='', max_length=160)
    unit: Literal['', 'mm', 'cm', 'm'] = ''
    source_quote: str = Field(min_length=1, max_length=1500)


class GeometrySpec(StrictModel):
    dimension: Literal[2, 3]
    points: list[SpecPoint] = Field(min_length=2, max_length=24)
    relations: list[Relation] = Field(min_length=1, max_length=40)
    draw: list[DrawObject] = Field(default_factory=list, max_length=32, description='Requested drawing scope. Solid boundary edges are automatic. Helpers stay invisible.')
    solid: Solid | None = None
    length_labels: list[LengthLabel] = Field(default_factory=list, max_length=24)
    unsupported: list[str] = Field(default_factory=list, max_length=40, description='Verbatim instruction excerpts not expressible by this schema. Nonempty prevents drawing; never replace spatial objects with planar surrogates.')


class SpecError(ValueError):
    def __init__(self, category: str, message: str):
        self.category = category
        super().__init__(f'{category}: {message}')


def instruction_preflight(instruction):
    audit = scan_instruction(instruction)
    if audit['issues']:
        raise SpecError('unsupported_instruction', str(audit['issues']))
    return audit


def _same_measure(left, right):
    a,b = metric_measure(left),metric_measure(right)
    return a.parameter == b.parameter and math.isclose(a.coefficient*UNIT_CM[left.unit], b.coefficient*UNIT_CM[right.unit], rel_tol=1e-10)


def admit_instruction(spec, instruction):
    """Merge independently parsed obligations into a copy, never edit extraction."""
    audit = instruction_preflight(instruction)
    if audit['spatial_requested'] and spec.dimension != 3:
        raise SpecError('dimension_mismatch', 'Instruction requests spatial geometry; planar replacement is unsupported')
    admitted = spec.model_copy(deep=True)
    names = {p.name for p in spec.points}
    lengths = []
    audit['added_relations'], audit['added_labels'] = [], []
    for fact in audit['obligations']:
        kind, points = fact['kind'], fact.get('points')
        if kind in {'radius', 'radius_segment'}:
            circles = [d for d in spec.draw if d.kind == 'circle' and d.points[0] == fact['center']]
            if len(circles) != 1:
                raise SpecError('unbound_source_requirement', f'Radius cannot bind to exactly one declared circle: {fact["quote"]}')
            kind, points = ('length', circles[0].points) if kind == 'radius' else ('length_ratio', circles[0].points+points)
        if any(n not in names for n in points):
            raise SpecError('unbound_source_requirement', fact['quote'])
        values = [fact['value']] if 'value' in fact else []
        relation = Relation(kind=kind, points=points, values=values, expression=fact.get('expression',''), unit=fact.get('unit', ''), source_quote=fact['quote'])
        if kind == 'length':
            lengths.append(relation)
            for existing in admitted.relations:
                if (existing.kind == 'length' and set(existing.points) == set(points)
                        and not _same_measure(existing,relation)):
                    raise SpecError('source_conflict', f'Model length disagrees with instruction: {fact["quote"]}')
        def same_fact(r, relation=relation):
            kind,points,values = relation.kind,relation.points,relation.values
            if r.kind != kind:
                return False
            if kind == 'length':
                return set(r.points) == set(points) and _same_measure(r,relation)
            if kind == 'angle':
                return (r.points == points or r.points == list(reversed(points))) and r.values == values
            if kind in {'perpendicular_planes','plane_angle'}:
                return {frozenset(r.points[:3]),frozenset(r.points[3:])} == {frozenset(points[:3]),frozenset(points[3:])} and r.values == values
            if kind == 'dihedral_angle':
                return set(r.points[1:3]) == set(points[1:3]) and {r.points[0],r.points[3]} == {points[0],points[3]} and r.values == values
            if kind == 'length_ratio':
                first,second = set(points[:2]),set(points[2:])
                if set(r.points[:2]) == first and set(r.points[2:]) == second:
                    return r.values == values
                if set(r.points[:2]) == second and set(r.points[2:]) == first:
                    return len(r.values)==len(values)==1 and math.isclose(r.values[0]*values[0],1,rel_tol=1e-10)
            return r.points == points and r.values == values and r.expression == relation.expression and r.unit == relation.unit
        same = any(same_fact(r) for r in admitted.relations)
        if not same:
            admitted.relations.append(relation)
            audit['added_relations'].append(relation.model_dump(mode='json'))
    for request in audit['annotations']:
        requested = [LengthLabel(points=['A','B'],source_quote=request['quote'],**q) for q in request['quantities']]
        matches = [r for r in lengths if not requested or any(_same_measure(r,q) for q in requested)]
        if not matches or any(not any(_same_measure(r,q) for r in matches) for q in requested):
            raise SpecError('unbound_source_requirement', f'Numeric label request cannot bind to given lengths: {request["quote"]}')
        for relation in matches:
            quantities = [q for q in requested if _same_measure(relation,q)]
            if len({(q.value,q.expression,q.unit) for q in quantities}) > 1:
                raise SpecError('unsupported_annotation', 'Multiple display units for the same length are ambiguous')
            label = (quantities[0].model_copy(update={'points':relation.points}) if quantities else
                     LengthLabel(points=relation.points, value=relation.values[0] if relation.values else None, expression=relation.expression, unit=relation.unit, source_quote=request['quote']))
            if any(set(l.points) == set(label.points) and (l.value != label.value or l.expression != label.expression or l.unit != label.unit) for l in admitted.length_labels):
                raise SpecError('source_conflict', f'Metric annotation disagrees with requested display: {request["quote"]}')
            if not any(set(l.points) == set(label.points) for l in admitted.length_labels):
                admitted.length_labels.append(label)
                audit['added_labels'].append(label.model_dump(mode='json'))
    return GeometrySpec.model_validate(admitted.model_dump()), audit


def _length(v):
    return float(np.linalg.norm(v))


def _line_parameter(p, a, b):
    v = b - a
    if _length(v) < 1e-8:
        raise ValueError('Degenerate line')
    t = float((p-a) @ v / (v @ v))
    return t, _length(p-a-t*v)


def _cross(u, v):
    return float(u[0]*v[1]-u[1]*v[0])


def _angle(a, v, b):
    u, w = a-v, b-v
    denominator = _length(u)*_length(w)
    if denominator < 1e-10:
        raise ValueError('Degenerate angle')
    return math.acos(float(np.clip((u @ w)/denominator, -1, 1)))


def _validate(spec: GeometrySpec, instruction: str):
    names = [p.name for p in spec.points]
    if len(set(names)) != len(names) or any(n.startswith('Sf') for n in names):
        raise SpecError('invalid_spec', 'Duplicate or reserved point name')
    if (spec.dimension == 3) != (spec.solid is not None):
        raise SpecError('unsupported', '3D requires one supported closed solid; 2D has no solid')
    arity = {'midpoint': 3, 'interpolation': 3, 'projection': 4, 'reflection': 4,
             'intersection': 5, 'on_line': 3, 'on_segment': 3, 'on_ray': 3,
             'same_side': 4, 'inside_angle': 4, 'equal_angle': 6, 'perpendicular': 4,
             'parallel': 4, 'distinct': 2, 'noncollinear': 3, 'centroid': 4, 'parallelogram': 4}
    arity.update(length=2, length_ratio=4, shorter=4, angle=3, on_plane=4,
                 perpendicular_planes=6, plane_angle=6, dihedral_angle=4)
    if spec.unsupported:
        raise SpecError('unsupported_instruction', str(spec.unsupported))
    mark_kinds = {'equal_length', 'midpoint', 'partition', 'perpendicular', 'projection', 'equal_angle', 'angle', 'length', 'parallel', 'length_ratio', 'perpendicular_planes', 'plane_angle', 'dihedral_angle'}
    for r in spec.relations:
        if r.mark is True and (r.kind not in mark_kinds or (r.kind == 'partition' and r.values and max(r.values) != min(r.values)) or (r.kind == 'length_ratio' and r.values != [1])):
            raise SpecError('unsupported', f'Visible annotation for {r.kind} is not supported')
        if any(n not in names for n in r.points):
            raise SpecError('invalid_spec', f'Unknown point in {r.kind}')
        if r.source_quote not in instruction:
            raise SpecError('invalid_spec', f'Nonverbatim source_quote in {r.kind}')
        if r.kind in arity and len(r.points) != arity[r.kind]:
            raise SpecError('invalid_spec', f'{r.kind} requires {arity[r.kind]} points')
        if r.kind == 'equal_length' and (len(r.points) < 4 or len(r.points) % 2):
            raise SpecError('invalid_spec', 'equal_length takes consecutive endpoint pairs')
        if r.kind == 'parallel_section' and (len(r.points) < 7 or len(r.points) % 2 != 1):
            raise SpecError('invalid_spec', 'parallel_section takes apex, n base points, n section points')
        if r.kind == 'partition' and len(r.points) < 3:
            raise SpecError('invalid_spec', 'partition takes ordered endpoints and division points')
        if r.kind == 'interpolation':
            if len(r.values) != 1 or not 0 <= r.values[0] <= 1:
                raise SpecError('invalid_spec', 'interpolation needs one fraction in [0,1]')
        elif r.kind == 'partition':
            if r.values and (len(r.values) != len(r.points)-1 or min(r.values) <= 0):
                raise SpecError('invalid_spec', 'partition needs positive interval ratios, or [] for equal parts')
        elif r.kind == 'length' and r.expression:
            if r.values or (r.unit and metric_measure(r).parameter):
                raise SpecError('invalid_spec', 'Expression lengths cannot also supply numeric values; a length parameter cannot carry another unit')
            metric_measure(r)
        elif r.kind in {'length', 'length_ratio'}:
            if len(r.values) != 1 or r.values[0] <= 0 or not math.isfinite(r.values[0]*UNIT_CM[r.unit]):
                raise SpecError('invalid_spec', f'{r.kind} requires one positive value')
        elif r.kind in {'angle', 'plane_angle', 'dihedral_angle'}:
            if len(r.values) != 1 or not 0 < r.values[0] < 180 or (r.kind == 'plane_angle' and r.values[0] > 90):
                raise SpecError('invalid_spec', 'angle requires one degree value strictly between 0 and 180')
        elif r.values:
            raise SpecError('invalid_spec', f'{r.kind} has no numeric parameters')
        if r.unit and r.kind != 'length':
            raise SpecError('invalid_spec', 'Only length has a unit')
        if r.expression and r.kind != 'length':
            raise SpecError('invalid_spec', 'Only length has an expression')
        if spec.dimension == 3 and r.kind in {'reflection', 'inside_angle', 'same_side'}:
            raise SpecError('unsupported', f'{r.kind} is currently planar')
        if spec.dimension != 3 and r.kind in {'on_plane', 'perpendicular_planes', 'plane_angle', 'dihedral_angle'}:
            raise SpecError('invalid_spec', f'{r.kind} requires 3D')
        if r.kind in {'perpendicular_planes', 'plane_angle'} and any(len(set(p)) != 3 for p in (r.points[:3],r.points[3:])):
            raise SpecError('invalid_spec', 'Each plane needs three distinct points')
        if r.kind in {'on_plane', 'dihedral_angle'} and len(set(r.points)) != 4:
            raise SpecError('invalid_spec', f'{r.kind} needs four distinct points')
    for d in spec.draw:
        if any(n not in names for n in d.points) or (d.kind != 'plane_angle' and len(set(d.points)) != len(d.points)):
            raise SpecError('invalid_spec', 'Unknown or duplicate drawing endpoint')
        if d.kind in {'segment', 'line', 'ray', 'circle'} and len(d.points) != 2:
            raise SpecError('invalid_spec', f'{d.kind} needs two points')
        if d.kind == 'polygon' and len(d.points) < 3:
            raise SpecError('invalid_spec', 'polygon needs at least three points')
        if d.kind == 'angle' and len(d.points) != 3:
            raise SpecError('invalid_spec', 'angle needs exactly three points')
        if d.kind in {'plane_angle', 'dihedral_angle'}:
            if spec.dimension != 3 or len(d.points) != (6 if d.kind == 'plane_angle' else 4):
                raise SpecError('invalid_spec', 'Plane/dihedral drawing requires 3D and two triples/four hinge-side points')
            if d.kind == 'plane_angle' and any(len(set(p)) != 3 for p in (d.points[:3],d.points[3:])):
                raise SpecError('invalid_spec', 'Each plane needs three distinct points')
        if d.label and d.kind not in {'line', 'ray', 'angle', 'plane_angle', 'dihedral_angle'}:
            raise SpecError('invalid_spec', 'Only lines, rays and angles have object labels')
        if spec.dimension == 3 and d.kind in {'line', 'ray', 'circle'}:
            raise SpecError('unsupported', 'Spatial scope currently supports contained straight segments')
    if spec.solid:
        s = spec.solid
        if s.source_quote not in instruction or any(n not in names for n in s.vertices) or len(set(s.vertices)) != len(s.vertices):
            raise SpecError('invalid_spec', 'Invalid solid source or vertices')
        if (s.kind == 'tetrahedron' and len(s.vertices) != 4) or (s.kind == 'parallelepiped' and len(s.vertices) != 8):
            raise SpecError('invalid_spec', 'Wrong solid vertex count')
    if not any(p.visible for p in spec.points):
        raise SpecError('invalid_spec', 'No visible points')
    lengths = [r for r in spec.relations if r.kind == 'length']
    parameters = {metric_measure(r).parameter for r in lengths}
    if len(parameters) > 1:
        raise SpecError('unsupported', 'Lengths require one shared positive parameter or one numeric unit system; independent parameters cannot be assigned arbitrary values')
    if any(r.unit for r in lengths) and any(not r.unit for r in lengths):
        raise SpecError('unsupported', 'Mixed implicit and explicit length units are ambiguous')
    for label in spec.length_labels:
        if bool(label.expression) == (label.value is not None) or (label.expression and label.unit and metric_measure(label).parameter):
            raise SpecError('invalid_spec', 'Length labels require exactly one numeric value or expression')
        if label.source_quote not in instruction or any(n not in names for n in label.points):
            raise SpecError('invalid_spec', 'Invalid metric label source or endpoints')
        if not any(set(r.points) == set(label.points) and _same_measure(r,label) for r in lengths):
            raise SpecError('invalid_spec', 'Metric label must match a bound length constraint')


def _lower(spec):
    """Compile relation patterns to an acyclic graph, never dispatch by case ID."""
    ops, faces, loci = {}, [], []
    helper_index = 0

    def helper(op, refs, values=()):
        nonlocal helper_index
        helper_index += 1
        name = f'Sf{helper_index}'
        ops[name] = (op, list(refs), list(values))
        return name

    def define(name, op, refs, values=()):
        # Redundant defining relations are checked numerically after realization.
        if name not in ops:
            ops[name] = (op, list(refs), list(values))

    if spec.solid:
        kind, v = spec.solid.kind, spec.solid.vertices
        if kind in {'tetrahedron', 'pyramid'}:
            apex, base = v[0], v[1:]
            faces = [base] + [[apex, a, b] for a, b in zip(base, base[1:]+base[:1])]
        else:
            a, b, c, d, ap, bp, cp, dp = v
            define(c, 'translate', [b, a, d])
            for lower, upper in ((b, bp), (c, cp), (d, dp)):
                define(upper, 'translate', [lower, a, ap])
            faces = [[a,b,c,d], [ap,bp,cp,dp], [a,b,bp,ap], [b,c,cp,bp], [c,d,dp,cp], [d,a,ap,dp]]
    priority = {'parallelogram': 0, 'parallel_section': 1, 'partition': 2, 'intersection': 3, 'midpoint': 4}
    relations = sorted(spec.relations, key=lambda r: priority.get(r.kind, 5))
    for r in relations:
        p, k = r.points, r.kind
        if k in {'midpoint', 'interpolation'}:
            define(p[0], 'lerp', p[1:], [0.5 if k == 'midpoint' else r.values[0]])
        elif k in {'projection', 'reflection', 'intersection'}:
            define(p[0], {'projection':'project', 'reflection':'reflect', 'intersection':'intersect'}[k], p[1:])
        elif k == 'parallelogram':
            if spec.dimension != 3:
                raise SpecError('unsupported', 'Planar parallelogram lowering is outside this pilot')
            define(p[2], 'translate', [p[1], p[0], p[3]])
        elif k == 'centroid':
            mid = helper('lerp', p[1:3], [0.5])
            define(p[0], 'lerp', [p[3], mid], [2/3])
        elif k == 'partition':
            weights = r.values or [1]*(len(p)-1)
            for i, name in enumerate(p[1:-1], 1):
                define(name, 'lerp', [p[0],p[-1]], [sum(weights[:i])/sum(weights)])
        elif k == 'parallel_section':
            if spec.dimension != 3:
                raise SpecError('unsupported', 'parallel_section requires 3D')
            n = (len(p)-1)//2
            apex, base, section = p[0], p[1:1+n], p[1+n:]
            for end, cut in zip(base[1:], section[1:]):
                parallel = helper('translate', [section[0], base[0], end])
                define(cut, 'intersect', [apex, end, section[0], parallel])
    for r in relations:
        if r.kind in {'on_line', 'on_segment', 'on_ray'} and r.points[0] not in ops:
            define(r.points[0], 'parameter', r.points[1:], [0])
            loci.append((r.points[0], r.kind))
    if spec.dimension == 2:
        projections = {r.points[0]: r.points[1:] for r in relations if r.kind == 'projection'}
        for r in relations:
            if r.kind != 'equal_length' or len(r.points) != 4:
                continue
            a, b, c, d = r.points
            shared = {a,b} & {c,d}
            if len(shared) != 1:
                continue
            center = next(iter(shared))
            left = b if a == center else a
            right = d if c == center else c
            if center in ops:
                continue
            lp, rp = projections.get(left), projections.get(right)
            common = set(lp[1:]) & set(rp[1:]) if lp and rp else set()
            if lp and rp and lp[0] == rp[0] == center and len(common) == 1:
                origin = next(iter(common))
                x, y = next(n for n in lp[1:] if n != origin), next(n for n in rp[1:] if n != origin)
                if y in ops:
                    raise SpecError('unsupported', 'Bisector direction endpoint already constrained')
                define(y, 'angle_parameter', [origin,x], [0])
                loci.append((y, 'angle'))
                mid = helper('lerp', [x,y], [0.5])
                define(center, 'parameter', [origin,mid], [0])
                loci.append((center, 'bisector'))
            elif left not in projections and right not in projections:
                mid = helper('lerp', [left,right], [0.5])
                normal = helper('rotate', [mid,right], [90])
                define(center, 'parameter', [mid,normal], [0])
                loci.append((center, 'perpendicular_bisector'))
    roots = [p.name for p in spec.points if p.name not in ops]
    ordered, known = [], set(roots)
    remaining = dict(ops)
    while remaining:
        ready = [name for name, (_,refs,_) in remaining.items() if set(refs) <= known]
        if not ready:
            raise SpecError('unsupported', 'Cyclic or unresolved defining relations: '+', '.join(remaining))
        for name in ready:
            op, refs, values = remaining.pop(name)
            ordered.append((name,op,refs,values))
            known.add(name)
    return roots, ordered, faces, dict(loci)


def _root_values(spec, roots, rng):
    dim = spec.dimension
    values = {name: [rng.uniform(-1,5), rng.uniform(1,4)] + ([rng.uniform(1,4)] if dim == 3 else []) for name in roots}
    if dim == 2:
        anchors = next((d.points for d in spec.draw if d.kind in {'line','ray'} and all(n in roots for n in d.points)), roots[:2])
        if len(anchors) == 2:
            values[anchors[0]], values[anchors[1]] = [0,0], [rng.uniform(4,6),0]
    else:
        s, v = spec.solid, spec.solid.vertices
        if s.kind == 'parallelepiped':
            a,b,_,d,ap,*_ = v
            frame = {a:[0,0,0], b:[rng.uniform(4,6),0,0], d:[rng.uniform(-1,2),rng.uniform(3,5),0], ap:[rng.uniform(-1,2),rng.uniform(-1,2),rng.uniform(3,5)]}
        else:
            apex, base = v[0], v[1:]
            frame = {apex:[rng.uniform(0,3),rng.uniform(0,2),rng.uniform(3,5)], base[0]:[0,0,0], base[1]:[rng.uniform(4,6),0,0]}
            for i,name in enumerate(base[2:], 2):
                theta = math.pi*(i-1)/(len(base)-1)
                frame[name] = [2+3*math.cos(theta),rng.uniform(3,5)*math.sin(theta),0]
            if len(base) == 4:
                frame[base[-1]] = [rng.uniform(-1,2),rng.uniform(3,5),0]
        values.update({n:p for n,p in frame.items() if n in roots})
    return values


def _steps(spec, roots, ordered, loci, rng, identifiers):
    values = _root_values(spec, roots, rng)
    steps = [{'name':identifiers[n], 'op':'free', 'values':p} for n,p in values.items()]
    for name, op, refs, parameters in ordered:
        parameters = list(parameters)
        if op == 'parameter':
            kind = loci[name]
            bounds = {'on_line':(-0.3,1.3), 'on_segment':(.15,.85), 'on_ray':(.2,1.4),
                      'bisector':(.35,.8), 'perpendicular_bisector':(1.0,2.2)}[kind]
            op, parameters = 'lerp', [rng.uniform(*bounds)]
        elif op == 'angle_parameter':
            op, parameters = 'rotate', [rng.uniform(45,100)]
        steps.append({'name':identifiers[name], 'op':op, 'refs':[identifiers[n] for n in refs], 'values':parameters})
    return steps


def check_constraints(spec, points, tolerance=1e-7):
    """Independent residuals on the realized world points, including branches."""
    p = {n:np.asarray(v,dtype=float) for n,v in points.items()}
    span = max((_length(a-b) for a,b in combinations(p.values(),2)), default=1)
    scale = max(span,1)
    checks = []
    metrics = [r for r in spec.relations if r.kind == 'length']
    reference = metrics[0] if metrics else None
    metric_scale = (_length(p[reference.points[0]]-p[reference.points[1]]) / (metric_measure(reference).coefficient*UNIT_CM[reference.unit])) if reference else 1
    for index,r in enumerate(spec.relations):
        v, k = [p[n] for n in r.points], r.kind
        residual, branch = 0.0, True
        if k in {'midpoint','interpolation'}:
            t = .5 if k == 'midpoint' else r.values[0]
            residual = _length(v[0]-(v[1]+t*(v[2]-v[1])))/scale
        elif k in {'on_line','on_segment','on_ray'}:
            t,error = _line_parameter(*v)
            residual = error/scale
            branch = k == 'on_line' or (-tolerance <= t <= 1+tolerance if k == 'on_segment' else t >= -tolerance)
        elif k == 'projection':
            foot,source,a,b = v
            _,error = _line_parameter(foot,a,b)
            residual = max(error/scale, abs(float((source-foot)@(b-a)))/max(_length(source-foot)*_length(b-a),1e-15))
            branch = _length(source-foot) > 1e-5*scale
        elif k == 'reflection':
            image,source,a,b = v
            _,error = _line_parameter((image+source)/2,a,b)
            residual = max(error/scale, abs(float((image-source)@(b-a)))/max(_length(image-source)*_length(b-a),1e-15))
            branch = _length(image-source) > 1e-5*scale
        elif k == 'intersection':
            residual = max(_line_parameter(v[0],v[1],v[2])[1], _line_parameter(v[0],v[3],v[4])[1])/scale
        elif k == 'centroid':
            residual = _length(v[0]-sum(v[1:])/3)/scale
        elif k == 'parallelogram':
            residual = _length(v[0]+v[2]-v[1]-v[3])/scale
        elif k == 'equal_length':
            lengths = [_length(a-b) for a,b in zip(v[::2],v[1::2])]
            residual = (max(lengths)-min(lengths))/scale
            branch = min(lengths) > 1e-5*scale
        elif k == 'equal_angle':
            residual = abs(_angle(*v[:3])-_angle(*v[3:]))
        elif k == 'angle':
            residual = abs(_angle(*v)-math.radians(r.values[0]))
        elif k in {'on_plane', 'perpendicular_planes', 'plane_angle'}:
            triples = [v[1:]] if k == 'on_plane' else [v[:3],v[3:]]
            normals = [np.cross(b-a,c-a) for a,b,c in triples]
            branch = all(_length(n) > 1e-8*scale**2 for n in normals)
            if branch:
                normals = [n/_length(n) for n in normals]
                if k == 'on_plane':
                    residual = abs(float((v[0]-v[1])@normals[0]))/scale
                elif k == 'perpendicular_planes':
                    residual = abs(float(normals[0]@normals[1]))
                else:
                    actual = math.acos(float(np.clip(abs(normals[0]@normals[1]),0,1)))
                    residual = abs(actual-math.radians(r.values[0]))
        elif k == 'dihedral_angle':
            a,b,c,d = v
            hinge = c-b
            branch = _length(hinge) > 1e-5*scale
            if branch:
                hinge /= _length(hinge)
                u,w = a-b-hinge*float((a-b)@hinge),d-b-hinge*float((d-b)@hinge)
                branch = min(_length(u),_length(w)) > 1e-5*scale
                if branch:
                    residual = abs(_angle(u,np.zeros(3),w)-math.radians(r.values[0]))
        elif k in {'length', 'length_ratio', 'shorter'}:
            first = _length(v[0]-v[1])
            if k == 'length':
                expected = metric_scale*metric_measure(r).coefficient*UNIT_CM[r.unit]
                branch = metric_scale > 1e-10 and first > 1e-5*scale
                residual = abs(first-expected)/max(expected,1e-15)
            else:
                second = _length(v[2]-v[3])
                branch = min(first,second) > 1e-5*scale
                if k == 'shorter':
                    branch = branch and second-first > tolerance*scale
                else:
                    residual = abs(first/ max(second,1e-15)-r.values[0])/max(1,r.values[0])
        elif k in {'perpendicular','parallel'}:
            u,w = v[1]-v[0],v[3]-v[2]
            denominator = _length(u)*_length(w)
            branch = denominator > 1e-10*scale**2
            cosine = float(u@w)/max(denominator,1e-30)
            residual = abs(cosine) if k == 'perpendicular' else abs(1-cosine*cosine)
        elif k == 'same_side':
            a,b,c,d = v
            first,second = _cross(d-c,a-c),_cross(d-c,b-c)
            branch = first*second > 1e-9*scale**4
        elif k == 'inside_angle':
            m,o,x,y = v
            matrix = np.column_stack((x-o,y-o))
            branch = np.linalg.cond(matrix) < 1e5 and _angle(x,o,y) < math.pi-1e-4
            if branch:
                weights = np.linalg.solve(matrix,m-o)
                branch = bool(min(weights) > 1e-5)
        elif k == 'distinct':
            branch = _length(v[0]-v[1]) > 1e-4*scale
        elif k == 'noncollinear':
            branch = np.linalg.matrix_rank(np.column_stack((v[1]-v[0],v[2]-v[0])),tol=1e-5*scale) == 2
        elif k == 'partition':
            weights = r.values or [1]*(len(v)-1)
            residual = max(_length(q-(v[0]+sum(weights[:i])/sum(weights)*(v[-1]-v[0])))/scale for i,q in enumerate(v[1:-1],1))
        elif k == 'parallel_section':
            n = (len(v)-1)//2
            apex,base,section = v[0],v[1:1+n],v[1+n:]
            ts = [_line_parameter(q,apex,end) for end,q in zip(base,section)]
            residual = max(max(e/scale for _,e in ts),max(t for t,_ in ts)-min(t for t,_ in ts))
            base_vectors = np.asarray(base[1:])-base[0]
            section_vectors = np.asarray(section[1:])-section[0]
            _,base_singular,base_basis = np.linalg.svd(base_vectors)
            _,section_singular,section_basis = np.linalg.svd(section_vectors)
            base_rank = sum(base_singular > tolerance*scale)
            section_rank = sum(section_singular > tolerance*scale)
            normal,section_normal = base_basis[-1],section_basis[-1]
            plane_error = max(abs(float(v@normal))/scale for v in base_vectors)
            section_error = max(abs(float(v@section_normal))/scale for v in section_vectors)
            residual = max(residual,plane_error,section_error,abs(1-float(normal@section_normal)**2))
            branch = (base_rank == section_rank == 2 and abs(float((apex-base[0])@normal)) > tolerance*scale
                      and all(tolerance < t < 1-tolerance for t,_ in ts))
        else:
            raise ValueError(f'Unsupported constraint checker kind: {k}')
        passed = bool(branch and math.isfinite(residual) and residual <= tolerance)
        checks.append({'index':index,'kind':k,'points':r.points,'residual':float(residual),'branch_pass':bool(branch),'pass':passed})
    # Projection onto a declared ray includes the positive-ray branch.
    rays = [d.points for d in spec.draw if d.kind == 'ray']
    for r in spec.relations:
        if r.kind == 'projection':
            for a,b in rays:
                if set(r.points[2:]) == {a,b}:
                    t,error = _line_parameter(p[r.points[0]],p[a],p[b])
                    checks.append({'kind':'projection_on_positive_ray','points':r.points,'pass':bool(t > 1e-5 and error <= tolerance*scale)})
    visible = [p[q.name] for q in spec.points if q.visible]
    checks.append({'kind':'distinct_visible_points','pass':all(_length(a-b)>1e-4*scale for a,b in combinations(visible,2))})
    return checks


def _drawing(spec, identifiers):
    segments, circles, unbounded = set(), [], []
    for d in spec.draw:
        p = [identifiers[n] for n in d.points]
        if d.kind in {'angle', 'plane_angle', 'dihedral_angle'}:
            continue
        if d.kind == 'circle':
            circles.append({'center':p[0],'through':p[1]})
        elif d.kind in {'ray','line'}:
            unbounded.append((d,p))
            segments.add(tuple(sorted(p)))
        else:
            pairs = list(pairwise(p)) + ([(p[-1],p[0])] if d.kind == 'polygon' else [])
            segments.update(tuple(sorted(pair)) for pair in pairs)
    return segments,circles,unbounded


def _equal_groups(spec, identifiers, drawn=None):
    # Retained for saved study consumers; production also verifies world lengths.
    selection = selected_relations(spec,identifiers)
    return [set(group) for group in selection['equal_classes']
            if drawn is None or all(drawn(a,b) for a,b in group)]


def _clearance(points, names, segments, circles):
    span = max((_length(points[a]-points[b]) for a,b in combinations(names,2)), default=1)
    if span < 1e-6:
        raise ValueError('Collapsed drawing')
    distances = [_length(points[a]-points[b])/span for a,b in combinations(names,2)]
    for name in names:
        for a,b in segments:
            t,error = _line_parameter(points[name],points[a],points[b])
            if error < 1e-7 and -1e-7 <= t <= 1+1e-7:
                continue
            nearest = points[a]+min(1,max(0,t))*(points[b]-points[a])
            distances.append(_length(points[name]-nearest)/span)
        for circle in circles:
            center,through = points[circle['center']],points[circle['through']]
            distance = abs(_length(points[name]-center)-_length(through-center))
            if distance > 1e-7:
                distances.append(distance/span)
    return min(distances, default=0)


def _planar(spec, steps, identifiers):
    segments,circles,unbounded = _drawing(spec,identifiers)
    names = [identifiers[p.name] for p in spec.points if p.visible]
    base_labels = [{'point':identifiers[p.name],'text':p.name,'position':'above'} for p in spec.points if p.visible]
    base = {'points':steps,'segments':[{'a':a,'b':b} for a,b in sorted(segments)],'circles':circles,'labels':base_labels}
    _,raw = realize(Construction.model_validate(base))
    points = {n:np.asarray(v) for n,v in raw.items()}
    labels = list(base_labels)
    arrow_edges = set()
    for index,(obj,(a,b)) in enumerate(unbounded):
        ts = [_line_parameter(points[n],points[a],points[b])[0] for n in names]
        lo,hi = (min(0,min(ts))-.2,max(1,max(ts))+.2) if obj.kind == 'line' else (0,max(1,max(ts))+.2)
        ends = [a]
        if obj.kind == 'line':
            start = f'LineStart{index}'
            steps.append({'name':start,'op':'lerp','refs':[a,b],'values':[lo]})
            points[start] = points[a]+lo*(points[b]-points[a])
            ends = [start]
        end = f'LineEnd{index}'
        steps.append({'name':end,'op':'lerp','refs':[a,b],'values':[hi]})
        points[end] = points[a]+hi*(points[b]-points[a])
        ends.append(end)
        segments.discard(tuple(sorted((a,b))))
        segments.add(tuple(ends))
        if obj.kind == 'ray':
            arrow_edges.add(tuple(ends))
        if obj.label:
            labels.append({'point':end,'text':obj.label,'position':'right','dot':False})
    # Coalesce collinear contained strokes, including a segment already on a line.
    keep = []
    for a,b in sorted(segments,key=lambda edge:-_length(points[edge[0]]-points[edge[1]])):
        if any(all(-1e-7 <= _line_parameter(points[n],points[u],points[v])[0] <= 1+1e-7 and _line_parameter(points[n],points[u],points[v])[1] < 1e-7 for n in (a,b)) for u,v in keep):
            continue
        keep.append((a,b))
    selection = selected_relations(spec,identifiers)
    right_records = _right_angle_options(points,keep,selection['perpendiculars'])
    angles, seen_angles = [], set()
    for record in right_records:
        if record['options']:
            a,v,b = record['options'][0]
            key = (v,tuple(sorted((a,b))))
            if key not in seen_angles:
                angles.append({'a':a,'vertex':v,'b':b,'kind':'right'})
                seen_angles.add(key)
            record.update(status='drawn',rays=[a,v,b])
    bound_sectors = bind_sectors(selection['sectors'],points,keep)
    # This inexpensive default is not a collision finalizer or a research endpoint.
    directions = {'above':(0,1),'below':(0,-1),'left':(-1,0),'right':(1,0),'above left':(-1,1),'above right':(1,1),'below left':(-1,-1),'below right':(1,-1)}
    for label in labels:
        if label.get('dot') is False:
            continue
        origin = points[label['point']]
        incident = []
        for a,b in keep:
            t,error = _line_parameter(origin,points[a],points[b])
            if error < 1e-7 and -1e-7 <= t <= 1+1e-7:
                incident.extend(points[n]-origin for n in (a,b) if _length(points[n]-origin)>1e-7)
        def gap(item, incident=incident):
            v = np.asarray(item[1])
            return min((1-float(v@ray)/(_length(v)*_length(ray)) for ray in incident),default=2)
        label['position'] = max(directions.items(),key=gap)[0]
    source,raw = realize(Construction.model_validate({**base,'points':steps,'segments':[{'a':a,'b':b,'arrow':(a,b) in arrow_edges} for a,b in keep],'angles':angles,'labels':labels}))
    marks = []
    groups = equality_groups(selection,points,keep)
    for group,pairs in enumerate(groups,1):
        for a,b in sorted(pairs):
            marks.append(f'  \\path ({a})--node[midway,sloped] {{${"|"*group}$}} ({b});')
    arc_strokes,sector_records = sector_strokes(bound_sectors,points,np.eye(2),1)
    metric_strokes,metric_records = metric_and_parallel_strokes(spec,identifiers,selection,groups,points,keep,np.eye(2),1)
    marks.extend(arc_strokes+metric_strokes)
    source = source.replace(r'\end{tikzpicture}', '\n'.join(marks+[r'\end{tikzpicture}']))
    return source, {'world_points':raw,'segments':[{'points':[a,b],'dashed':False} for a,b in keep],
                    'clearance_score':_clearance(points,names,keep,circles),
                    'relation_marks':right_records,'sector_marks':sector_records,'metric_marks':metric_records,
                    'presentation_decisions':selection['decisions'],'equal_classes':groups}


def realize_spec(spec: GeometrySpec, instruction: str, *, seed: int = 0, candidates: int | None = None):
    started = perf_counter()
    _validate(spec,instruction)
    spec,instruction_audit = admit_instruction(spec,instruction)
    _validate(spec,instruction)
    roots,ordered,faces,loci = _lower(spec)
    all_names = [p.name for p in spec.points]+[n for n,_,_,_ in ordered if n not in {p.name for p in spec.points}]
    identifiers = {name:f'P{i}' for i,name in enumerate(all_names)}
    count = candidates if candidates is not None else (32 if spec.dimension == 2 else 12)
    if not 1 <= count <= 128:
        raise ValueError('Search budget must be between 1 and 128')
    rng, rejected, best, valid = random.Random(seed), Counter(), None, 0
    solver_attempts = []
    for index in range(count):
        try:
            steps = _steps(spec,roots,ordered,loci,rng,identifiers)
            mapped_faces = [[identifiers[n] for n in face] for face in faces]
            if spec.dimension == 3:
                raw = forward_points(steps)
                logical = {name:raw[internal] for name,internal in identifiers.items()}
                needs_solving = not all(row['pass'] for row in check_constraints(spec,logical))
                try:
                    validate_solid(raw,mapped_faces)
                except ValueError:
                    needs_solving = True
                if needs_solving:
                    steps,solver = solve_parameters(spec,steps,identifiers,roots,loci,faces=mapped_faces)
                    solver_attempts.append({'candidate':index,**solver})
                    raw = forward_points(steps)
                    logical = {name:raw[internal] for name,internal in identifiers.items()}
                failures = [row['kind'] for row in check_constraints(spec,logical) if not row['pass']]
                if failures:
                    rejected.update(failures)
                    continue
                validate_solid(raw,mapped_faces)
            if spec.dimension == 2:
                raw = forward_points(steps)
                logical = {name:raw[internal] for name,internal in identifiers.items()}
                if not all(row['pass'] for row in check_constraints(spec,logical)):
                    steps,solver = solve_parameters(spec,steps,identifiers,roots,loci)
                    solver_attempts.append({'candidate':index,**solver})
                    raw = forward_points(steps)
                    logical = {name:raw[internal] for name,internal in identifiers.items()}
                failures = [row['kind'] for row in check_constraints(spec,logical) if not row['pass']]
                if failures:
                    rejected.update(failures)
                    continue
                source,witness = _planar(spec,steps,identifiers)
                score = witness['clearance_score']
                quality = score
            else:
                segments,_,_ = _drawing(spec,identifiers)
                edges = {tuple(sorted((face[i],face[(i+1)%len(face)]))) for face in mapped_faces for i in range(len(face))}
                selection = selected_relations(spec,identifiers)
                groups = equality_groups(selection,raw,segments|edges)
                plan = SpatialConstruction.model_validate({'points':steps,'faces':mapped_faces,
                    'segments':[{'a':a,'b':b} for a,b in sorted(segments-edges)],
                    'labels':[{'point':identifiers[p.name],'text':p.name} for p in spec.points if p.visible],
                    'ticks':[{'a':a,'b':b,'group':group} for group,pairs in enumerate(groups,1) for a,b in sorted(pairs)]})
                source,witness = realize_spatial(plan,base=mapped_faces[0],minimum_clearance=.008,
                    perpendiculars=selection['perpendiculars'],sectors=selection['sectors'],plane_sections=selection['plane_sections'])
                world = {n:np.asarray(v) for n,v in witness['world_points'].items()}
                marks,metric_records = metric_and_parallel_strokes(spec,identifiers,selection,groups,world,
                    [r['points'] for r in witness['segments']],np.array(witness['projection']),witness['display_scale'])
                source = source.replace(r'\end{tikzpicture}', '\n'.join(marks+[r'\end{tikzpicture}']))
                witness.update(presentation_decisions=selection['decisions'],equal_classes=groups,metric_marks=metric_records)
                score = witness['camera']['clearance_score']
                quality = witness['camera']['quality_score']
            logical = {name:witness['world_points'][internal] for name,internal in identifiers.items()}
            checks = check_constraints(spec,logical)
            failures = [row['kind'] for row in checks if not row['pass']]
            if failures:
                rejected.update(failures)
                continue
            if score < .008:
                rejected['projected_clearance'] += 1
                continue
            valid += 1
            ranking = (witness['camera']['readable_perpendicular_count']+witness['camera']['readable_sector_count'] if spec.dimension == 3 else 0,quality)
            if best is None or ranking > best[0]:
                best = ranking,source,witness,checks,index,steps
            # Camera search already evaluates each feasible configuration. Three
            # validated spatial configurations bound extra aesthetic search cost.
            if spec.dimension == 3 and valid >= 3:
                break
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as error:
            rejected[str(error)] += 1
    attempted = index+1
    if best is None:
        raise SpecError('search_exhausted', f'No validated configuration in {count} candidates; not a proof of inconsistency. Rejections: {dict(rejected)}')
    ranking,source,witness,checks,index,steps = best
    quality = ranking[1]
    score = witness['camera']['clearance_score'] if spec.dimension == 3 else witness['clearance_score']
    evidence = {'spec':spec.model_dump(mode='json'),'identifier_map':identifiers,'roots':roots,
                'instruction_audit':instruction_audit,
                'lowered_operations':[{'name':n,'op':op,'refs':refs,'parameters':values} for n,op,refs,values in ordered],
                'candidate_count':attempted,'candidate_budget':count,'valid_candidates':valid,'selected_candidate':index,'rejections':dict(rejected),
                'solver_attempts':solver_attempts,
                'execution_operations':steps,'clearance_score':score,'presentation_score':quality,'checks':checks,'witness':witness,'seconds':perf_counter()-started,
                'scope':'Supplied-spec consistency only; source fidelity is independently evaluated. No TeX call in search.'}
    metrics = [r for r in spec.relations if r.kind == 'length']
    if metrics:
        reference = metrics[0]
        a,b = (np.asarray(witness['world_points'][identifiers[n]]) for n in reference.points)
        evidence['metric_frame'] = {'source_unit':'cm' if reference.unit else 'abstract',
                                   'parameter':metric_measure(reference).parameter or None,
                                   'source_units_per_drawing_unit':metric_measure(reference).coefficient*UNIT_CM[reference.unit]/_length(a-b),
                                   'reference_points':reference.points,
                                   'scope':'Uniform diagram scale; not a promise that physical paper lengths equal the given lengths.'}
    return source,evidence
