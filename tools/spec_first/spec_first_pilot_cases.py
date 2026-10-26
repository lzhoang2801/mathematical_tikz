"""Independent primary checks for the Spec First comparison; no worker imports."""
from __future__ import annotations

import numpy as np

from evaluation.tikz_coverage import connections
from evaluation.tikz_marks import observe_marks
from tools.spec_first import construction_pilot_cases, spatial_pilot_cases


def _filled_ray_arrow(scene, origin, end):
    """Recognize a filled triangular/Stealth head attached to this ray's shaft."""
    axis = end-origin
    axis = axis/np.linalg.norm(axis)
    normal = np.asarray([-axis[1],axis[0]])
    for drawing in scene.get('paths', []):
        for subpath in drawing['subpaths']:
            items = subpath[1:]
            if drawing['operation'] not in {'fill', 'fillstroke'} or drawing.get('fill_opacity',1) <= 0 or len(items) not in (2,3,4) or any(i[0]!='l' for i in items):
                continue
            if any(np.linalg.norm(np.asarray(items[i][2])-items[i+1][1])>.01 for i in range(len(items)-1)):
                continue
            # Filled native subpaths implicitly close at their first vertex.
            vertices = [i[1] for i in items]
            if np.linalg.norm(np.asarray(items[-1][2])-vertices[0])>.01:
                vertices.append(items[-1][2])
            if len(vertices) not in (3,4):
                continue
            vertices = np.asarray(vertices)
            x,y = (vertices-origin)@axis,(vertices-origin)@normal
            tip = int(np.argmax(x))
            length = float(max(x)-min(x))
            if not (1 < length < 20 and abs(y[tip])<.1 and x[tip]>float((end-origin)@axis)):
                continue
            side = [i for i in range(len(vertices)) if i!=tip and abs(y[i])>.1]
            if len(side)!=2 or abs(y[side[0]]+y[side[1]])>.05 or abs(x[side[0]]-x[side[1]])>.05:
                continue
            if not (0.15*length < abs(y[side[0]]) < length):
                continue
            if len(vertices)==4:
                notch = next((i for i in range(4) if i!=tip and i not in side),None)
                if notch is None or abs(y[notch])>.1 or not min(x)<x[notch]<max(x):
                    continue
            for stroke in scene['strokes']:
                if stroke['dashed']:
                    continue
                for component in stroke['components']:
                    ends = np.asarray(component.coords)
                    along,across = (ends-origin)@axis,(ends-origin)@normal
                    if max(abs(across))<.1 and max(along)-min(along)>3*length and min(along)<.5 and min(x)-.5 <= max(along) <= max(x)+.5:
                        return True
    return False


def check_output(case, scene, *, suite):
    if suite == 'spatial':
        result = spatial_pilot_cases.check_output(case,scene)
    else:
        result = construction_pilot_cases.check_output(case,scene)
        # A right corner on either side of a supporting line denotes the same
        # perpendicularity. Preserve the old sector check as diagnostic evidence.
        marks = observe_marks(scene,connections(scene))
        points = scene['points']
        for check in result['checks']:
            if not check['id'].startswith('right_angle:') or check['status'] == 'pass':
                continue
            a,v,b = check['id'].split(':',1)[1].split('-')
            if any(points.get(n) is None for n in (a,v,b)):
                continue
            def same_support(x,y,v=v):
                u,w = np.asarray(points[x])-points[v],np.asarray(points[y])-points[v]
                denominator = np.linalg.norm(u)*np.linalg.norm(w)
                return denominator>0 and abs(float(u@w))/denominator>.9999
            matched = any(vertex==v and any(same_support(a,x) and same_support(b,y) for x,y in ((u,w),(w,u)))
                          for u,vertex,w in marks['right_angles'])
            if matched and check.get('residual',1) <= .006:
                check.update(original_status=check['status'],status='pass',equivalent_support_sector=True)
        result['checks'].append({'id':'planar_solid_roles','status':'fail' if any(s['dashed'] for s in scene['strokes']) else 'pass'})
        if case == 'tangency':
            for foot in ('H','K'):
                valid = False
                if all(points.get(n) is not None for n in ('O',foot)):
                    origin,end = np.asarray(points['O']),np.asarray(points[foot])
                    vector=end-origin
                    length=np.linalg.norm(vector)
                    if length>0:
                        valid = any(float((np.asarray(a['tip'])-end)@vector)>0
                                    and abs(float(vector[0]*(np.asarray(a['tip'])-origin)[1]-vector[1]*(np.asarray(a['tip'])-origin)[0]))/length<.4
                                    and float(vector@a['direction'])/length>.99
                                    for a in scene.get('arrows',[]) if not a['dashed'])
                        valid = valid or _filled_ray_arrow(scene,origin,end)
                result['checks'].append({'id':'ray_arrow:'+foot,'status':'pass' if valid else 'unverified'})
    result['failed_checks'] = [r['id'] for r in result['checks'] if r['status'] != 'pass']
    result['status'] = 'pass' if not result['failed_checks'] else 'held'
    primary = [r for r in result['checks'] if not r['id'].startswith('label:')]
    result['geometry_content_pass'] = all(r['status']=='pass' for r in primary)
    result['geometry_content_failures'] = [r['id'] for r in primary if r['status']!='pass']
    result['primary_scope'] = 'Source mathematics, drawing coverage/roles and point/view separation. Glyph placement is reported separately; no repair is presumed.'
    return result
