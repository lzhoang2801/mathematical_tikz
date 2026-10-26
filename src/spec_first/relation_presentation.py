"""Select source-backed cues and render angle sectors under one common projection.

This module never infers premises from numerical coincidences or adds carriers.
Its records describe presentation, not completeness of an extracted specification.
"""
from __future__ import annotations

from itertools import pairwise
import math

import numpy as np

from spec_first.instruction_constraints import UNIT_CM
from spec_first.metric_expression import metric_measure


def _edge(a, b):
    return tuple(sorted((a, b)))


def _sector(a, v, b):
    return (min(a, b), v, max(a, b))


def _merge(groups):
    merged = []
    for group in groups:
        group = set(group)
        matches = [old for old in merged if old & group]
        for old in matches:
            group |= old
            merged.remove(old)
        merged.append(group)
    return sorted(merged, key=lambda group: sorted(group))


def selected_relations(spec, identifiers):
    """One selection boundary shared by planar and spatial Spec First emission."""
    equal, angle_equal, parallel, lengths, sectors, perpendiculars = [], [], [], [], {}, []
    decisions = []
    plane_sections = {}
    map_points = lambda names: [identifiers[n] for n in names]
    def plane_key(kind, p):
        if kind == 'dihedral_angle':
            return 'dihedral',tuple(sorted(p[1:3])),tuple(sorted((p[0],p[3])))
        return 'planes',tuple(sorted((tuple(sorted(p[:3])),tuple(sorted(p[3:])))))
    def cue_key(r):
        p=r.points
        if r.kind in {'perpendicular_planes','plane_angle','dihedral_angle'}:
            return plane_key(r.kind,p)
        if r.kind=='angle':return r.kind,_sector(*p)
        if r.kind=='equal_angle':return r.kind,tuple(sorted((_sector(*p[:3]),_sector(*p[3:]))))
        if r.kind=='length':return r.kind,_edge(*p)
        if r.kind=='midpoint':return r.kind,p[0],_edge(*p[1:])
        if r.kind in {'perpendicular','parallel'}:return r.kind,tuple(sorted((_edge(*p[:2]),_edge(*p[2:]))))
        if r.kind=='equal_length' or (r.kind=='length_ratio' and r.values==[1]):
            return 'equality',tuple(sorted(_edge(a,b) for a,b in zip(p[::2],p[1::2])))
        return r.kind,tuple(p)
    suppressed={cue_key(r) for r in spec.relations if r.mark is False}
    for index, r in enumerate(spec.relations):
        p = map_points(r.points)
        selected = r.mark if r.mark is not None else r.kind in {
            'equal_length', 'equal_angle', 'projection', 'perpendicular', 'angle', 'length', 'length_ratio', 'partition',
            'perpendicular_planes','plane_angle','dihedral_angle'}
        record = {'relation':index, 'kind':r.kind, 'source_quote':r.source_quote,
                  'status':'suppressed' if r.mark is False else 'structural_or_mathematical'}
        decisions.append(record)
        if cue_key(r) in suppressed:
            if r.mark is True:
                raise ValueError('Conflicting explicit presentation requests for the same relation')
            record['status']='suppressed'
            continue
        if not selected:
            continue
        required = r.mark is True
        group = None
        if r.kind in {'perpendicular_planes','plane_angle','dihedral_angle'}:
            key = plane_key(r.kind,p)
            plane_sections[key] = {'kind':r.kind,'points':p,'value':90. if r.kind=='perpendicular_planes' else r.values[0],
                                   'label':'','source_quote':r.source_quote,'required':True}
        elif r.kind == 'equal_length':
            group = {_edge(a,b) for a,b in zip(p[::2],p[1::2])}
            common = set.intersection(*(set(e) for e in group))
            if not required and any(d.kind == 'circle' and identifiers[d.points[0]] in common
                    and _edge(*map_points(d.points)) in group for d in spec.draw):
                record['status'] = 'implicit_circle_radii'
                continue
        elif r.kind == 'midpoint':
            group = {_edge(p[0],p[1]), _edge(p[0],p[2])}
        elif r.kind == 'partition' and (not r.values or max(r.values) == min(r.values)):
            group = {_edge(a,b) for a,b in pairwise(p)}
        elif r.kind == 'length_ratio' and r.values == [1]:
            group = {_edge(*p[:2]), _edge(*p[2:])}
        elif r.kind == 'length':
            m = metric_measure(r)
            lengths.append({'points':_edge(*p), 'measure':m, 'unit':r.unit,
                            'source_quote':r.source_quote, 'required':required})
        elif r.kind == 'perpendicular':
            perpendiculars.append({'points':p,'mark':r.mark})
        elif r.kind == 'projection':
            h,source,a,b = p
            perpendiculars.append({'points':[source,h,a,b],'mark':r.mark})
        elif r.kind == 'angle':
            key=_sector(*p)
            required |= sectors.get(key,{}).get('required',False)
            if math.isclose(r.values[0],90,abs_tol=1e-10):
                perpendiculars.append({'points':[p[0],p[1],p[1],p[2]],'mark':r.mark})
                if required:
                    sectors[_sector(*p)] = {'points':list(_sector(*p)), 'value':90.,
                                            'required':True, 'group':0, 'label':'', 'right':True}
            else:
                sectors[_sector(*p)] = {'points':list(_sector(*p)), 'value':r.values[0],
                                        'required':required, 'group':0, 'label':''}
        elif r.kind == 'equal_angle':
            angle_equal.append({_sector(*p[:3]), _sector(*p[3:])})
        elif r.kind == 'parallel' and required:
            parallel.append({_edge(*p[:2]), _edge(*p[2:])})
        else:
            continue
        record['status'] = 'selected'
        if group:
            equal.append({'members':group, 'required':required})
    # Only source quantities, with compatible units and a shared parameter,
    # authorize equality. Solved segment lengths are deliberately not consulted.
    measure_groups = []
    for item in lengths:
        found = next((g for g in measure_groups if g[0]['measure'].parameter == item['measure'].parameter
            and math.isclose(g[0]['measure'].coefficient*UNIT_CM[g[0]['unit']],
                             item['measure'].coefficient*UNIT_CM[item['unit']],rel_tol=1e-10)),None)
        if found is None:
            measure_groups.append([item])
        else:
            found.append(item)
    for group in measure_groups:
        members = {item['points'] for item in group}
        if len(members) > 1:
            equal.append({'members':members,'required':any(item['required'] for item in group)})
    equal_classes = _merge(g['members'] for g in equal)
    required_edges = set().union(*(g['members'] for g in equal if g['required']))
    for group, members in enumerate(_merge(angle_equal),1):
        if group > 3:
            raise ValueError('At most three visible angle equality classes')
        for points in members:
            sector = sectors.setdefault(points,{'points':list(points),'value':None,'label':'','required':False})
            sector['group'] = group
            sector['equality_required'] = any(r.kind=='equal_angle' and r.mark is True
                and points in {_sector(*map_points(r.points[:3])),_sector(*map_points(r.points[3:]))} for r in spec.relations)
    for d in spec.draw:
        if d.kind == 'angle':
            points = _sector(*map_points(d.points))
            sector = sectors.setdefault(points,{'points':list(points),'value':None,'group':0})
            sector.update(required=True,label=d.label)
        elif d.kind in {'plane_angle','dihedral_angle'}:
            p=map_points(d.points)
            key=plane_key(d.kind,p)
            request=plane_sections.setdefault(key,{'kind':d.kind,'points':p,'value':None})
            request.update(required=True,label=d.label)
    return {'equal_classes':[sorted(g) for g in equal_classes], 'required_edges':sorted(required_edges),
            'lengths':lengths, 'sectors':list(sectors.values()), 'perpendiculars':perpendiculars,
            'parallel_classes':[sorted(g) for g in _merge(parallel)], 'plane_sections':list(plane_sections.values()), 'decisions':decisions}


def on_segment(p, a, b, tolerance=1e-7):
    v = b-a
    squared = float(v@v)
    if squared < 1e-14:
        return False
    t = float((p-a)@v)/squared
    return -tolerance <= t <= 1+tolerance and np.linalg.norm(p-a-t*v) <= tolerance*max(1,math.sqrt(squared))


def drawn_segment(points, segments, a, b):
    return any(on_segment(points[a],points[u],points[v]) and on_segment(points[b],points[u],points[v]) for u,v in segments)


def equality_groups(selection, points, segments):
    groups = []
    for members in selection['equal_classes']:
        missing = [e for e in members if not drawn_segment(points,segments,*e)]
        if any(e in selection['required_edges'] for e in missing):
            raise ValueError('Selected equality annotation has no drawn carrier')
        painted = [e for e in members if e not in missing]
        if len(painted) >= 2:
            lengths = [np.linalg.norm(points[a]-points[b]) for a,b in painted]
            if not np.allclose(lengths,lengths[0],rtol=1e-6,atol=1e-7):
                raise ValueError('False equality annotation')
            groups.append(painted)
    if len(groups) > 3:
        raise ValueError('At most three visible length equality classes')
    return groups


def bind_sectors(requests, points, segments):
    records = []
    for request in requests:
        a,v,b = request['points']
        u,w = points[a]-points[v],points[b]-points[v]
        lengths = np.linalg.norm(u),np.linalg.norm(w)
        if min(lengths) < 1e-7:
            raise ValueError('Degenerate angle annotation')
        cosine = float(np.clip(u@w/(lengths[0]*lengths[1]),-1,1))
        theta = math.acos(cosine)
        if min(theta,math.pi-theta) < 1e-5:
            raise ValueError('Degenerate angle sector')
        if request.get('value') is not None and not math.isclose(math.degrees(theta),request['value'],abs_tol=1e-4):
            raise ValueError('False numeric angle annotation')
        painted = all(drawn_segment(points,segments,v,end) for end in (a,b))
        if not painted and (request.get('required') or request.get('equality_required')):
            raise ValueError('Selected angle annotation has no drawn carrier')
        records.append({**request,'status':'available' if painted else 'no_drawn_carrier','world_radians':theta})
    for group in {r.get('group') for r in records if r.get('group')}:
        members = [r for r in records if r.get('group')==group]
        if len(members)<2 or not np.allclose([r['world_radians'] for r in members],members[0]['world_radians'],atol=1e-6):
            raise ValueError('False angle equality class')
        # One matching arc on its own no longer communicates an equality.
        if any(r['status']!='available' for r in members):
            for r in members:
                if r.get('equality_required'):
                    raise ValueError('Selected angle equality has no drawn carrier')
                r['group']=0
                if r['status']=='available' and (r.get('required') or r.get('value') is not None):
                    r['equality_status']='incomplete_equality_carriers'
                else:
                    r['status']='incomplete_equality_carriers'
    return records


def sector_shape(record, points, projection, scale):
    a,v,b = record['points']
    u,w = points[a]-points[v],points[b]-points[v]
    lu,lw = np.linalg.norm(u),np.linalg.norm(w)
    theta = record['world_radians']
    first = u/lu
    second = (w/lw-math.cos(theta)*first)/math.sin(theta)
    basis = np.column_stack((first,second))
    # The smallest singular value bounds compression of every ray in the sector,
    # not just its two boundary rays.
    retention = float(np.linalg.svd(projection@basis,compute_uv=False)[-1])
    radius = min(.25/max(scale*retention,1e-12),.22*min(lu,lw))
    size = radius*scale*retention
    return theta,lu,lw,radius,size,basis


def sector_strokes(records, points, projection, scale):
    strokes, evidence = [], []
    def fmt(x):
        return format(float(x),'.12g')
    for r in sector_visibility(records,points,projection,scale):
        if r['status'] != 'available':
            if r['status']=='unreadable_size' and (r.get('required') or r.get('equality_required')):
                raise ValueError('Selected angle sector is too small to read')
            evidence.append(r)
            continue
        theta,lu,lw,radius,size,basis = sector_shape(r,points,projection,scale)
        if size < .08:
            if r.get('required') or r.get('equality_required'):
                raise ValueError('Selected angle sector is too small to read')
            evidence.append({**r,'status':'unreadable_size','minimum_radius_cm':size})
            continue
        a,v,b = r['points']
        def coordinate(t,rad,geometry=(a,v,b,theta,lu,lw)):
            a,v,b,theta,lu,lw = geometry
            beta = rad*math.sin(t)/math.sin(theta)/lw
            alpha = rad*(math.cos(t)-math.cos(theta)*math.sin(t)/math.sin(theta))/lu
            return f'($({v})!{fmt(alpha)}!({a})+({v})!{fmt(beta)}!({b})-({v})$)'
        samples = np.linspace(0,theta,max(9,math.ceil(math.degrees(theta)/5)+1))
        curves = []
        for ring in range(max(1,r.get('group',0))):
            rad = radius*(1+.16*ring)
            vertices = points[v]+rad*(np.cos(samples)[:,None]*basis[:,0]+np.sin(samples)[:,None]*basis[:,1])
            if not r.get('right'):
                strokes.append('  \\draw[thin] '+'--'.join(coordinate(t,rad) for t in samples)+';')
            curves.append({'world_points':vertices.tolist(),'projected_points':(vertices@projection.T).tolist()})
        text = r.get('label','')
        if r.get('value') is not None:
            text += ('=' if text else '')+rf'{r["value"]:g}^{{\circ}}'
        if text:
            strokes.append(f'  \\node[fill=white,inner sep=1pt] at {coordinate(theta/2,radius*1.65)} {{${text}$}};')
        evidence.append({**r,'status':'drawn','minimum_radius_cm':size,'curves':curves,'text':text})
    return strokes,evidence


def sector_visibility(records, points, projection, scale):
    """An equality glyph class is atomic; a remaining singleton is misleading."""
    visible=[]
    for record in records:
        r=dict(record)
        if r['status']=='available':
            *_,size,_basis=sector_shape(r,points,projection,scale)
            r['minimum_radius_cm']=size
            if size<.08:r['status']='unreadable_size'
        visible.append(r)
    for group in {r.get('group') for r in visible if r.get('group')}:
        members=[r for r in visible if r.get('group')==group]
        if any(r['status']!='available' for r in members):
            for r in members:
                if not r.get('equality_required'):
                    r['group']=0
                    if r.get('value') is None and not r.get('required'):
                        r['status']='unreadable_equality_class'
    return visible


def metric_and_parallel_strokes(spec, identifiers, selection, groups, points, segments, projection, scale):
    strokes, records, labels = [], [], {}
    for label in spec.length_labels:
        edge = _edge(*(identifiers[n] for n in label.points))
        labels[edge] = {'measure':metric_measure(label),'unit':label.unit,'reason':'explicit_request'}
    for item in selection['lengths']:
        edge = item['points']
        group = next((g for g in groups if edge in g),None)
        if not drawn_segment(points,segments,*edge) and not item['required']:
            records.append({'kind':'length_label','points':list(edge),'status':'no_drawn_carrier'})
            continue
        if item['required'] or not group or not any(e in labels for e in group):
            labels.setdefault(edge,{**item,'reason':'selected_value' if item['required'] else 'equality_class_value'})
    for (a,b),label in labels.items():
        if not drawn_segment(points,segments,a,b):
            raise ValueError('Requested numeric length label has no drawn carrier')
        text = label['measure'].tex+(rf'\,\mathrm{{{label["unit"]}}}' if label['unit'] else '')
        strokes.append(f'  \\path ({a})--node[midway,sloped,above,fill=white,inner sep=1pt] {{${text}$}} ({b});')
        records.append({'kind':'length_label','points':[a,b],'text':text,'reason':label['reason'],'status':'drawn'})
    for group,members in enumerate(selection['parallel_classes'],1):
        if group > 3:
            raise ValueError('At most three visible parallel classes')
        reference = points[members[0][1]]-points[members[0][0]]
        for a,b in members:
            if not drawn_segment(points,segments,a,b):
                raise ValueError('Selected parallel annotation has no drawn carrier')
            direction = points[b]-points[a]
            cosine = float(direction@reference)/(np.linalg.norm(direction)*np.linalg.norm(reference))
            if not math.isclose(abs(cosine),1,abs_tol=1e-6):
                raise ValueError('False parallel annotation')
            xy = projection@direction
            if np.linalg.norm(xy)*scale < .4:
                raise ValueError('Selected parallel carrier is too short')
            axis = xy/np.linalg.norm(xy)*np.sign(cosine)
            normal = np.array([-axis[1],axis[0]])
            for i in range(group):
                offsets = [(-.07+(i-(group-1)/2)*.1)*axis+.045*normal,
                           (i-(group-1)/2)*.1*axis,
                           (-.07+(i-(group-1)/2)*.1)*axis-.045*normal]
                coords = [f'($({a})!.5!({b})+({p[0]:.12g}cm,{p[1]:.12g}cm)$)' for p in offsets]
                strokes.append('  \\draw[thin] '+'--'.join(coords)+';')
            records.append({'kind':'parallel','points':[a,b],'group':group,'status':'drawn'})
    return strokes,records
