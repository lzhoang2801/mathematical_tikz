"""Bounded affine 3D construction, convex-solid validation and view selection.

Only one closed convex polyhedron is supported. Faces are geometry, not fills;
hidden lines follow its opaque-surface drawing convention. No TeX is used while
choosing the view. This module does not infer the instruction's requirements.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, pairwise, product
import math
from typing import Literal

import numpy as np
from pydantic import Field, FiniteFloat

from spec_first.construction import Name, StrictModel
from spec_first.plane_sections import normal_sections, visibility_parts
from spec_first.relation_presentation import bind_sectors, sector_strokes, sector_visibility
from spec_first.relation_presentation import on_segment as _on_segment


class SpatialPoint(StrictModel):
    name: Name
    op: Literal['free', 'lerp', 'translate', 'intersect', 'project']
    refs: list[Name] = Field(default_factory=list, max_length=4, description='Earlier names: free []; lerp [A,B]; translate [P,A,B] means P+B-A; project [P,A,B] is the world-metric perpendicular foot of P on AB; intersect [A,B,C,D] for intersecting 3D lines AB and CD.')
    values: list[FiniteFloat] = Field(default_factory=list, max_length=3, description='free [x,y,z] in cm; lerp [t] means A+t(B-A); others [].')


class SpatialSegment(StrictModel):
    a: Name
    b: Name


class SpatialTick(SpatialSegment):
    group: int = Field(ge=1, le=3)


class SpatialLabel(StrictModel):
    point: Name
    text: str = Field(pattern=r"^[A-Za-z](?:[A-Za-z0-9]*|_[0-9]+)'{0,2}$", max_length=20)
    position: Literal['auto', 'above', 'below', 'left', 'right', 'above left', 'above right', 'below left', 'below right'] = 'auto'


class SpatialConstruction(StrictModel):
    points: list[SpatialPoint] = Field(min_length=4, max_length=32)
    faces: list[list[Name]] = Field(min_length=4, max_length=12, description='Each face is a cyclic vertex list (3 to 8 names). One closed, nondegenerate convex solid only. All solid edges are drawn automatically.')
    segments: list[SpatialSegment] = Field(default_factory=list, max_length=32, description='Additional requested segments on or inside the solid, including section boundaries/diagonals. No duplicate solid edges. Visibility is calculated from faces and the selected view, never from a point name or auxiliary status.')
    ticks: list[SpatialTick] = Field(default_factory=list, max_length=24, description='Equality classes on already drawn carriers; same group must have equal 3D lengths. Ticks do not redraw a carrier.')
    labels: list[SpatialLabel] = Field(min_length=4, max_length=32)
    scale: FiniteFloat = Field(default=1, ge=0.25, le=3)


def _norm(vector):
    return float(np.linalg.norm(vector))


def _fmt(number):
    return format(0.0 if abs(number) < 1e-12 else number, '.12g')


def realize_points(steps: list[SpatialPoint]):
    points, free, dependent = {}, [], []
    arity = {'free': (0, 3), 'lerp': (2, 1), 'translate': (3, 0), 'intersect': (4, 0), 'project': (3, 0)}
    for step in steps:
        name, refs, values = step.name, step.refs, step.values
        if name in points or (len(refs), len(values)) != arity[step.op]:
            raise ValueError(f'Duplicate point or wrong operation arity: {name}')
        if any(ref not in points for ref in refs):
            raise ValueError(f'Unknown or forward reference at {name}')
        if step.op == 'free':
            value = np.asarray(values, dtype=float)
            expression = ','.join(map(_fmt, value))
        elif step.op == 'lerp':
            a, b = refs
            if _norm(points[b] - points[a]) < 1e-7:
                raise ValueError(f'Degenerate interpolation at {name}')
            value = points[a] + values[0] * (points[b] - points[a])
            expression = f'$({a})!{_fmt(values[0])}!({b})$'
        elif step.op == 'project':
            p,a,b = refs
            direction = points[b]-points[a]
            if _norm(direction) < 1e-7:
                raise ValueError(f'Degenerate spatial projection at {name}')
            parameter = float((points[p]-points[a])@direction)/float(direction@direction)
            value = points[a]+parameter*direction
            # PGF's screen-space foot would change the world relation.
            expression = f'$({a})!{_fmt(parameter)}!({b})$'
        elif step.op == 'translate':
            p, a, b = refs
            if _norm(points[b] - points[a]) < 1e-7:
                raise ValueError(f'Zero translation at {name}')
            value = points[p] + points[b] - points[a]
            expression = f'$({p})+({b})-({a})$'
        else:
            a, b, c, d = refs
            u, v = points[b] - points[a], points[d] - points[c]
            matrix = np.column_stack((u, -v))
            if min(_norm(u), _norm(v)) < 1e-7 or np.linalg.cond(matrix) > 1e7:
                raise ValueError(f'Parallel/degenerate intersection at {name}')
            ts = np.linalg.lstsq(matrix, points[c] - points[a], rcond=None)[0]
            value = points[a] + ts[0] * u
            if _norm(value - points[c] - ts[1] * v) > 1e-7 * max(_norm(u), _norm(v)):
                raise ValueError(f'Skew 3D lines at {name}')
            expression = f'intersection of {a}--{b} and {c}--{d}'
        if not np.isfinite(value).all() or np.max(np.abs(value)) > 50:
            raise ValueError(f'Invalid or oversized 3D coordinate: {name}')
        points[name] = value
        (free if step.op == 'free' else dependent).append(f'  \\coordinate ({name}) at ({expression});')
    return points, free, dependent


def validate_solid(points, faces):
    """Return outward planes and unique edges of a closed convex boundary."""
    if any(not 3 <= len(face) <= 8 or len(set(face)) != len(face) for face in faces):
        raise ValueError('Faces need 3 to 8 distinct cyclic vertices')
    names = sorted({name for face in faces for name in face})
    if any(name not in points for name in names):
        raise ValueError('Face references an unknown point')
    vertices = np.array([points[name] for name in names])
    center = vertices.mean(axis=0)
    if np.linalg.matrix_rank(vertices - center, tol=1e-7) != 3:
        raise ValueError('Solid has no 3D volume')
    scale = max(_norm(point - center) for point in vertices)
    tolerance = 1e-7 * max(1, scale)
    planes, counts = [], Counter()
    for face in faces:
        xyz = np.array([points[name] for name in face])
        normal = np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])
        if _norm(normal) <= tolerance**2:
            raise ValueError('Degenerate face')
        normal /= _norm(normal)
        if normal @ (xyz.mean(axis=0) - center) < 0:
            normal = -normal
        offsets = (vertices - xyz[0]) @ normal
        if np.max(np.abs((xyz - xyz[0]) @ normal)) > tolerance or np.max(offsets) > tolerance:
            raise ValueError('Nonplanar face or nonconvex solid')
        turns = [float(np.cross(xyz[(i+1) % len(xyz)] - xyz[i], xyz[(i+2) % len(xyz)] - xyz[(i+1) % len(xyz)]) @ normal) for i in range(len(xyz))]
        if min(turns) <= tolerance**2 and max(turns) >= -tolerance**2:
            raise ValueError('Face vertex order is not a convex cycle')
        if abs(float((center - xyz[0]) @ normal)) <= tolerance:
            raise ValueError('Degenerate solid interior')
        planes.append((xyz[0], normal))
        counts.update(tuple(sorted((face[i], face[(i+1) % len(face)]))) for i in range(len(face)))
    if any(count != 2 for count in counts.values()) or len(names) - len(counts) + len(faces) != 2:
        raise ValueError('Faces do not form one closed convex solid')
    return planes, sorted(counts)


def hidden_segment(a, b, planes, direction):
    """A contained segment is visible iff its midpoint lies on a front face."""
    midpoint = (a + b) / 2
    return not any(abs(float((midpoint - origin) @ normal)) < 1e-6 and normal @ direction > 1e-6 for origin, normal in planes)


def _camera_frames(points, faces, planes, base):
    """Frames follow geometry, never point names or the solver's arbitrary axes."""
    if base is not None:
        cycles = [face for face in faces if len(face) == len(base) and set(face) == set(base)]
        if not cycles or len(set(base)) != len(base):
            raise ValueError('Semantic base must be one complete solid face')
        cycle = cycles[0]
        doubled = cycle + cycle
        if not any(list(base) == doubled[i:i+len(base)] or list(reversed(base)) == doubled[i:i+len(base)] for i in range(len(cycle))):
            raise ValueError('Semantic base must be a cyclic face')
        selected, provenance = cycles, 'declared_base'
    else:
        # A general construction has no semantic base. Use its largest faces as
        # geometric frame candidates and record the distinction in the witness.
        def area(face):
            origin = points[face[0]]
            return sum(_norm(np.cross(points[a]-origin, points[b]-origin)) for a,b in pairwise(face[1:])) / 2
        areas = [area(face) for face in faces]
        selected = [face for face,value in zip(faces,areas) if math.isclose(value,max(areas),rel_tol=1e-8)]
        provenance = 'largest_face_geometric_fallback'
    frames = []
    for face in selected:
        z = -planes[faces.index(face)][1]
        edges = [(points[b]-points[a]) for a,b in zip(face,face[1:]+face[:1])]
        longest = max(map(_norm,edges))
        for edge in edges:
            if not math.isclose(_norm(edge),longest,rel_tol=1e-8):
                continue
            for sign in (-1,1):
                x = sign*edge/_norm(edge)
                frame = np.array([x,np.cross(z,x),z])
                if not any(np.allclose(frame,old[0],atol=1e-9) for old in frames):
                    frames.append((frame,face))
    return frames,provenance


def _right_angle_options(points, segments, perpendiculars):
    """Bind supplied perpendiculars to drawn rays; never infer them from pixels."""
    records = []
    for relation in perpendiculars:
        a,b,c,d = relation['points']
        if any(n not in points for n in (a,b,c,d)):
            raise ValueError('Perpendicular annotation references an unknown point')
        u,v = points[b]-points[a],points[d]-points[c]
        if min(_norm(u),_norm(v)) < 1e-7 or abs(float(u@v))/(_norm(u)*_norm(v)) > 1e-6:
            raise ValueError('False spatial right-angle annotation')
        options = []
        if relation.get('mark') is not False:
            for vertex,origin in points.items():
                if not (_on_segment(origin,points[a],points[b]) and _on_segment(origin,points[c],points[d])):
                    continue
                for first,last in product((a,b),(c,d)):
                    if min(_norm(points[first]-origin),_norm(points[last]-origin)) < 1e-7:
                        continue
                    if all(any(_on_segment(origin,points[p],points[q]) and _on_segment(points[end],points[p],points[q]) for p,q in segments) for end in (first,last)):
                        options.append((first,vertex,last))
        status = 'suppressed' if relation.get('mark') is False else ('available' if options else 'no_drawn_incident_rays')
        if relation.get('mark') is True and not options:
            raise ValueError('Selected right angle has no drawn carrier with incident rays')
        records.append({'points':list(relation['points']),'mark':relation.get('mark'),'status':status,'options':options})
    return records


def _projected_intersections_valid(points, projection, intersections):
    for refs in intersections:
        a,b,c,d = refs
        u,v = projection@(points[b]-points[a]),projection@(points[d]-points[c])
        lengths = _norm(u)*_norm(v)
        if lengths < 1e-12 or abs(float(u[0]*v[1]-u[1]*v[0]))/lengths < .05:
            return False
    return True


def choose_view(points, labels, segments, planes, *, faces, base=None, focus=(), intersections=(), right_angles=(), sectors=(), minimum_clearance=1e-4, page_scale=1):
    """Bounded, base-relative orthographic search with explicit quality terms.

    Clearance saturates at 2.5% of the diagram span. Carrier retention and mark
    conditioning then influence selection instead of rewarding an ever wider
    spread. These are presentation preferences, not mathematical constraints.
    """
    frames,provenance = _camera_frames(points,faces,planes,base)
    names = [label.point for label in labels]
    named = np.array([points[n] for n in names])
    pairs = list(combinations(range(len(names)),2))
    drawn = np.array([points[n] for n in sorted(set(names) | {n for edge in segments for n in edge})])
    starts = np.array([points[a] for a,b in segments])
    vectors = np.array([points[b]-points[a] for a,b in segments])
    lengths = np.linalg.norm(vectors,axis=1)
    unrelated = np.array([[not _on_segment(points[n],points[a],points[b]) for a,b in segments] for n in names])
    focus_indices = [i for i,edge in enumerate(segments) if frozenset(edge) in {frozenset(e) for e in focus}]
    best,candidate_count = None,0
    for frame,face in frames:
        upper = [points[n] for n in {n for f in faces for n in f} if n not in face]
        base_xyz = np.array([points[n] for n in face])
        height = max(float((p-base_xyz[0])@frame[2]) for p in upper)
        for azimuth,elevation in product(range(0,360,30),(10,20,30,40)):
            a,e = map(math.radians,(azimuth,elevation))
            direction = np.array([math.cos(e)*math.cos(a),math.cos(e)*math.sin(a),math.sin(e)]) @ frame
            projection = np.array([[-math.sin(a),math.cos(a),0],[-math.sin(e)*math.cos(a),-math.sin(e)*math.sin(a),math.cos(e)]]) @ frame
            if min(abs(float(normal@direction)) for _,normal in planes) < .025 or not _projected_intersections_valid(points,projection,intersections):
                continue
            projected = named@projection.T
            distances = np.array([_norm(projected[i]-projected[j]) for i,j in pairs])
            drawn_xy = drawn@projection.T
            span = float(np.linalg.norm(drawn_xy[:,None,:]-drawn_xy[None,:,:],axis=2).max())
            if span < 1e-6:
                continue
            pv = vectors@projection.T
            delta = projected[:,None,:]-(starts@projection.T)[None,:,:]
            squared = np.einsum('ij,ij->i',pv,pv)
            t = np.clip(np.einsum('nsj,sj->ns',delta,pv)/np.maximum(squared,1e-14),0,1)
            carrier_distances = np.linalg.norm(delta-t[:,:,None]*pv[None,:,:],axis=2)
            clearance = min(float(distances.min()),float(carrier_distances[unrelated].min()) if unrelated.any() else span)/span
            if clearance < minimum_clearance:
                continue
            retention = np.sqrt(squared)/lengths
            xy = {name:projection@p for name,p in points.items()}
            mark_quality,readable_marks,required_missing = [],0,False
            for relation in right_angles:
                qualities,readable = [],[]
                for first,vertex,last in relation['options']:
                    u,v = xy[first]-xy[vertex],xy[last]-xy[vertex]
                    conditioning = abs(float(u[0]*v[1]-u[1]*v[0]))/(_norm(u)*_norm(v))
                    wu,wv = _norm(points[first]-points[vertex]),_norm(points[last]-points[vertex])
                    minimum_leg = min(.18,.18*min(wu,wv)*min(_norm(u)/wu,_norm(v)/wv)*8*page_scale/span)
                    qualities.append(conditioning)
                    if conditioning >= .20 and minimum_leg >= .08:
                        readable.append(conditioning)
                if qualities:
                    mark_quality.append(max(readable or qualities))
                    readable_marks += bool(readable)
                    required_missing |= relation.get('mark') is True and not readable
            readable_sectors = 0
            for sector in sector_visibility(sectors,points,projection,8*page_scale/span):
                readable_sectors += sector['status']=='available'
                required_missing |= (sector.get('required',False) or sector.get('equality_required',False)) and sector['status']!='available'
            # Reject unreadable marks, not nonvertical or legitimately thin solids.
            if required_missing or (mark_quality and min(mark_quality) < .20):
                continue
            components = {'clearance':min(clearance/.025,1.0),'carrier_retention':float(retention.min()),
                          'requested_retention':float(retention[focus_indices].min()) if focus_indices else 1.0,
                          'relation_mark_conditioning':min(mark_quality,default=1.0),
                          'base_area_retention':math.sin(e),
                          'height_separation':float(np.clip((max(float((projection@p)[1]) for p in upper)-float((base_xyz@projection.T)[:,1].max()))/(height*math.cos(e)),0,1))}
            quality = sum(components.values())/len(components)
            candidate_count += 1
            # Rounded scores avoid world-frame floating point noise choosing a
            # different view among symmetric ties. No identifier breaks a tie.
            key = (readable_marks+readable_sectors,round(quality,10),round(clearance,10))
            if best is None or key > best[0]:
                camera = {'policy':'base-relative-relations-v2','azimuth':azimuth,'elevation':elevation,
                          'frame_provenance':provenance,'frame_face':list(face),'frame':frame.tolist(),
                          'clearance_score':clearance,'quality_score':quality,'components':components,'span':span}
                camera['readable_perpendicular_count'] = readable_marks
                camera['readable_sector_count'] = readable_sectors
                best = key,projection,direction,xy,camera
    if best is None:
        raise ValueError('No readable nondegenerate camera candidate')
    best[-1]['valid_view_candidates'] = candidate_count
    return best[1:]


def _right_angle_strokes(points, xy, projection, relations, display_scale):
    strokes,records,occupied,drawn = [],[],[],set()
    for relation in relations:
        record = {key:value for key,value in relation.items() if key != 'options'}
        if not relation['options']:
            records.append(record)
            continue
        choices = []
        for first,vertex,last in relation['options']:
            origin = points[vertex]
            u,v = points[first]-origin,points[last]-origin
            ulen,vlen = _norm(u),_norm(v)
            u,v = u/ulen,v/vlen
            pu,pv = projection@u,projection@v
            conditioning = abs(float(pu[0]*pv[1]-pu[1]*pv[0]))/(_norm(pu)*_norm(pv))
            if conditioning < .20:
                continue
            side = min(.18/(display_scale*min(_norm(pu),_norm(pv))),.18*min(ulen,vlen))
            corners = np.array([origin+side*u,origin+side*(u+v),origin+side*v])
            projected = corners@projection.T
            separation = min((_norm(projected[1]-p)*display_scale for p in occupied),default=1.0)
            minimum_leg = min(_norm(projected[1]-projected[0]),_norm(projected[2]-projected[1]))*display_scale
            choices.append(((minimum_leg>=.08,round(min(conditioning,separation/.25),10)),first,vertex,last,side,ulen,vlen,corners,projected))
        _,first,vertex,last,side,ulen,vlen,corners,projected = max(choices,key=lambda row:row[0])
        minimum_leg = min(_norm(projected[1]-projected[0]),_norm(projected[2]-projected[1]))*display_scale
        if minimum_leg < .08:
            if relation.get('mark') is True:
                raise ValueError('Selected spatial right-angle mark is too small to read')
            record.update(status='unreadable_size',minimum_leg_cm=minimum_leg)
            records.append(record)
            continue
        f,g = _fmt(side/ulen),_fmt(side/vlen)
        key = tuple(np.round(corners[[0,1,2] if tuple(corners[0])<tuple(corners[2]) else [2,1,0]].ravel(),10))
        if key not in drawn:
            strokes.append(f'  \\draw[thin] ($({vertex})!{f}!({first})$)--($({vertex})!{f}!({first})+({vertex})!{g}!({last})-({vertex})$)--($({vertex})!{g}!({last})$);')
            drawn.add(key)
        occupied.append(projected[1])
        record.update(status='drawn',rays=[first,vertex,last],world_corners=corners.tolist(),projected_corners=projected.tolist(),
                      minimum_leg_cm=minimum_leg)
        records.append(record)
    return strokes,records


def _tick_strokes(points, xy, segments, ticks, label_names, relation_marks, display_scale):
    """Keep validated equality ticks away from dots, crossings and corner marks."""
    page = {n:p*display_scale for n,p in xy.items()}
    dots = [page[n] for n in label_names]
    corners = [pair for mark in relation_marks if mark['status']=='drawn'
               for pair in pairwise(np.asarray(mark['projected_corners'])*display_scale)]
    strokes,records,occupied = [],[],[]
    def distance(point, a, b):
        vector = b-a
        fraction = np.clip(float((point-a)@vector)/max(float(vector@vector),1e-14),0,1)
        return _norm(point-a-fraction*vector)
    def geometry_key(tick):
        endpoints = sorted(tuple(np.round(page[n],10)) for n in (tick.a,tick.b))
        return endpoints,tick.group
    for tick in sorted(ticks,key=geometry_key):
        a,b = tick.a,tick.b
        obstacles = corners+[(page[u],page[v]) for u,v in segments
            if not all(_on_segment(points[n],points[u],points[v]) for n in (a,b))]
        # A fixed page-space margin covers the tick glyph and the point dot.
        # This is a geometric placement check, not a text/readability verdict.
        margin = .22+.04*(tick.group-1)
        choices = []
        for fraction in np.linspace(.2,.8,13):
            center = page[a]+fraction*(page[b]-page[a])
            clearance = min([_norm(center-p) for p in dots]
                +[distance(center,u,v) for u,v in obstacles]
                +[_norm(center-p)-radius for p,radius in occupied])
            key = (round(min(clearance/margin,1),10),-round(abs(fraction-.5),10),tuple(np.round(center,10)))
            choices.append((key,float(fraction),center,clearance))
        _,fraction,center,clearance = max(choices,key=lambda row:row[0])
        strokes.append(f'  \\path ({a})--node[pos={_fmt(fraction)},sloped] {{${"|"*tick.group}$}} ({b});')
        occupied.append((center,margin/2))
        records.append({'points':[a,b],'group':tick.group,'fraction':fraction,
                        'status':'placed' if clearance>=margin-1e-10 else 'crowded',
                        'clearance_cm':clearance,'required_clearance_cm':margin})
    return strokes,records


def realize_spatial(plan: SpatialConstruction, *, base=None, perpendiculars=(), sectors=(), plane_sections=(), minimum_clearance=1e-4):
    points, free, dependent = realize_points(plan.points)
    planes, edges = validate_solid(points, plan.faces)
    segments = list(edges)
    for segment in plan.segments:
        if segment.a not in points or segment.b not in points:
            raise ValueError('Segment references an unknown point')
        edge = tuple(sorted((segment.a, segment.b)))
        if edge in segments or _norm(points[edge[0]] - points[edge[1]]) < 1e-7:
            raise ValueError(f'Duplicate or degenerate segment {edge}')
        segments.append(edge)
    names = [label.point for label in plan.labels]
    if len(set(names)) != len(names) or len({label.text for label in plan.labels}) != len(names) or any(name not in points for name in names):
        raise ValueError('Unknown or duplicate visible label')
    for name in {name for edge in segments for name in edge} | set(names):
        if any((points[name] - origin) @ normal > 1e-6 for origin, normal in planes):
            raise ValueError('This pilot supports contained segments and labels only')
    tick_groups = defaultdict(list)
    for tick in plan.ticks:
        if tick.a not in points or tick.b not in points:
            raise ValueError('Tick references an unknown point')
        length = _norm(points[tick.a] - points[tick.b])
        if length < 1e-7 or not any(_on_segment(points[tick.a], points[a], points[b]) and _on_segment(points[tick.b], points[a], points[b]) for a, b in segments):
            raise ValueError('Equality tick has no drawn carrier')
        tick_groups[tick.group].append(length)
    if any(len(values) < 2 or not np.allclose(values, values[0], rtol=1e-6, atol=1e-7) for values in tick_groups.values()):
        raise ValueError('False or singleton spatial equality class')
    generated,section_edges,section_corners,section_sectors,section_records = normal_sections(plane_sections,points,planes,set(segments)) if plane_sections else ({},set(),[],[],[])
    points.update(generated)
    segments.extend(sorted(section_edges))
    perpendiculars = [*perpendiculars,*section_corners]
    sectors = [*sectors,*section_sectors]
    right_angles = _right_angle_options(points,segments,perpendiculars)
    bound_sectors = bind_sectors(sectors,points,segments)
    projection,direction,xy,camera = choose_view(points,plan.labels,segments,planes,faces=plan.faces,base=base,
        focus=[(s.a,s.b) for s in plan.segments],intersections=[p.refs for p in plan.points if p.op == 'intersect'],right_angles=right_angles,sectors=bound_sectors,minimum_clearance=minimum_clearance,page_scale=plan.scale)
    display_scale = 8*plan.scale/camera['span']
    # Center and uniformly normalize only the emitted coordinate frame. This
    # avoids TeX dimension overflow and loss of precision for tiny translated
    # worlds. The original world and affine dependencies are preserved below.
    coordinate_origin = np.mean(list(points.values()),axis=0)
    free = [f'  \\coordinate ({p.name}) at ({",".join(map(_fmt,(points[p.name]-coordinate_origin)*display_scale))});'
            for p in plan.points if p.op == 'free']
    free.extend(f'  \\coordinate ({name}) at ({",".join(map(_fmt,(point-coordinate_origin)*display_scale))});' for name,point in generated.items())
    styles = {edge: hidden_segment(points[edge[0]], points[edge[1]], planes, direction) for edge in segments}
    axes = ','.join(f'{axis}={{({_fmt(projection[0,i])}cm,{_fmt(projection[1,i])}cm)}}' for i, axis in enumerate('xyz'))
    strokes = [f'  \\draw[{"dashed" if styles[a,b] else ""}] ({a})--({b});' for a, b in sorted(segments, key=lambda edge: not styles[edge]) if (a,b) not in section_edges]
    section_visibility = []
    for a,b in sorted(section_edges):
        parts=visibility_parts(points[a],points[b],planes,direction)
        for part in parts:
            left,right=_fmt(part['start']),_fmt(part['end'])
            strokes.append(f'  \\draw[thin,{"dashed" if part["dashed"] else ""}] ($({a})!{left}!({b})$)--($({a})!{right}!({b})$);')
        styles[a,b]=parts[0]['dashed'] if len(parts)==1 else None
        section_visibility.append({'points':[a,b],'parts':parts})
    angle_strokes,relation_marks = _right_angle_strokes(points,xy,projection,right_angles,display_scale)
    arcs,sector_marks = sector_strokes(bound_sectors,points,projection,display_scale)
    tick_strokes,tick_marks = _tick_strokes(points,xy,segments,plan.ticks,names,relation_marks,display_scale)
    strokes.extend(tick_strokes)
    strokes.extend(angle_strokes)
    strokes.extend(arcs)
    labels = []
    directions = {'right': (1,0), 'above right': (1,1), 'above': (0,1), 'above left': (-1,1), 'left': (-1,0), 'below left': (-1,-1), 'below': (0,-1), 'below right': (1,-1)}
    for label in plan.labels:
        position = label.position
        if position == 'auto':
            # Choose an angular gap among all incident carriers; text layout is
            # still reviewed after rendering, not claimed solved by this heuristic.
            rays = []
            for a, b in segments:
                if _on_segment(points[label.point], points[a], points[b]):
                    rays.extend(xy[n] - xy[label.point] for n in (a,b) if _norm(xy[n] - xy[label.point]) > 1e-7)
            def gap(item, rays=rays):
                vector = np.asarray(item[1], dtype=float)
                return min((1 - float(vector @ ray) / (_norm(vector)*_norm(ray)) for ray in rays), default=2)
            position = max(directions.items(), key=gap)[0]
        labels.append(f'  \\node[circle,fill,inner sep=1.35pt,label={{{position}:${label.text}$}}] at ({label.point}) {{}};')
    source = '\n'.join([f'\\begin{{tikzpicture}}[{axes},thick,line cap=round,line join=round,font=\\footnotesize,label distance=2pt]', *free, '', r'  \begin{pgfinterruptboundingbox}', *dependent, r'  \end{pgfinterruptboundingbox}', '', *strokes, '', *labels, r'\end{tikzpicture}'])
    witness = {'world_points': {k: v.tolist() for k,v in points.items()}, 'projection': projection.tolist(), 'view_direction': direction.tolist(),
               'camera':camera,'display_scale':display_scale,'coordinate_origin':coordinate_origin.tolist(),'relation_marks':relation_marks,'sector_marks':sector_marks,'tick_marks':tick_marks,
               'segments': [{'points': list(edge), 'dashed': styles[edge]} for edge in segments], 'faces': plan.faces,
               'normal_sections':section_records,'section_visibility':section_visibility,
               'section_operations':[{'name':name,'op':'free','values':point.tolist()} for name,point in generated.items()]}
    return source, witness
