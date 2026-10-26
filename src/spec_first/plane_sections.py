"""Normal sections of actual planes/half-planes, independent of solid names.

The solid only clips carrier extents. It never defines the requested angle.
Generated points are presentation auxiliaries; source points remain unchanged.
"""
from itertools import combinations, pairwise, product
import math

import numpy as np


def _unit(v):
    length = float(np.linalg.norm(v))
    if length < 1e-9:
        raise ValueError('Degenerate plane or dihedral hinge')
    return v/length


def _interval(point, direction, planes):
    lower,upper = -math.inf,math.inf
    for origin,normal in planes:
        offset,slope = float((point-origin)@normal),float(direction@normal)
        if abs(slope) < 1e-10:
            if offset > 1e-7:
                return None
        elif slope > 0:
            upper = min(upper,-offset/slope)
        else:
            lower = max(lower,-offset/slope)
    return (lower,upper) if upper-lower > 1e-8 else None


def _frame(request, points):
    p = [points[n] for n in request['points']]
    if request['kind'] == 'dihedral_angle':
        a,b,c,d = p
        hinge = _unit(c-b)
        first = _unit(a-b-hinge*float((a-b)@hinge))
        last = _unit(d-b-hinge*float((d-b)@hinge))
        return b,hinge,[(first,last)]
    a,b,c,d,e,f = p
    first_normal,last_normal = _unit(np.cross(b-a,c-a)),_unit(np.cross(e-d,f-d))
    hinge = _unit(np.cross(first_normal,last_normal))
    origin = np.linalg.lstsq(np.vstack((first_normal,last_normal)),
                            [float(a@first_normal),float(d@last_normal)],rcond=None)[0]
    first,last = _unit(np.cross(hinge,first_normal)),_unit(np.cross(hinge,last_normal))
    # Full planes have no selected half-plane: choose the acute sector, retaining
    # any required exterior extension. A named dihedral never enters this branch.
    choices = [(s*first,t*last) for s,t in product((-1,1),repeat=2)
               if float(s*first@(t*last)) >= -1e-7]
    return origin,hinge,choices


def normal_sections(requests, points, planes, segments):
    """Construct a bounded section at a common hinge point for every request.

    Prefer existing named points/carriers when they genuinely form a normal
    section. Otherwise clip the real hinge and rays to the solid. Acute full-plane
    angles may need an exterior ray; its visibility is evaluated separately.
    """
    generated,carriers,corners,sectors,records = {},set(),[],[],[]
    source_points = dict(points)
    span = max(float(np.linalg.norm(a-b)) for a,b in combinations(points.values(),2))
    def intern(point):
        for name,existing in {**source_points,**generated}.items():
            if np.linalg.norm(point-existing) < 1e-7*max(1,span):
                return name
        name = f'Ns{len(generated)}'
        while name in source_points or name in generated:
            name += 'x'
        generated[name] = point
        return name
    for request in requests:
        origin,hinge,choices = _frame(request,source_points)
        interval = _interval(origin,hinge,planes)
        if interval is None:
            # Full supporting planes can meet only at a vertex, or outside the
            # solid. Their intersection still exists; show a bounded extension.
            center=np.mean([source_points[n] for n in request['points']],axis=0)
            parameter=float((center-origin)@hinge)
            if np.linalg.norm(origin+parameter*hinge-center)>2*span:
                raise ValueError('Plane intersection is too far from the solid for a readable normal section')
            interval=(parameter-.25*span,parameter+.25*span)
        low,high = interval
        if not math.isfinite(low+high):
            raise ValueError('Unbounded normal-section hinge')
        candidates = [origin+(low+t*(high-low))*hinge for t in (.25,.5,.75)]
        candidates += [p for p in source_points.values()
                       if np.linalg.norm(np.cross(p-origin,hinge)) < 1e-7*max(1,span)
                       and low-1e-7 <= float((p-origin)@hinge) <= high+1e-7]
        best = None
        for center in candidates:
            # A normal section can be at a hinge endpoint (for example, two
            # already drawn face edges normal to that hinge). One nonzero
            # hinge direction suffices; requiring room on both sides invents
            # unnecessary interior sections and discards valid named carriers.
            hinge_room = max(float((center-origin)@hinge)-low,high-float((center-origin)@hinge))
            if hinge_room < .02*span:
                continue
            for first,last in choices:
                endpoints,inside,named,painted = [],0,0,0
                for direction in (first,last):
                    interval_ray = _interval(center,direction,planes)
                    reach = interval_ray[1] if interval_ray else 0
                    inside += reach > .02*span
                    extent = reach if reach > .02*span else .25*span
                    aligned = [(float((p-center)@direction),p,n) for n,p in source_points.items()
                               if np.linalg.norm(np.cross(p-center,direction)) < 1e-7*max(1,span)
                               and .03*span < float((p-center)@direction) <= extent+1e-7]
                    if aligned:
                        _,end,name = max(aligned,key=lambda row:row[0])
                        named += 1
                        painted += any(name in edge and any(np.linalg.norm(center-source_points[n]) < 1e-7 for n in edge) for edge in segments)
                    else:
                        end = center+extent*direction
                    endpoints.append(end)
                length = min(np.linalg.norm(end-center) for end in endpoints)
                existing_center = any(np.linalg.norm(center-p) < 1e-7*max(1,span) for p in source_points.values())
                score = (inside,existing_center,painted,named,round(min(length,hinge_room)/span,10))
                if length > .03*span and (best is None or score > best[0]):
                    best = score,center,endpoints,first,last
        if best is None:
            raise ValueError('No nondegenerate normal section on the actual hinge')
        _,center,endpoints,first,last = best
        angle = math.degrees(math.acos(float(np.clip(first@last,-1,1))))
        if min(angle,180-angle) < 1e-4:
            raise ValueError('Degenerate normal-section sector')
        if request.get('value') is not None and not math.isclose(angle,request['value'],abs_tol=1e-4):
            raise ValueError('Normal section disagrees with source angle')
        left,vertex,right = intern(endpoints[0]),intern(center),intern(endpoints[1])
        start,end = intern(origin+low*hinge),intern(origin+high*hinge)
        for edge in ((left,vertex),(vertex,right),(start,end)):
            # Avoid redrawing an already painted containing carrier.
            a,b = ({**source_points,**generated}[n] for n in edge)
            exists = False
            for u,v in segments | carriers:
                known = {**source_points,**generated}
                delta = known[v]-known[u]
                squared = float(delta@delta)
                if squared < 1e-14:
                    continue
                ts = [float((p-known[u])@delta)/squared for p in (a,b)]
                if all(-1e-7 <= t <= 1+1e-7 and np.linalg.norm(p-known[u]-t*delta) < 1e-7 for p,t in zip((a,b),ts)):
                    exists = True
                    break
            if not exists:
                carriers.add(tuple(sorted(edge)))
        corners.extend({'points':[vertex,ray,start,end],'mark':True} for ray in (left,right))
        right_angle = request['kind']=='perpendicular_planes' or request.get('value')==90
        if right_angle:
            corners.append({'points':[left,vertex,vertex,right],'mark':True})
        sectors.append({'points':[left,vertex,right],'value':request.get('value') if request['kind']!='perpendicular_planes' else None,
                        'label':request.get('label',''),'group':0,'required':True,'right':right_angle})
        records.append({**request,'section_points':[left,vertex,right],'hinge_points':[start,end],
                        'hinge_direction':hinge.tolist(),'world_degrees':angle,'status':'constructed',
                        'scope':'True normal section; a derived numerical angle is evidence, not a printed answer.'})
    return generated,carriers,corners,sectors,records


def visibility_parts(a, b, planes, direction):
    """Split an auxiliary carrier at convex-body and projected-silhouette events."""
    delta = b-a
    cuts = {0.,1.}
    ray_planes = []
    for origin,normal in planes:
        offset,slope,view = float((a-origin)@normal),float(delta@normal),float(direction@normal)
        if abs(slope)>1e-12:
            cuts.add(-offset/slope)
        if abs(view)>1e-12:
            ray_planes.append((-offset/view,-slope/view))
    for (a0,a1),(b0,b1) in combinations(ray_planes,2):
        if abs(a1-b1)>1e-12:
            cuts.add((b0-a0)/(a1-b1))
    cuts = sorted(t for t in cuts if 0 <= t <= 1)
    parts = []
    for low,high in pairwise(cuts):
        if high-low < 1e-8:
            continue
        ray = _interval(a+(low+high)/2*delta,direction,planes)
        hidden = bool(ray and ray[1] > max(ray[0],1e-7))
        if parts and parts[-1]['dashed']==hidden:
            parts[-1]['end'] = high
        else:
            parts.append({'start':low,'end':high,'dashed':hidden})
    return parts
