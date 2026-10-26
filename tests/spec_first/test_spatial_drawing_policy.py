"""Presentation changes cannot move geometry or assert false relationships."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))

import numpy as np
import pytest

from spec_first.spatial_construction import (
    SpatialConstruction, _projected_intersections_valid, _right_angle_options,
    _right_angle_strokes, _tick_strokes, SpatialTick, realize_points, realize_spatial,
)


def plan():
    return SpatialConstruction.model_validate({
        'points':[{'name':n,'op':'free','values':p} for n,p in
                  {'A':[0,0,0],'B':[4,0,0],'C':[4,3,0],'D':[0,3,0],'S':[1,1,3]}.items()]+
                 [{'name':'O','op':'intersect','refs':['A','C','B','D']},
                  {'name':'M','op':'lerp','refs':['S','A'],'values':[.4]}],
        'faces':[['A','B','C','D'],['S','A','B'],['S','B','C'],['S','C','D'],['S','D','A']],
        'segments':[{'a':a,'b':b} for a,b in [('A','C'),('B','D'),('S','O')]],
        'labels':[{'point':n,'text':n} for n in 'ABCDSOM']})


def test_camera_preserves_dependencies_and_all_world_coordinates():
    drawing=plan();world,free,dependent=realize_points(drawing.points)
    source,w=realize_spatial(drawing,base=drawing.faces[0],perpendiculars=[{'points':['A','B','B','C']}])
    assert all(np.array_equal(world[n],w['world_points'][n]) for n in world)
    assert all(line in source for line in dependent)
    assert len(free)==sum(p.op=='free' for p in drawing.points)
    p=np.array(w['projection']);view=np.array(w['view_direction']);z=np.array(w['camera']['frame'])[2]
    assert np.allclose(p@p.T,np.eye(2)) and np.allclose(p@view,0)
    assert (p@z)[0]==pytest.approx(0,abs=1e-12) and (p@z)[1]>0
    assert w['camera']['quality_score']!=w['camera']['clearance_score']
    assert w['relation_marks'][0]['status']=='drawn'


def test_rigid_frame_and_uniform_scale_invariance():
    original=plan();_,first=realize_spatial(original,base=original.faces[0])
    transform=np.array([[.36,-.48,.8],[.8,.60,0],[-.48,.64,.60]])
    moved=original.model_copy(deep=True)
    for point in moved.points:
        if point.op=='free':point.values=(2.3*transform@np.array(point.values)+[3,-2,1]).tolist()
    _,second=realize_spatial(moved,base=moved.faces[0])
    assert second['camera']['components']==pytest.approx(first['camera']['components'],abs=1e-9)
    def normalized(w):
        p=np.array(w['projection']);xy=np.array([p@v for v in w['world_points'].values()])
        return (xy-xy[0])*w['display_scale']
    assert np.allclose(normalized(first),normalized(second),atol=1e-9)
    assert first['segments']==second['segments']


def test_names_and_input_order_do_not_select_quality():
    drawing=plan();_,first=realize_spatial(drawing,base=drawing.faces[0])
    renamed=drawing.model_copy(deep=True);mapping={p.name:f'Q{i}' for i,p in enumerate(drawing.points)}
    for point in renamed.points:
        point.name=mapping[point.name];point.refs=[mapping[n] for n in point.refs]
    for segment in renamed.segments:segment.a=mapping[segment.a];segment.b=mapping[segment.b]
    for label in renamed.labels:label.point=mapping[label.point];label.text=mapping[label.text]
    renamed.faces=[[mapping[n] for n in reversed(f)] for f in reversed(drawing.faces)]
    renamed.labels.reverse();renamed.segments.reverse()
    _,second=realize_spatial(renamed,base=[mapping[n] for n in ['B','C','D','A']])
    assert second['camera']['components']==pytest.approx(first['camera']['components'],abs=1e-9)
    assert second['camera']['quality_score']==pytest.approx(first['camera']['quality_score'])


def test_thin_solid_is_not_reshaped_or_rejected_for_posture():
    drawing=plan()
    drawing.points[4].values=[1,1,.04]
    _,w=realize_spatial(drawing,base=drawing.faces[0])
    assert w['world_points']['S']==[1,1,.04]
    assert w['camera']['clearance_score']>0


def test_camera_search_applies_callers_clearance_gate_before_ranking():
    drawing=plan();drawing.points=drawing.points[:5]
    drawing.points[4].values=[0,0,.06];drawing.labels=drawing.labels[:5];drawing.segments=[]
    _,w=realize_spatial(drawing,base=drawing.faces[0],minimum_clearance=.008,
        perpendiculars=[{'points':['S','A','A','B']}])
    assert w['camera']['clearance_score']>=.008
    assert w['relation_marks'][0]['status']=='unreadable_size'


def test_tiny_translated_world_uses_bounded_emission_coordinates():
    import re
    drawing=plan()
    for point in drawing.points:
        if point.op=='free':point.values=(np.array(point.values)*.001+[30,30,30]).tolist()
    source,w=realize_spatial(drawing,base=drawing.faces[0])
    assert w['world_points']['A']==[30,30,30]
    triples=re.findall(r'at \(([-\d.e,]+)\);',source)
    assert len(triples)==5
    assert max(abs(float(v)) for triple in triples for v in triple.split(','))<10


def test_selected_mark_size_is_a_camera_feasibility_condition():
    drawing=plan();drawing.points=drawing.points[:5]
    drawing.points[4].values=[0,0,.35];drawing.labels=drawing.labels[:5];drawing.segments=[]
    _,w=realize_spatial(drawing,base=drawing.faces[0],minimum_clearance=.008,
        perpendiculars=[{'points':['S','A','A','B'],'mark':True}])
    assert w['relation_marks'][0]['status']=='drawn'
    assert w['relation_marks'][0]['minimum_leg_cm']>=.08


def test_base_requires_a_complete_cyclic_face_and_fallback_is_explicit():
    drawing=plan()
    for base in (['A','B','S','D'],['A','C','B','D']):
        with pytest.raises(ValueError,match='base'):realize_spatial(drawing,base=base)
    _,w=realize_spatial(drawing)
    assert w['camera']['frame_provenance']=='largest_face_geometric_fallback'


def test_true_world_right_angle_may_project_obliquely():
    points={n:np.array(p,float) for n,p in {'V':[0,0,0],'A':[1,0,0],'B':[0,0,1]}.items()}
    p=np.array([[1/np.sqrt(2),0,-1/np.sqrt(2)],[1/np.sqrt(6),-2/np.sqrt(6),1/np.sqrt(6)]])
    xy={n:p@v for n,v in points.items()}
    assert np.dot(xy['A'],xy['B'])/(np.linalg.norm(xy['A'])*np.linalg.norm(xy['B']))==pytest.approx(-.5)
    options=_right_angle_options(points,[('V','A'),('V','B')],[{'points':['V','A','V','B']}])
    strokes,marks=_right_angle_strokes(points,xy,p,options,4)
    assert len(strokes)==1 and marks[0]['status']=='drawn'
    corners=np.array(marks[0]['world_corners'])
    assert np.dot(corners[1]-corners[0],corners[2]-corners[1])==pytest.approx(0,abs=1e-12)
    assert np.allclose(corners@p.T,marks[0]['projected_corners'])


def test_screen_right_angle_does_not_authorize_false_world_mark():
    points={n:np.array(p,float) for n,p in {'V':[0,0,0],'A':[1,0,1],'B':[0,1,1]}.items()}
    with pytest.raises(ValueError,match='False spatial'):
        _right_angle_options(points,[('V','A'),('V','B')],[{'points':['V','A','V','B']}])


def test_skew_perpendiculars_cannot_receive_a_corner_at_projected_crossing():
    points={n:np.array(p,float) for n,p in {'A':[-1,0,0],'B':[1,0,0],'C':[0,-1,1],'D':[0,1,1]}.items()}
    relation={'points':['A','B','C','D']}
    records=_right_angle_options(points,[('A','B'),('C','D')],[relation])
    assert records[0]['status']=='no_drawn_incident_rays'
    with pytest.raises(ValueError,match='incident rays'):
        _right_angle_options(points,[('A','B'),('C','D')],[{**relation,'mark':True}])


def test_suppression_missing_carriers_and_interior_intersection():
    points={n:np.array(p,float) for n,p in {'A':[-1,0,0],'B':[1,0,0],'C':[0,-1,0],'D':[0,1,0],'V':[0,0,0]}.items()}
    segments=[('A','B'),('C','D')];relation={'points':['A','B','C','D']}
    assert len(_right_angle_options(points,segments,[relation])[0]['options'])==4
    assert _right_angle_options(points,segments,[{**relation,'mark':False}])[0]['status']=='suppressed'
    with pytest.raises(ValueError,match='incident rays'):
        _right_angle_options(points,segments[:1],[{**relation,'mark':True}])


def test_world_intersection_is_not_enough_when_projected_lines_coincide():
    points={n:np.array(p,float) for n,p in {'A':[-1,0,-1],'B':[1,0,1],'C':[-1,0,1],'D':[1,0,-1]}.items()}
    assert not _projected_intersections_valid(points,np.array([[1,0,0],[0,1,0]]),[['A','B','C','D']])
    assert _projected_intersections_valid(points,np.array([[1,0,0],[0,0,1]]),[['A','B','C','D']])


def test_page_span_includes_unlabelled_solid_vertices():
    drawing=plan();drawing.points=drawing.points[:5];drawing.segments=[]
    for name,last in [('M','B'),('N','D'),('R','S')]:
        drawing.points.append(type(drawing.points[0])(name=name,op='lerp',refs=['A',last],values=[.002]))
    drawing.labels=[type(drawing.labels[0])(point=n,text=n) for n in 'AMNR']
    _,w=realize_spatial(drawing,base=drawing.faces[0])
    xy=np.array(list(w['world_points'].values()))@np.array(w['projection']).T*w['display_scale']
    assert np.linalg.norm(xy[:,None,:]-xy[None,:,:],axis=2).max()==pytest.approx(8)


def test_ticks_avoid_midpoint_dots_crossings_and_corner_glyphs():
    points={n:np.array(p,float) for n,p in {'A':[0,0,0],'B':[4,0,0],'M':[2,0,0],
        'E':[1.5,-1,0],'F':[1.5,1,0]}.items()}
    xy={n:p[:2] for n,p in points.items()}
    marks=[{'status':'drawn','projected_corners':[[2.4,0],[2.4,.18],[2.58,.18]]}]
    ticks=[SpatialTick(a='A',b='B',group=1)]
    source,records=_tick_strokes(points,xy,[('A','B'),('E','F')],ticks,['A','B','M'],marks,1)
    assert records[0]['status']=='placed' and records[0]['fraction']!=.5
    x=4*records[0]['fraction']
    assert min(abs(x-2),abs(x-1.5),abs(x-2.4))>=.22
    assert f"pos={records[0]['fraction']:.12g}" in source[0]
    moved={n:p*3+np.array([7,9,1]) for n,p in points.items()}
    moved_marks=[{'status':'drawn','projected_corners':(np.array(marks[0]['projected_corners'])*3+[7,9]).tolist()}]
    _,again=_tick_strokes(moved,{n:p[:2] for n,p in moved.items()},[('A','B'),('E','F')],ticks,['A','B','M'],moved_marks,1/3)
    assert again[0]['fraction']==records[0]['fraction']
    assert again[0]['clearance_cm']==pytest.approx(records[0]['clearance_cm'])


def test_tick_on_short_carrier_reports_crowding_instead_of_readability():
    points={n:np.array(p,float) for n,p in {'A':[0,0,0],'B':[.15,0,0]}.items()}
    strokes,records=_tick_strokes(points,{n:p[:2] for n,p in points.items()},[('A','B')],
        [SpatialTick(a='A',b='B',group=1)],['A','B'],[],1)
    assert len(strokes)==1 and records[0]['status']=='crowded'


def test_equality_placement_keeps_the_validated_class_and_world():
    drawing=plan();drawing.points.append(type(drawing.points[0])(name='H',op='lerp',refs=['A','B'],values=[.5]))
    drawing.labels.append(type(drawing.labels[0])(point='H',text='H'))
    drawing.ticks=[SpatialTick(a=a,b=b,group=1) for a,b in [('A','B'),('C','D')]]
    before,_,_=realize_points(drawing.points)
    _,w=realize_spatial(drawing,base=drawing.faces[0])
    assert all(np.array_equal(before[n],w['world_points'][n]) for n in before)
    assert {tuple(m['points']) for m in w['tick_marks']}=={('A','B'),('C','D')}
    assert next(m for m in w['tick_marks'] if m['points']==['A','B'])['fraction']!=.5
    drawing.points[2].values=[3.5,3,0]
    with pytest.raises(ValueError,match='False or singleton'):
        realize_spatial(drawing,base=drawing.faces[0])
