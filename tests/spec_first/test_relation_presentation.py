"""Source-bound cues, not inferred answers or screen-space geometry."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path[:0] = [str(Path(__file__).resolve().parents[2]/'src')]

from spec_first.relation_presentation import (
    bind_sectors, equality_groups, metric_and_parallel_strokes,
    sector_strokes, selected_relations,
)
from spec_first.spec import GeometrySpec, admit_instruction, realize_spec


def specification(names, relations, draw=(), dimension=2, solid=None):
    return GeometrySpec.model_validate({'dimension':dimension,'points':[{'name':n} for n in names.split()],
        'relations':[{'source_quote':'fixture',**r} for r in relations], 'draw':draw,'solid':solid})


def relation(kind, points, **extra):
    return {'kind':kind,'points':points.split(),**extra}


def test_admission_does_not_fabricate_suppression_or_override_it_through_reversal():
    s = specification('A B C',[relation('noncollinear','A B C')])
    s.relations[0].source_quote = 'AB = AC = 5 cm'
    admitted,audit = admit_instruction(s,'AB = AC = 5 cm')
    assert len(audit['added_relations']) == 2
    assert all(r.mark is None for r in admitted.relations)
    r = admitted.relations[1]
    r.points.reverse();r.mark=False
    twice,_ = admit_instruction(admitted,'AB = AC = 5 cm')
    assert len(twice.relations)==len(admitted.relations)
    assert twice.relations[1].mark is False


def test_equalities_merge_from_source_measures_and_ratio_one_only():
    s=specification('A B C D E F G H',[
        relation('length','A B',expression='a'), relation('length','C D',expression='a'),
        relation('length_ratio','C D E F',values=[1]), relation('length','G H',expression='2a')])
    ids={p.name:p.name for p in s.points}
    chosen=selected_relations(s,ids)
    assert chosen['equal_classes']==[[('A','B'),('C','D'),('E','F')]]
    # Deliberate geometry coincidences cannot insert GH into the supplied class.
    p={n:np.array([i//2,i%2],float) for i,n in enumerate('ABCDEFGH')}
    assert equality_groups(chosen,p,[('A','B'),('C','D'),('E','F'),('G','H')])==chosen['equal_classes']
    p['F']+=np.array([0,.5])
    with pytest.raises(ValueError,match='False equality'):
        equality_groups(chosen,p,[('A','B'),('C','D'),('E','F')])


def test_one_source_value_and_distinct_ticks_do_not_claim_groups_are_unequal():
    s=specification('A B C D',[relation('length','A B',values=[4],unit='cm'),
        relation('length','C D',values=[40],unit='mm')])
    ids={p.name:p.name for p in s.points};chosen=selected_relations(s,ids)
    p={n:np.array(v) for n,v in {'A':[0.,0.],'B':[4.,0.],'C':[0.,2.],'D':[4.,2.]}.items()}
    edges=[('A','B'),('C','D')];groups=equality_groups(chosen,p,edges)
    strokes,marks=metric_and_parallel_strokes(s,ids,chosen,groups,p,edges,np.eye(2),1)
    assert len(strokes)==1 and marks[0]['text']==r'4\,\mathrm{cm}'
    s.relations[0].mark=False
    assert not selected_relations(s,ids)['equal_classes']


def test_overlapping_angle_classes_merge_and_unknown_sector_gets_no_answer():
    s=specification('A B C D E F G H I',[
        relation('equal_angle','A B C D E F'),relation('equal_angle','D E F G H I')],
        [{'kind':'angle','points':['A','B','C'],'label':'x'}])
    choice=selected_relations(s,{p.name:p.name for p in s.points})
    assert len(choice['sectors'])==3 and {r['group'] for r in choice['sectors']}=={1}
    assert all(r['value'] is None for r in choice['sectors'])


def test_numeric_triangle_angles_do_not_print_unknown_solution():
    s=specification('M N P',[relation('angle','N M P',values=[90]),
        relation('angle','M N P',values=[60])],[{'kind':'polygon','points':['M','N','P']}])
    source,e=realize_spec(s,'fixture',candidates=2)
    assert all(r['pass'] for r in e['checks'])
    assert 'right angle' in source and r'60^{\circ}' in source
    assert r'30^{\circ}' not in source
    assert len(e['witness']['sector_marks'])==1


def test_isosceles_midpoint_does_not_announce_derived_right_angles():
    s=specification('A B C D',[relation('equal_length','A B A C'),
        relation('midpoint','D B C',mark=True)],
        [{'kind':'polygon','points':['A','B','C']},{'kind':'segment','points':['A','D']}])
    source,e=realize_spec(s,'fixture',candidates=2)
    assert len(e['witness']['equal_classes'])==2
    assert not e['witness']['relation_marks'] and not e['witness']['sector_marks']
    assert 'right angle' not in source


def test_square_premise_basis_does_not_complete_all_its_properties():
    s=specification('A B C D',[
        relation('perpendicular','D A A B'),relation('perpendicular','B C C D'),
        relation('perpendicular','C D D A'),relation('equal_length','A D D C')],
        [{'kind':'polygon','points':['A','B','C','D']}])
    _,e=realize_spec(s,'fixture',candidates=2)
    assert len(e['witness']['relation_marks'])==3
    assert len(e['witness']['equal_classes'][0])==2


@pytest.mark.parametrize('dimension',[2,3])
def test_sector_samples_bind_true_angle_under_common_projection(dimension):
    p={'V':np.zeros(dimension),'A':np.array([3.,0.,0.][:dimension]),
       'B':np.array([-1.5,3*np.sqrt(3)/2,0.][:dimension])}
    projection=np.eye(2) if dimension==2 else np.array([[.8,.6,0],[-.3,.4,np.sqrt(.75)]])
    req={'points':['A','V','B'],'value':120.,'required':True,'group':0,'label':''}
    records=bind_sectors([req],p,[('A','V'),('V','B')])
    source,marks=sector_strokes(records,p,projection,1)
    curve=marks[0]['curves'][0];world=np.array(curve['world_points'])
    assert np.allclose(world@projection.T,curve['projected_points'])
    assert np.ptp(np.linalg.norm(world-p['V'],axis=1))<1e-10
    first,last=world[0]-p['V'],world[-1]-p['V']
    assert first@last/(np.linalg.norm(first)*np.linalg.norm(last))==pytest.approx(-.5)
    assert r'120^{\circ}' in source[-1]
    if dimension==3:
        screen=np.array(curve['projected_points'])
        cosine=screen[0]@screen[-1]/(np.linalg.norm(screen[0])*np.linalg.norm(screen[-1]))
        assert not np.isclose(cosine,-.5)


def test_false_angle_wrong_rays_missing_carrier_and_edge_on_projection_fail():
    p={n:np.array(v,float) for n,v in {'V':[0,0,0],'A':[2,0,0],'B':[1,1,0]}.items()}
    req={'points':['A','V','B'],'value':60.,'required':True,'group':0,'label':''}
    with pytest.raises(ValueError,match='False numeric'):
        bind_sectors([req],p,[('A','V'),('B','V')])
    req['value']=45.
    with pytest.raises(ValueError,match='no drawn carrier'):
        bind_sectors([req],p,[('A','V')])
    bound=bind_sectors([req],p,[('A','V'),('B','V')])
    with pytest.raises(ValueError,match='too small'):
        sector_strokes(bound,p,np.array([[1,0,0],[0,0,1]]),1)


def test_selected_parallel_class_honors_direction_and_checks_truth():
    s=specification('A B C D',[relation('parallel','A B C D',mark=True)])
    ids={p.name:p.name for p in s.points};choice=selected_relations(s,ids)
    p={n:np.array(v,float) for n,v in {'A':[0,0],'B':[3,0],'C':[2,1],'D':[0,1]}.items()}
    strokes,marks=metric_and_parallel_strokes(s,ids,choice,[],p,[('A','B'),('C','D')],np.eye(2),1)
    assert len(strokes)==2 and all(r['kind']=='parallel' for r in marks)
    p['D'][1]=2
    with pytest.raises(ValueError,match='False parallel'):
        metric_and_parallel_strokes(s,ids,choice,[],p,[('A','B'),('C','D')],np.eye(2),1)


def test_ratio_admission_cannot_override_reversed_suppression():
    s=specification('A B C D',[relation('length_ratio','B A D C',values=[1],mark=False)])
    s.relations[0].source_quote='AB=CD.'
    admitted,_=admit_instruction(s,'AB=CD.')
    assert len(admitted.relations)==1
    assert not selected_relations(admitted,{p.name:p.name for p in s.points})['equal_classes']


def test_duplicate_angle_preserves_required_and_explicit_suppression():
    s=specification('A V B',[relation('angle','A V B',values=[60],mark=True),
        relation('angle','B V A',values=[60])])
    ids={p.name:p.name for p in s.points}
    assert selected_relations(s,ids)['sectors'][0]['required']
    s.relations[0].mark=False
    assert selected_relations(s,ids)['sectors']==[]


def test_optional_incomplete_equality_keeps_required_numeric_sector():
    s=specification('A V B C W D',[relation('angle','A V B',values=[60],mark=True),
        relation('equal_angle','A V B C W D')])
    choice=selected_relations(s,{p.name:p.name for p in s.points})
    p={n:np.array(v,float) for n,v in {'V':[0,0],'A':[2,0],'B':[1,np.sqrt(3)],
        'W':[4,0],'C':[6,0],'D':[5,np.sqrt(3)]}.items()}
    bound=bind_sectors(choice['sectors'],p,[('A','V'),('B','V')])
    _,marks=sector_strokes(bound,p,np.eye(2),1)
    visible=[m for m in marks if m['status']=='drawn']
    assert len(visible)==1 and visible[0]['text']==r'60^{\circ}' and visible[0]['group']==0


def test_explicit_angle_equality_cannot_disappear_in_edge_on_projection():
    s=specification('A V B C W D',[relation('equal_angle','A V B C W D',mark=True)],dimension=2)
    choice=selected_relations(s,{p.name:p.name for p in s.points})
    p={n:np.array(v,float) for n,v in {'V':[0,0,0],'A':[2,0,0],'B':[1,1,0],
        'W':[4,0,0],'C':[6,0,0],'D':[5,1,0]}.items()}
    bound=bind_sectors(choice['sectors'],p,[('A','V'),('B','V'),('C','W'),('D','W')])
    with pytest.raises(ValueError,match='too small'):
        sector_strokes(bound,p,np.array([[1,0,0],[0,0,1]]),1)


def test_optional_angle_equality_drops_as_class_if_one_world_plane_is_edge_on():
    s=specification('A V B C W D',[relation('equal_angle','A V B C W D')])
    choice=selected_relations(s,{p.name:p.name for p in s.points})
    p={n:np.array(v,float) for n,v in {'V':[0,0,0],'A':[2,0,0],'B':[1,1,0],
        'W':[4,0,0],'C':[6,0,0],'D':[5,0,1]}.items()}
    bound=bind_sectors(choice['sectors'],p,[('A','V'),('B','V'),('C','W'),('D','W')])
    source,marks=sector_strokes(bound,p,np.array([[1,0,0],[0,1,0]]),1)
    assert not source and all(m['status']=='unreadable_equality_class' for m in marks)
