"""Construction relations survive new coordinates; deliberate violations lose credit."""
import math
from copy import deepcopy

import pytest
from shapely.geometry import LineString
from shapely.ops import unary_union

from evaluation.tikz_geometry import compare_geometry


def transformed(points, *, scale=2.3, angle=0.71, reflection=False):
    cosine, sine = math.cos(angle), math.sin(angle)
    return {label: (17 + scale * (cosine * (-x if reflection else x) - sine * y),
                    -8 + scale * (sine * (-x if reflection else x) + cosine * y))
            for label, (x, y) in points.items()}


def scene(points, edges, circles=(), marks=()):
    strokes = []
    for names in edges:
        line = LineString([points[name] for name in names])
        strokes.append({'geometry': line, 'width': 0.01, 'dashed': False})
    for a, vertex, b in marks:
        p = points[vertex]
        endpoints = [(p[0]+.1*(points[n][0]-p[0]), p[1]+.1*(points[n][1]-p[1])) for n in (a,b)]
        corner = (endpoints[0][0]+endpoints[1][0]-p[0], endpoints[0][1]+endpoints[1][1]-p[1])
        parts = [LineString([endpoints[0],corner]), LineString([corner,endpoints[1]])]
        strokes.append({'geometry': unary_union(parts), 'components': parts, 'width': .01, 'dashed': False})
    return {'points': points, 'circles': list(circles), 'strokes': strokes}


def circle_scene(base=6, height=4.2):
    t = height**2 / (base**2 + height**2)
    points = {'A': (0,0), 'B': (0,height), 'C': (base,0), 'M': (base/2,0),
              'N': (base/2,height/2), 'H': (t*base,height*(1-t))}
    return scene(points, [('A','B'),('B','C'),('C','A'),('A','H'),('M','N')],
                 [{'center': points['C'], 'radius': base/2, 'dashed': True}],
                 [('B','A','C'),('A','H','C')])


def prism_scene(*, base=(4,0), back=(1,1), top=(0,4.18)):
    points = {'A': (0,0), 'B': base, 'C': back, "A'": top,
              "B'": (base[0]+top[0],base[1]+top[1]), "C'": (back[0]+top[0],back[1]+top[1]),
              'M': (base[0]+top[0]/2,base[1]+top[1]/2), 'N': (back[0]+top[0]/2,back[1]+top[1]/2),
              'H': (2*base[0],2*base[1]), 'K': (2*back[0],2*back[1])}
    return scene(points, [('A','K'),('C','B'),('C',"C'"),("A'",'K'),('N','M'),('K','H'),
                          ('A','H'),('A',"A'"),("A'","B'"),("B'",'B'),("A'","C'"),("C'","B'"),("A'",'H')])


@pytest.mark.parametrize('scale', [1e-6, 1, 1e6])
@pytest.mark.parametrize('reflection', [False, True])
def test_uniform_scale_rotation_and_reflection_preserve_relations(scale, reflection):
    target = circle_scene()
    output = deepcopy(target)
    output['points'] = transformed(target['points'], scale=scale, reflection=reflection)
    output['circles'] = [{**c, 'center': transformed({'O':c['center']},scale=scale,reflection=reflection)['O'],
                           'radius': c['radius']*scale} for c in target['circles']]
    checks, matches = compare_geometry(target, output)
    assert checks and all(checks) and matches == [0]
    output['points']['X'] = (1e12,1e12)
    assert compare_geometry(target, output) == (checks,matches)


def test_free_points_can_change_without_freezing_the_perpendicular_foot_ratio():
    target, output = circle_scene(), circle_scene(base=7)
    assert all(compare_geometry(target,output)[0])
    assert target['points']['H'][0]/6 != output['points']['H'][0]/7


def test_prism_dependencies_allow_new_free_points_and_changed_projection():
    target = prism_scene()
    for output in [prism_scene(base=(5,0),back=(1.3,1.6),top=(.7,3.4)), deepcopy(target)]:
        if output['points'] == target['points']:
            output['points'] = {n: (1.5*x+.4*y,.75*y) for n,(x,y) in output['points'].items()}
        assert all(compare_geometry(target,output)[0])
    output['points']['M'] = (3,1)
    assert not all(compare_geometry(target,output)[0])


@pytest.mark.parametrize('mutation', ['midpoint','foot','radius','center','missing_circle','missing_point','collapse','shear'])
def test_broken_relations_fail_with_a_fixed_target_denominator(mutation):
    target, output = circle_scene(), circle_scene()
    if mutation == 'midpoint':
        output['points']['M'] = (3.5,0)
    elif mutation == 'foot':
        output['points']['H'] = (2.4,2.52)  # Still on BC, but AH is not perpendicular.
    elif mutation == 'radius':
        output['circles'][0]['radius'] = math.dist(output['points']['C'],output['points']['N'])
    elif mutation == 'center':
        output['circles'][0]['center'] = (6.5,0)
    elif mutation == 'missing_circle':
        output['circles'] = []
    elif mutation == 'missing_point':
        output['points']['M'] = None
    elif mutation == 'collapse':
        output['points'] = {n:(0,0) for n in output['points']}
    else:
        output['points'] = {n:(x+.4*y,y) for n,(x,y) in output['points'].items()}
    checks,_ = compare_geometry(target,output)
    assert len(checks) == len(compare_geometry(target,target)[0])
    assert not all(checks)


def test_circle_order_and_style_do_not_change_mathematical_relations():
    target = circle_scene()
    target['circles'].append({'center':target['points']['A'],'radius':3,'dashed':False})
    output = deepcopy(target)
    output['circles'].reverse()
    checks,matches = compare_geometry(target,output)
    assert all(checks) and matches == [1,0]
    output['circles'][0]['dashed'] = True
    assert all(compare_geometry(target,output)[0])


def test_unanchored_reference_circle_is_not_silently_certified():
    target = {'points':{'A':(0,0),'B':(4,0),'C':(0,3)},
              'circles':[{'center':(1,1),'radius':1,'dashed':True}]}
    with pytest.raises(ValueError,match='Reference circular path has no'):
        compare_geometry(target,target)


def test_circle_limits_and_a_lone_circle():
    target = circle_scene()
    output = deepcopy(target)
    output['circles'] *= 13
    checks,matches = compare_geometry(target,output)
    assert not all(checks) and matches == [None]
    with pytest.raises(ValueError,match='12-circular-path'):
        compare_geometry(output,target)
    circle = {'points':{},'circles':[{'center':(0,0),'radius':1,'dashed':True}]}
    assert compare_geometry(circle,circle) == ([True],[0])
    circle['circles'] *= 2
    with pytest.raises(ValueError,match='distinct named points'):
        compare_geometry(circle,circle)


def test_coincident_names_cannot_hide_separation():
    target = {'points':{'A':(0,0),'B':(4,0),'M':(0,0)}}
    output = deepcopy(target)
    assert all(compare_geometry(target,output)[0])
    output['points']['M'] = (.01,0)
    assert not all(compare_geometry(target,output)[0])


def test_splitting_marker_paths_does_not_change_perpendicularity_checks():
    target, output = circle_scene(), circle_scene()
    output['points']['H'] = (2.4,2.52)
    expected = compare_geometry(target,output)
    split = deepcopy(target)
    split['strokes'] = [{**stroke,'geometry':part,'components':[part]} for stroke in target['strokes']
                        for part in stroke.get('components',[stroke['geometry']])]
    assert compare_geometry(split,output) == expected

def semicircle_scene(m=110, p=38):
    m, p = math.radians(m), math.radians(p)
    u, v = math.tan(m / 2), math.tan(p / 2)
    x = (1-u*v)/(1+u*v)
    points = {'O': (0,0), 'A': (-1,0), 'B': (1,0), 'M': (math.cos(m),math.sin(m)),
              'P': (math.cos(p),math.sin(p)), 'N': (x,2*u/(1+u*v)), 'Q': (x,2*v/(1+u*v)),
              'E': (-1,2/u), 'H': (x,0), 'T': (x,(u+v)/(1+u*v))}
    result = scene(points, [('A','B'),('A','N'),('B','N'),('B','E'),('A','P'),('A','E'),
                            ('N','H'),('O','P'),('P','T')],
                   [{'center':points['T'],'radius':math.dist(points['T'],points['N']),'dashed':True}],
                   [('E','A','B'),('Q','H','B'),('B','M','A'),('N','P','Q')])
    result['arcs'] = [{'center':(0,0),'radius':1,'start':(1,0),'end':(-1,0),'sweep':math.pi,'closed':False,'dashed':False}]
    return result


@pytest.mark.parametrize('angles', [(142,58),(125,30),(150,65),(95,20),(110,70)])
def test_semicircle_free_points_and_dependent_intersections_keep_full_credit(angles):
    target, output = semicircle_scene(), semicircle_scene(*angles)
    assert all(compare_geometry(target,output)[0])
    if angles == (142,58):
        assert target['points']['H'][0] * output['points']['H'][0] < 0  # H may cross O.


@pytest.mark.parametrize('reflection', [False,True])
def test_arcs_preserve_similarity_and_reversed_path_traversal(reflection):
    target, output = semicircle_scene(), semicircle_scene()
    output['points'] = transformed(output['points'],reflection=reflection)
    for key in ('circles','arcs'):
        for path in output[key]:
            path['center'] = transformed({'C':path['center']},reflection=reflection)['C']
            path['radius'] *= 2.3
            if key == 'arcs':
                ends = transformed({'A':path['start'],'B':path['end']},reflection=reflection)
                path['start'],path['end'] = ends['B'],ends['A']
                path['sweep'] *= 1 if reflection else -1
    assert all(compare_geometry(target,output)[0])


@pytest.mark.parametrize('mutation', ['order','off_arc','opposite_half','missing','endpoint','radius','style'])
def test_arc_requirements_distinguish_geometry_from_style(mutation):
    target = semicircle_scene()
    # Isolate the arc requirement: no unrelated line/midpoint facts can mask this test.
    target['points'] = {name:p for name,p in target['points'].items() if name in {'O','A','B','M','P'}}
    target['strokes'],target['circles'] = [],[]
    output = deepcopy(target)
    if mutation == 'order':
        output['points']['M'],output['points']['P'] = output['points']['P'],output['points']['M']
    elif mutation == 'off_arc':
        output['points']['M'] = (0,.9)
    elif mutation == 'opposite_half':
        output['arcs'][0]['sweep'] *= -1
    elif mutation == 'missing':
        output['arcs'] = []
    elif mutation == 'endpoint':
        output['arcs'][0]['end'] = (0,1)
        output['arcs'][0]['sweep'] = math.pi/2
    elif mutation == 'radius':
        output['arcs'][0]['radius'] = 1.2
    else:
        output['arcs'][0]['dashed'] = True
    checks,matches = compare_geometry(target,output)
    assert len(checks) == len(compare_geometry(target,target)[0])
    assert all(checks) == (mutation == 'style')
    from evaluation.tikz_coverage import compare_content
    content = compare_content(target,output,matches)
    assert all(content) == (mutation not in {'missing','style'})


def test_unrelated_distinct_points_do_not_dilute_a_wrong_altitude():
    target = scene({'A':(0,0),'B':(4,0),'C':(0,3),'H':(1.44,1.92)},
                   [('A','B'),('B','C'),('C','A'),('A','H')], marks=[('B','A','C'),('A','H','B')])
    output = deepcopy(target)
    output['points']['H'] = (2,1.5)
    checks,_ = compare_geometry(target,output)
    assert checks.count(False) == 1 and len(checks) == 3
    for name,p in {'X':(5.1,5.7),'Y':(-1.9,6.3),'Z':(5.5,-2.2)}.items():
        target['points'][name] = output['points'][name] = p
    assert compare_geometry(target,output)[0] == checks


def test_collinear_intermediate_points_do_not_add_duplicate_line_votes():
    target = scene({'A':(0,0),'B':(10,0),'C':(1.3,0),'D':(4.1,0),'E':(7.7,0)}, [('A','B')])
    assert compare_geometry(target,target)[0] == [True]


@pytest.mark.parametrize('span', [math.pi/2,math.pi,1.5*math.pi,2*math.pi])
def test_circular_path_measurement_accepts_arcs_and_rejects_elliptical_distortion(span):
    from evaluation.tikz_geometry import measure_circular_path
    points = [(3+2*math.cos(span*i/256),5+2*math.sin(span*i/256)) for i in range(257)]
    if span == 2*math.pi:
        points[-1] = points[0]
    path = measure_circular_path(points)
    assert path['center'] == pytest.approx([3,5])
    assert path['radius'] == pytest.approx(2)
    assert abs(path['sweep']) == pytest.approx(span)
    assert path['closed'] == (span == 2*math.pi)
    assert measure_circular_path([(1.5*x,.75*y) for x,y in points]) is None
    reverse = measure_circular_path(points[::-1])
    assert reverse['sweep'] == pytest.approx(-path['sweep'])


def test_nearly_straight_curve_is_not_certified_as_a_circle():
    from evaluation.tikz_geometry import measure_circular_path
    assert measure_circular_path([(math.cos(i/10000),math.sin(i/10000)) for i in range(100)]) is None


def test_arc_branch_is_preserved_without_freezing_its_angle():
    target = {'points':{'O':(0,0),'A':(1,0),'B':(0,1)}, 'strokes':[], 'circles':[],
              'arcs':[{'center':(0,0),'radius':1,'start':(1,0),'end':(0,1),
                       'sweep':math.pi/2,'closed':False,'dashed':False}]}
    output = deepcopy(target)
    output['arcs'][0]['sweep'] = -3*math.pi/2
    assert compare_geometry(target,output)[0] == [False]
    output['points']['B'] = (math.cos(1.2),math.sin(1.2))
    output['arcs'][0].update(end=output['points']['B'],sweep=1.2)
    assert compare_geometry(target,output)[0] == [True]


def test_unconstrained_triangle_still_requires_a_noncollapsed_configuration():
    target = {'points':{'A':(0,0),'B':(1,0),'C':(0,1)}}
    assert compare_geometry(target,target)[0] == [True]
    for points in [{'A':(0,0),'B':(1,0),'C':(2,0)}, {'A':(0,0),'B':(0,0),'C':(0,0)}]:
        assert compare_geometry(target,{'points':points})[0] == [False]



def test_a_required_interior_point_cannot_collapse_onto_a_segment_endpoint():
    target = scene({'A':(0,0),'B':(2,0),'C':(5,0)}, [('A','C')])
    output = scene({'A':(0,0),'B':(0,0),'C':(5,0)}, [('A','C')])
    assert compare_geometry(target,target)[0] == [True]
    assert compare_geometry(target,output)[0] == [False]
