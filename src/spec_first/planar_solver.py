"""Bounded numerical solving of a construction's remaining degrees of freedom.

The exact operation DAG eliminates dependent coordinates. The solver only changes
root coordinates and locus parameters, never instructions, relations or strokes.
Convergence is not acceptance: the caller must independently check every relation.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import combinations
import math

import numpy as np
from spec_first.instruction_constraints import UNIT_CM
from spec_first.metric_expression import metric_measure


def line_circle_parameters(a, b, center, radius):
    """Both ordered parameters on the infinite line; () means no intersection."""
    a, b, center = (np.asarray(p, dtype=float) for p in (a, b, center))
    direction = b - a
    squared = float(direction @ direction)
    if squared <= 1e-24 or radius <= 0:
        raise ValueError('Degenerate line or circle')
    t = float((center-a) @ direction) / squared
    foot = a+t*direction
    distance_squared = float((foot-center) @ (foot-center))
    height_squared = radius*radius - distance_squared
    tolerance = 1e-12 * max(radius*radius, distance_squared)
    if height_squared < -tolerance:
        return ()
    offset = math.sqrt(max(0, height_squared) / squared)
    return (t-offset, t+offset)


def forward_points(steps):
    """Numerical counterpart of the named PGF operations, without drawing/TeX."""
    points = {}
    for step in steps:
        op, values = step['op'], step.get('values', [])
        refs = [points[n] for n in step.get('refs', [])]
        if op == 'free':
            value = np.asarray(values, dtype=float)
        elif op == 'lerp':
            a,b = refs
            value = a+values[0]*(b-a)
        elif op == 'translate':
            p,a,b = refs
            value = p+b-a
        elif op == 'rotate':
            o,p = refs
            theta = math.radians(values[0])
            rotation = np.array([[math.cos(theta),-math.sin(theta)], [math.sin(theta),math.cos(theta)]])
            value = o+rotation@(p-o)
        elif op in {'project','reflect'}:
            p,a,b = refs
            direction = b-a
            foot = a+float((p-a)@direction)/max(float(direction@direction),1e-24)*direction
            value = foot if op == 'project' else 2*foot-p
        elif op == 'intersect':
            a,b,c,d = refs
            u,v,w = b-a,d-c,c-a
            if len(u) == 3:
                # Closest-line point is only a search value. The residual below
                # enforces concurrence; the emission executor rejects skew lines.
                parameters = np.linalg.lstsq(np.column_stack((u,-v)),w,rcond=None)[0]
                value = a+parameters[0]*u
            else:
                determinant = u[0]*v[1]-u[1]*v[0]
                denominator = math.copysign(max(abs(determinant),1e-12),determinant)
                value = a+(w[0]*v[1]-w[1]*v[0])/denominator*u
        else:
            raise ValueError(f'Unsupported planar operation: {op}')
        points[step['name']] = value
    return points


def constraint_residuals(spec, points):
    """Signed equalities and branch barriers in an already normalized frame.

    Small positive margins discourage collapsed roots. They guide this local
    search only; check_constraints remains the separate acceptance authority.
    """
    residuals = []

    def norm(v):
        return float(np.linalg.norm(v))

    def cross(u,v):
        return float(np.linalg.norm(np.cross(u,v))) if len(u)==3 else float(u[0]*v[1]-u[1]*v[0])

    def line(p,a,b):
        u = b-a
        length = max(norm(u),1e-12)
        return float((p-a)@u)/length**2, cross(u,p-a)/length

    def unit(v):
        return v/max(norm(v),1e-12)

    metrics = [r for r in spec.relations if r.kind == 'length']
    reference = metrics[0] if metrics else None
    metric_scale = (norm(points[reference.points[0]]-points[reference.points[1]]) / (metric_measure(reference).coefficient*UNIT_CM[reference.unit])) if reference else 1
    for r in spec.relations:
        v,k = [points[n] for n in r.points],r.kind
        if k in {'midpoint','interpolation'}:
            t = .5 if k == 'midpoint' else r.values[0]
            residuals.extend(v[0]-v[1]-t*(v[2]-v[1]))
        elif k in {'on_line','on_segment','on_ray'}:
            t,error = line(*v)
            residuals.append(error)
            if k != 'on_line':
                residuals.append(max(0,-t))
            if k == 'on_segment':
                residuals.append(max(0,t-1))
        elif k in {'projection','reflection'}:
            image,source,a,b = v
            foot = image if k == 'projection' else (image+source)/2
            residuals.extend([line(foot,a,b)[1],float((source-image)@unit(b-a))])
        elif k == 'intersection':
            residuals.extend([line(v[0],v[1],v[2])[1],line(v[0],v[3],v[4])[1]])
        elif k == 'centroid':
            residuals.extend(v[0]-sum(v[1:])/3)
        elif k == 'parallelogram':
            residuals.extend(v[0]+v[2]-v[1]-v[3])
        elif k == 'equal_length':
            lengths = [norm(a-b) for a,b in zip(v[::2],v[1::2])]
            residuals.extend(length-lengths[0] for length in lengths[1:])
            residuals.append(max(0,.03-min(lengths)))
        elif k == 'equal_angle':
            a,o,b,c,p,d = v
            residuals.append(float(unit(a-o)@unit(b-o)-unit(c-p)@unit(d-p)))
        elif k == 'angle':
            a,o,b = v
            residuals.extend([float(unit(a-o)@unit(b-o))-math.cos(math.radians(r.values[0])),
                              max(0,.03-min(norm(a-o),norm(b-o)))])
        elif k in {'on_plane','perpendicular_planes','plane_angle'}:
            triples = [v[1:]] if k == 'on_plane' else [v[:3],v[3:]]
            normals = [np.cross(b-a,c-a) for a,b,c in triples]
            residuals.extend(max(0,.015-norm(n)) for n in normals)
            normals = [unit(n) for n in normals]
            if k == 'on_plane':
                residuals.append(float((v[0]-v[1])@normals[0]))
            else:
                cosine = float(normals[0]@normals[1])
                residuals.append(cosine if k == 'perpendicular_planes' else abs(cosine)-math.cos(math.radians(r.values[0])))
        elif k == 'dihedral_angle':
            a,b,c,d = v
            hinge = unit(c-b)
            first,last = a-b-hinge*float((a-b)@hinge),d-b-hinge*float((d-b)@hinge)
            residuals.extend([float(unit(first)@unit(last))-math.cos(math.radians(r.values[0])),
                              max(0,.03-min(norm(c-b),norm(first),norm(last)))])
        elif k == 'length':
            length = norm(v[0]-v[1])
            residuals.extend([length-metric_scale*metric_measure(r).coefficient*UNIT_CM[r.unit], max(0,.03-length)])
        elif k in {'length_ratio', 'shorter'}:
            first,second = norm(v[0]-v[1]),norm(v[2]-v[3])
            residuals.append(first-r.values[0]*second if k == 'length_ratio' else max(0,first-second+.001))
            residuals.append(max(0,.03-min(first,second)))
        elif k in {'perpendicular','parallel'}:
            u,w = v[1]-v[0],v[3]-v[2]
            residuals.append(float(unit(u)@unit(w)) if k == 'perpendicular' else cross(unit(u),unit(w)))
            residuals.append(max(0,.03-min(norm(u),norm(w))))
        elif k == 'same_side':
            a,b,c,d = v
            residuals.append(max(0,.0001-cross(unit(d-c),a-c)*cross(unit(d-c),b-c)))
        elif k == 'inside_angle':
            m,o,x,y = v
            determinant = cross(x-o,y-o)
            # Oriented sub-cones must agree with the enclosing minor sector.
            residuals.extend([max(0,.0001-cross(x-o,m-o)*determinant),
                              max(0,.0001-cross(m-o,y-o)*determinant)])
        elif k == 'distinct':
            residuals.append(max(0,.03-norm(v[0]-v[1])))
        elif k == 'noncollinear':
            residuals.append(max(0,.015-abs(cross(unit(v[1]-v[0]),unit(v[2]-v[0])))))
        elif k == 'partition':
            weights = r.values or [1]*(len(v)-1)
            for i,q in enumerate(v[1:-1],1):
                residuals.extend(q-v[0]-sum(weights[:i])/sum(weights)*(v[-1]-v[0]))
        elif k == 'parallel_section':
            n = (len(v)-1)//2
            apex,base,section = v[0],v[1:1+n],v[1+n:]
            parameters = [line(q,apex,end) for end,q in zip(base,section)]
            for t,error in parameters:
                residuals.extend([error,t-parameters[0][0],max(0,.005-t),max(0,t-.995)])
        else:
            raise ValueError(f'Unsupported planar constraint: {k}')
    for r in spec.relations:
        if r.kind == 'projection':
            for d in spec.draw:
                if d.kind == 'ray' and set(d.points) == set(r.points[2:]):
                    residuals.append(max(0,.01-line(points[r.points[0]],*[points[n] for n in d.points])[0]))
    visible = [points[p.name] for p in spec.points if p.visible]
    residuals.extend(max(0,.04-norm(a-b)) for a,b in combinations(visible,2))
    return np.asarray(residuals,dtype=float)


def solve_parameters(spec, steps, identifiers, roots, loci, *, faces=(), max_evaluations=80):
    """Optimize a bounded parameter vector; retain all named dependent steps."""
    from scipy.optimize import least_squares

    solved = deepcopy(steps)
    by_name = {step['name']:step for step in solved}
    original = forward_points(solved)
    anchors = [identifiers[n] for n in roots[:2]]
    origin = original[anchors[0]] if anchors else np.zeros(spec.dimension)
    scale = float(np.linalg.norm(original[anchors[1]]-origin)) if len(anchors)>1 else 5.0
    if scale < 1e-7:
        raise ValueError('Collapsed solver gauge')
    slots,initial,lower,upper = [],[],[],[]
    for name in roots[2:]:
        step = by_name[identifiers[name]]
        for axis in range(spec.dimension):
            slots.append((step,axis,True))
            initial.append((step['values'][axis]-origin[axis])/scale)
            lower.append(-8.0); upper.append(8.0)
    for name,kind in loci.items():
        step = by_name[identifiers[name]]
        bounds = {'on_line':(-50,50),'on_segment':(.001,.999),'on_ray':(.001,50),
                  'bisector':(.001,30),'perpendicular_bisector':(-30,30),'angle':(.1,179.9)}[kind]
        slots.append((step,0,False))
        initial.append(step['values'][0]);lower.append(bounds[0]);upper.append(bounds[1])
    if not slots:
        return solved,{'method':'fixed_construction','residual_calls':0}

    # Seed actual line/circle roots, including external roots beyond t=1.
    # This reads only relationships, never case IDs or source/target diagrams.
    seeded = []
    for r in spec.relations:
        if spec.dimension != 2 or r.kind != 'equal_length':
            continue
        pairs = list(zip(r.points[::2],r.points[1::2]))
        centers = set(pairs[0]).intersection(*(set(pair) for pair in pairs[1:]))
        if len(centers) != 1:
            continue
        center = next(iter(centers))
        ends = [b if a == center else a for a,b in pairs]
        for name in ends:
            if loci.get(name) not in {'on_line','on_segment','on_ray'}:
                continue
            step = by_name[identifiers[name]]
            others = [n for n in ends if n != name and n not in loci]
            if not others:
                continue
            a,b = (original[n] for n in step['refs'])
            o,through = original[identifiers[center]],original[identifiers[others[0]]]
            hits = line_circle_parameters(a,b,o,float(np.linalg.norm(through-o)))
            position = next(i for i,(s,_,_) in enumerate(slots) if s is step)
            hits = [t for t in hits if lower[position]<t<upper[position]]
            if hits:
                # Successive same-carrier points start on opposite roots.
                root = len([n for n in seeded if by_name[identifiers[n]]['refs']==step['refs']]) % len(hits)
                initial[position] = hits[root]
                seeded.append(name)
    calls = 0
    def unpack(x):
        for value,(step,axis,is_coordinate) in zip(x,slots):
            step['values'][axis] = float(origin[axis]+scale*value if is_coordinate else value)
        return forward_points(solved)

    def residual(x):
        nonlocal calls
        calls += 1
        raw = unpack(x)
        logical = {name:(raw[internal]-origin)/scale for name,internal in identifiers.items()}
        result = list(constraint_residuals(spec,logical))
        if spec.dimension == 3:
            normalized = {name:(point-origin)/scale for name,point in raw.items()}
            # A closed solid implies planar, nondegenerate faces and volume.
            # Preserve those obligations while moving roots; convexity is checked
            # independently by validate_solid before selecting a camera.
            vertices = sorted({name for face in faces for name in face})
            if vertices:
                xyz = np.array([normalized[name] for name in vertices])
                singular = np.linalg.svd(xyz-xyz.mean(axis=0),compute_uv=False)
                result.append(max(0,.03-singular[-1]))
            for face in faces:
                a,b,c = (normalized[name] for name in face[:3])
                normal = np.cross(b-a,c-a)
                area = float(np.linalg.norm(normal))
                result.append(max(0,.03-area))
                result.extend(float((normalized[name]-a)@normal)/max(area,1e-12) for name in face[3:])
            for step in solved:
                if step['op'] == 'intersect':
                    a,b,c,d = (normalized[name] for name in step['refs'])
                    point = normalized[step['name']]
                    direction = d-c
                    length = max(float(np.linalg.norm(direction)),1e-12)
                    result.append(float(np.linalg.norm(np.cross(point-c,direction)))/length)
        return np.asarray(result,dtype=float)

    result = least_squares(residual,np.asarray(initial),bounds=(lower,upper),method='trf',
                           max_nfev=max_evaluations,ftol=1e-11,xtol=1e-11,gtol=1e-11)
    unpack(result.x)
    return solved,{'method':'bounded_root_parameters','nfev':result.nfev,'residual_calls':calls,
                   'status':result.status,'max_residual':float(np.max(np.abs(result.fun))),
                   'line_circle_seeds':seeded,'variables':len(slots),'max_nfev':max_evaluations,
                   'dimension':spec.dimension}
