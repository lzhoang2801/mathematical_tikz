"""Independent affine and line-visibility checks for three real spatial cases.

Canonical XYZ gives an affine existence witness, never metric reconstruction.
Fit four anchors only, then test every other observed point. Neither generation
plans nor emitter-selected cameras are inputs to these checks.
"""
from __future__ import annotations

from itertools import combinations
import math

import numpy as np
from shapely.geometry import LineString
from shapely.ops import unary_union

from evaluation.requirements import Requirements
from evaluation.tikz_coverage import connections
from evaluation.tikz_marks import observe_marks
from evaluation.tikz_readability import inspect_readability

CASES = {
    'tetrahedron': '571c8b35-b2f8-5053-807a-5c8e1007f559',
    'pyramid': '5a39fb6d-a416-5713-a16f-c937952828db',
    'parallelepiped': '473b7bef-1a21-5627-9470-92259bb9199e',
}
SCOPE = 'Three curated grade-11/12 Generate cases with affine spatial constructions; two repetitions; no Edit/Reconstruct, training or promotion.'
SELECTION = 'Assistant-selected tetrahedron sections, pyramid midpoint section and parallelepiped centroid. Unfilled closed convex solids; visibility from either consistent parallel view. Not a random generalization sample.'


def canonical(case):
    p = {'A': np.array([0.,0,0]), 'B': np.array([1.,0,0]), 'C': np.array([0.,1,0]), 'S': np.array([0.,0,1])}
    extra, optional = [], []
    if case == 'tetrahedron':
        anchors = ['A','B','C','S']
        faces = [['A','B','C'], ['S','A','B'], ['S','B','C'], ['S','C','A']]
        for index, fraction in ((1, 2/3), (2, 1/3)):
            for name in 'ABC':
                p[name+str(index)] = p['S'] + fraction*(p[name]-p['S'])
            extra.extend([(f'A{index}',f'B{index}'), (f'B{index}',f'C{index}'), (f'C{index}',f'A{index}')])
    elif case == 'pyramid':
        p['D'], p['C'] = np.array([0.,1,0]), np.array([1.,1,0])
        anchors = ['A','B','D','S']
        faces = [['A','B','C','D'], ['S','A','B'], ['S','B','C'], ['S','C','D'], ['S','D','A']]
        p['O'] = (p['A']+p['C'])/2
        for name, base in zip('MNPQ','ABCD'):
            p[name] = (p['S']+p[base])/2
        p['I'] = (p['M']+p['P'])/2
        extra = [('M','N'),('N','P'),('P','Q'),('Q','M'),('M','P'),('N','Q'),('S','O')]
        optional = [('A','C'),('B','D')]
    elif case == 'parallelepiped':
        p = {'A': np.array([0.,0,0]), 'B': np.array([1.,0,0]), 'C': np.array([1.,1,0]), 'D': np.array([0.,1,0])}
        p.update({name+"'": value+np.array([0.,0,1]) for name,value in list(p.items())})
        anchors = ['A','B','D',"A'"]
        faces = [['A','B','C','D'], ["A'","B'","C'","D'"], ['A','B',"B'","A'"], ['B','C',"C'","B'"], ['C','D',"D'","C'"], ['D','A',"A'","D'"]]
        p['O'] = (p['A']+p['C'])/2
        p['G'] = (p['B']+p['D']+p["A'"])/3
        extra = [('B','D'),('B',"A'"),('D',"A'"),("A'",'O')]
        optional = [('A','C')]
    else:
        raise ValueError(case)
    edges = sorted({tuple(sorted((face[i],face[(i+1)%len(face)]))) for face in faces for i in range(len(face))})
    return p, anchors, faces, edges+extra, optional


def requirements(case):
    p, anchors, _, _, _ = canonical(case)
    return Requirements(points=list(p), relations=[{'id':'affine_independent_anchors', 'kind':'noncoplanar', 'points':anchors}])


def fit_projection(case, observed):
    world, anchors, _, _, _ = canonical(case)
    if any(observed.get(name) is None for name in world):
        return {'status':'unverified', 'reason':'Missing or unresolved named points'}
    origin = np.asarray(observed[anchors[0]])
    matrix = np.column_stack([np.asarray(observed[name])-origin for name in anchors[1:]])
    # Each canonical anchor set is the origin followed by the three unit axes.
    if not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix, tol=1e-6) != 2:
        return {'status':'fail', 'reason':'Collapsed affine projection'}
    predicted = {name: matrix @ value+origin for name,value in world.items()}
    errors = {name: float(np.linalg.norm(np.asarray(observed[name])-predicted[name])) for name in world if name not in anchors}
    # TeX/PDF quantization is far below this fixed 0.15 bp bound; no refit using auxiliaries.
    status = 'pass' if max(errors.values(), default=0) <= 0.15 else 'fail'
    direction = np.linalg.svd(matrix, full_matrices=True)[2][-1]
    return {'status':status, 'held_out_errors_bp':errors, 'matrix':matrix.tolist(), 'translation':origin.tolist(), 'direction':direction.tolist()}


def expected_styles(case, direction):
    """Evaluate face planes from frozen source topology, not emitter witnesses."""
    world, _, faces, edges, optional = canonical(case)
    vertices = {name for face in faces for name in face}
    interior = np.mean([world[name] for name in vertices], axis=0)
    planes = []
    for face in faces:
        a,b,c = (world[name] for name in face[:3])
        normal = np.cross(b-a,c-a)
        normal /= np.linalg.norm(normal)
        if normal @ (a-interior) < 0:
            normal = -normal
        planes.append((a,normal))
    styles = {}
    for a,b in edges+optional:
        midpoint = (world[a]+world[b])/2
        front = [abs(float((midpoint-origin) @ normal)) < 1e-8 and normal @ direction > 1e-8 for origin,normal in planes]
        styles[a,b] = not any(front)
    return styles, min(abs(float(normal @ direction)) for _,normal in planes)


def style_support(scene, a, b, dashed):
    """Measure collinear vector support; unrelated crossings cannot cause failure."""
    line = LineString([a,b])
    if line.length < 1e-6:
        return 0.0
    u = (np.asarray(b)-a)/line.length
    pieces = []
    tolerance = max(0.08, line.length*0.001)
    for stroke in scene['strokes']:
        if stroke['dashed'] != dashed:
            continue
        for part in stroke.get('components', [stroke['geometry']]):
            if part.geom_type != 'LineString' or len(part.coords) != 2 or part.length < 1e-6:
                continue
            first,last = map(np.asarray, part.coords)
            v = (last-first)/part.length
            perpendicular = np.array([-u[1],u[0]])
            if abs(float(u @ v)) > 0.99999 and max(abs(float((p-a) @ perpendicular)) for p in (first,last)) <= tolerance:
                pieces.append(part)
    return float(line.intersection(unary_union(pieces).buffer(tolerance)).length/line.length)




def allowed_tick_parts(case, scene):
    """Exempt only vector marks bound to source-justified equality classes."""
    groups = []
    if case == 'tetrahedron':
        groups = [[('A','A1'),('A1','A2'),('A2','S')]]
    elif case == 'pyramid':
        groups = [[('S',mid),(mid,base)] for mid,base in zip('MNPQ','ABCD')]
    elif case == 'parallelepiped':
        groups = [[('A','O'),('O','C')],[('B','O'),('O','D')]]
    permitted = [{tuple(sorted(edge)) for edge in group} for group in groups]
    edges = connections(scene)
    marks = observe_marks(scene,edges)
    certified = set().union(*(group for group in marks['equal_segments'] if group in permitted))
    if not certified:
        return []
    parts = []
    font = max((label.get('size',10) for label in scene['text']), default=10)
    for stroke in scene['strokes']:
        if stroke['dashed']:
            continue
        for part in stroke.get('components',[stroke['geometry']]):
            if part.length > 2*font:
                continue
            single = {**scene,'text':[],'strokes':[{**stroke,'geometry':part,'components':[part]}]}
            bound = observe_marks(single,edges)['equal_segments']
            if any(group and group <= certified for group in bound):
                parts.append(part)
    return parts


def check_output(case, scene):
    world, _, _, edges, optional = canonical(case)
    points = scene['points']
    fit = fit_projection(case, points)
    checks = [{'id':'affine_projection_binding', **fit}, {'id':'point_names','status':'pass' if set(points) == set(world) else 'fail'},
              {'id':'observations','status':'pass' if not scene['unresolved'] and not scene['unsupported'] else 'unverified'}]
    visibility = []
    if fit['status'] == 'pass':
        for sign in (1,-1):
            styles, grazing = expected_styles(case, sign*np.asarray(fit['direction']))
            rows = []
            for a,b in edges+optional:
                solid = style_support(scene,points[a],points[b],False)
                dashed = style_support(scene,points[a],points[b],True)
                if (a,b) in optional and max(solid,dashed) < 0.1:
                    continue
                expected = styles[a,b]
                correct, wrong = (dashed,solid) if expected else (solid,dashed)
                rows.append({'id':'style:'+a+'-'+b,'status':'pass' if correct >= 0.985 and wrong < 0.02 else 'fail', 'expected_dashed':expected,'correct_coverage':correct,'opposite_coverage':wrong})
            visibility.append({'sign':sign, 'grazing':grazing, 'checks':rows, 'failed':sum(row['status'] != 'pass' for row in rows)})
        best = min(visibility,key=lambda candidate:candidate['failed'])
        checks.extend(best['checks'])
        checks.append({'id':'visibility_consistency','status':'pass' if best['failed']==0 else 'fail'})
        allowed = unary_union([*[LineString([points[a],points[b]]) for a,b in edges+optional], *allowed_tick_parts(case,scene)]).buffer(0.20)
        residual = sum(part.difference(allowed).length for stroke in scene['strokes'] for part in stroke.get('components',[stroke['geometry']]))
        checks.append({'id':'unrequested_strokes','status':'pass' if residual <= 0.4 else 'fail','residual_length_bp':float(residual)})
        checks.append({'id':'non_grazing_view','status':'pass' if best['grazing'] > 0.01 else 'unverified'})
        projected = list(points.values())
        separation = min(math.dist(a,b) for a,b in combinations(projected,2))
        checks.append({'id':'distinct_projected_points','status':'pass' if separation > 1.0 else 'fail','minimum_bp':separation})
        if case == 'tetrahedron':
            marks = observe_marks(scene,connections(scene))
            expected = {tuple(sorted(edge)) for edge in [('A','A1'),('A1','A2'),('A2','S')]}
            checks.append({'id':'trisection_ticks','status':'pass' if expected in marks['equal_segments'] else 'fail'})
    else:
        checks.append({'id':'visibility','status':'unverified','reason':'Cannot bind source construction to observed projection'})
    readability = inspect_readability(scene)
    checks.extend({'id':'label:'+str(i),'status':row['status'],'details':row} for i,row in enumerate(readability['labels']))
    return {'status':'pass' if all(row['status']=='pass' for row in checks) else 'held', 'mathematics_pass':fit['status']=='pass',
            'visibility_pass':bool(visibility and best['failed']==0 and best['grazing']>0.01 and separation>1.0 and residual<=0.4), 'checks':checks,
            'visibility_hypotheses':visibility, 'failed_checks':[row['id'] for row in checks if row['status']!='pass'],
            'scope':'Affine existence and original-PDF line style; metric 3D statements and arbitrary extra annotations are not certified.'}


def calibration_variants(case, target):
    mutations = {
        'tetrahedron': ('$(S)!2/3!(A)$', '$(S)!0.55!(A)$', r'\draw[dashed] (A) -- (C);', r'\draw (A) -- (C);', r'\draw (A1) -- (B1) -- (C1);'),
        'pyramid': ('$(S)!0.5!(A)$', '$(S)!0.3!(A)$', r'\draw[dashed] (A) -- (D) (A) -- (B) (S) -- (A);', r'\draw (A) -- (D) (A) -- (B) (S) -- (A);', r'\draw (N) -- (P) -- (Q);'),
    }
    if case == 'parallelepiped':
        old,new = "$(A')!{2/3}!(O)$", "$(A')!{1/2}!(O)$"
        dashed,solid = "\\draw[dashed] (A) -- (A');", "\\draw (A) -- (A');"
        missing = "\\draw[dashed] (A') -- (O);"
    else:
        old,new,dashed,solid,missing = mutations[case]
    if any(target.count(text) != 1 for text in (old,dashed,missing)):
        raise ValueError('Stale spatial calibration mutation: '+case)
    variants = {'target':(target,[]),
            'valid_similarity':(target.replace('[thick,','[rotate=17,scale=1.15,thick,',1),[]),
            'extra_dash':(target.replace(r'\end{tikzpicture}',r'\draw[dashed] (10,0)--(11,1);'+'\n'+r'\end{tikzpicture}'),['unrequested_strokes']),
            'wrong_geometry':(target.replace(old,new),['affine_projection_binding']),
            'wrong_visibility':(target.replace(dashed,solid),['visibility_consistency']),
            'missing_segment':(target.replace(missing,''),['style:'+({'tetrahedron':'A1-B1','pyramid':'N-P','parallelepiped':"A'-O"}[case])])}

    if case == 'tetrahedron':
        front = target.replace('(2,4.5)', '(2.5,2)').replace('(0,0.5)', '(0,0)').replace('(1.8,-1)', '(8,0)').replace('(5,0.5)', '(1,7)').replace('dashed', 'solid')
        variants['valid_all_visible'] = (front, ['label:0','label:6','label:7'])
        clear_front = front.replace('above:$S$', 'above right:$S$').replace('left:$B_1$', 'above right:$B_1$').replace('left:$B_2$', 'above right:$B_2$')
        variants['valid_all_visible_clear'] = (clear_front, [])
        old_ticks = r'\draw (\U) -- node[midway,sloped] {$|$} (\V);'
        new_ticks = r'{\path ($(\U)!0.5!(\V)$) coordinate (Tick); \draw ($(Tick)!2.5pt!90:(\V)$)--($(Tick)!2.5pt!-90:(\V)$);}'
        if target.count(old_ticks) != 1:
            raise ValueError('Stale vector-tick calibration')
        variants['valid_vector_ticks'] = (target.replace(old_ticks,new_ticks), [])
    return variants
