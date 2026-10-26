"""Plane truth, selected half-planes and emitted normal sections are separate."""
from pathlib import Path
import math
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from spec_first.instruction_constraints import scan_instruction
from spec_first.plane_sections import normal_sections, visibility_parts
from spec_first.planar_solver import constraint_residuals
from spec_first.relation_presentation import selected_relations
from spec_first.spatial_construction import SpatialConstruction, SpatialPoint, realize_points, realize_spatial, validate_solid
from spec_first.spec import GeometrySpec, Relation, SpecError, admit_instruction, check_constraints, realize_spec


def specimen(kind='dihedral_angle',value=120):
    points = {'A':np.array([2.,0,1]),'B':np.zeros(3),'C':np.array([0.,0,3]),'D':np.array([-.5,math.sqrt(3)/2,2])}
    names = ['A','B','C','D'] if kind=='dihedral_angle' else ['A','B','C','B','C','D']
    relation={'kind':kind,'points':names,'source_quote':'fixture','mark':False}
    if value is not None:relation['values']=[value]
    spec=GeometrySpec.model_validate({'dimension':3,'points':[{'name':n} for n in points],
        'solid':{'kind':'tetrahedron','vertices':list(points),'source_quote':'fixture'},'relations':[relation]})
    return spec,points


def test_selected_dihedral_is_not_acute_plane_angle_or_arbitrary_edge_angle():
    spec,p=specimen()
    assert all(r['pass'] for r in check_constraints(spec,p))
    assert np.max(np.abs(constraint_residuals(spec,p))) < 1e-10
    spec.relations[0].values=[60]
    assert not check_constraints(spec,p)[0]['pass']
    assert np.max(np.abs(constraint_residuals(spec,p))) > .9
    planes,p=specimen('plane_angle',60)
    assert all(r['pass'] for r in check_constraints(planes,p))
    # Reflecting the selected half-plane keeps both supporting planes unchanged.
    p['D'][:2]*=-1
    assert all(r['pass'] for r in check_constraints(planes,p))
    assert all(r['pass'] for r in check_constraints(spec,p))


def test_independent_authoring_evaluator_distinguishes_supplementary_openings():
    from evaluation.requirements import Relation as Requirement, relation_residual
    _,p=specimen()
    dihedral=Requirement(id='given',kind='dihedral_angle',points=list('ABCD'),value=120)
    plane=Requirement(id='given',kind='plane_angle',points=list('ABCBCD'),value=60)
    assert relation_residual(dihedral,p)<1e-10
    assert relation_residual(plane,p)<1e-10
    p['D'][:2]*=-1
    assert relation_residual(dihedral,p)==pytest.approx(1/3)
    assert relation_residual(plane,p)<1e-10


@pytest.mark.parametrize('kind,value',[('dihedral_angle',120),('plane_angle',60)])
def test_section_uses_common_hinge_and_true_rays_in_a_rotated_frame(kind,value):
    spec,p=specimen(kind,value)
    rotation,_=np.linalg.qr(np.array([[1.,2,3],[2,-1,1],[3,1,-2]]))
    p={n:rotation@q+np.array([3.,-2,1]) for n,q in p.items()}
    faces=[['B','C','D'],['A','B','C'],['A','C','D'],['A','D','B']]
    body,edges=validate_solid(p,faces)
    request={'kind':kind,'points':spec.relations[0].points,'value':value}
    added,carriers,corners,sectors,records=normal_sections([request],p,body,set(edges))
    world={**p,**added};record=records[0]
    a,v,b=(world[n] for n in record['section_points'])
    hinge=p['C']-p['B'];u,w=a-v,b-v
    assert abs(u@hinge)<1e-7 and abs(w@hinge)<1e-7
    assert np.linalg.norm(np.cross(v-p['B'],hinge))<1e-7
    assert math.degrees(math.acos(np.clip(u@w/np.linalg.norm(u)/np.linalg.norm(w),-1,1)))==pytest.approx(value)
    first=p['A']-p['B']-hinge*((p['A']-p['B'])@hinge)/(hinge@hinge)
    last=p['D']-p['B']-hinge*((p['D']-p['B'])@hinge)/(hinge@hinge)
    if kind=='dihedral_angle':assert u@first>0 and w@last>0
    assert len(corners)==2 and carriers and sectors[0]['value']==value


def test_plane_perpendicularity_uses_whole_planes_and_rejects_degenerate_triplets():
    spec,p=specimen('perpendicular_planes',None)
    p['D']=np.array([0.,2,2])
    assert all(r['pass'] for r in check_constraints(spec,p))
    assert np.max(np.abs(constraint_residuals(spec,p)))<1e-10
    p['A']=np.array([0.,0,1])
    assert not check_constraints(spec,p)[0]['pass']
    with pytest.raises(ValueError,match='Degenerate'):
        normal_sections([{'kind':'perpendicular_planes','points':spec.relations[0].points,'value':90}],p,[],set())


def test_unimplemented_checker_kind_never_silently_passes():
    spec,p=specimen()
    spec.relations[0]=Relation.model_construct(kind='not_implemented',points=['A','B'])
    with pytest.raises(ValueError,match='Unsupported constraint checker'):
        check_constraints(spec,p)


def test_plane_source_admission_retains_omitted_constraints_and_suppression():
    instruction='(ABC) và (BCD) cùng vuông góc với (ABD). [A,BC,D] = 120°.'
    scan=scan_instruction(instruction)
    assert not scan['issues']
    assert [r['kind'] for r in scan['obligations']]==['perpendicular_planes','perpendicular_planes','dihedral_angle']
    spec,_=specimen()
    spec.relations[0].source_quote='[A,BC,D] = 120°'
    admitted,audit=admit_instruction(spec,instruction)
    assert len(audit['added_relations'])==2
    assert admitted.relations[0].mark is False
    chosen=selected_relations(admitted,{p.name:p.name for p in admitted.points})
    assert len(chosen['plane_sections'])==2
    for text in ('2[A,BC,D] = 120°','sin [A,BC,D] = 120°','[A,BC,D] = 120°+30°'):
        scan=scan_instruction(text)
        assert scan['issues'] and not scan['obligations']


def test_supporting_planes_with_vertex_only_body_intersection_have_a_real_extended_hinge():
    p={n:np.array(v,float) for n,v in {'S':[0,0,1],'A':[-1,-1,0],'B':[1,-1,0],'C':[1,1,0],'D':[-1,1,0]}.items()}
    faces=[list('ABCD'),list('SAB'),list('SBC'),list('SCD'),list('SDA')]
    body,edges=validate_solid(p,faces)
    added,_,_,_,records=normal_sections([{'kind':'perpendicular_planes','points':list('SABSCD'),'value':90}],p,body,set(edges))
    world={**p,**added}
    first,vertex,last=(world[n] for n in records[0]['section_points'])
    assert abs((first-vertex)@(last-vertex))<1e-8
    assert np.linalg.norm(np.cross(vertex-p['S'],np.array([1.,0,0])))<1e-8


def test_named_hinge_endpoint_with_normal_face_edges_is_a_valid_section():
    p={n:np.array(v,float) for n,v in {'B':[0,0,0],'C':[0,0,3],'A':[2,0,0],'D':[-1,math.sqrt(3),0]}.items()}
    faces=[list('BCD'),list('ABC'),list('ACD'),list('ADB')]
    body,edges=validate_solid(p,faces)
    added,carriers,_,_,records=normal_sections([{'kind':'dihedral_angle','points':list('ABCD'),'value':120}],p,body,set(edges))
    assert records[0]['section_points']==['A','B','D']
    assert not added and not carriers


@pytest.mark.parametrize('renamed',[False,True])
def test_solver_and_emitter_support_plane_constraints_without_shape_dispatch(renamed):
    spec,_=specimen('perpendicular_planes',None)
    spec.relations[0].mark=None
    if renamed:
        mapping={p.name:f'V{i}' for i,p in enumerate(spec.points)}
        for p in spec.points:p.name=mapping[p.name]
        spec.solid.vertices=[mapping[n] for n in spec.solid.vertices]
        spec.relations[0].points=[mapping[n] for n in reversed(spec.relations[0].points)]
    source,evidence=realize_spec(spec,'fixture',candidates=3)
    assert source and all(r['pass'] for r in evidence['checks'])
    section=evidence['witness']['normal_sections'][0]
    assert section['world_degrees']==pytest.approx(90,abs=1e-5)
    assert section['status']=='constructed'
    assert all(r['status']=='drawn' for r in evidence['witness']['relation_marks'])


def test_unknown_dihedral_does_not_print_answer_and_projection_binds_emitted_sector():
    _,p=specimen()
    faces=[['B','C','D'],['A','B','C'],['A','C','D'],['A','D','B']]
    plan=SpatialConstruction.model_validate({'points':[{'name':n,'op':'free','values':v.tolist()} for n,v in p.items()],
        'faces':faces,'labels':[{'point':n,'text':n} for n in p]})
    source,witness=realize_spatial(plan,base=faces[0],plane_sections=[{'kind':'dihedral_angle','points':['A','B','C','D'],'value':None}])
    assert '120' not in ''.join(r['text'] for r in witness['sector_marks'])
    assert r'^{\circ}' not in source
    for curve in witness['sector_marks'][0]['curves']:
        assert np.allclose(np.array(curve['world_points'])@np.array(witness['projection']).T,curve['projected_points'])
    assert witness['normal_sections'][0]['world_degrees']==pytest.approx(120)


def test_spatial_foot_uses_world_metric_before_projection():
    steps=[SpatialPoint(name=n,op='free',values=p) for n,p in {'A':[0,0,0],'B':[2,1,1],'P':[0,2,1]}.items()]
    steps.append(SpatialPoint(name='H',op='project',refs=['P','A','B']))
    p,_,dependent=realize_points(steps)
    assert abs((p['P']-p['H'])@(p['B']-p['A']))<1e-10
    assert '!0.5!' in dependent[0]


def test_exterior_section_is_not_dashed_just_because_it_is_auxiliary():
    planes=[(np.array([s,0.,0.]),np.array([s,0.,0.])) for s in (-1.,1.)]
    planes += [(np.array([0.,s,0.]),np.array([0.,s,0.])) for s in (-1.,1.)]
    planes += [(np.array([0.,0.,s]),np.array([0.,0.,s])) for s in (-1.,1.)]
    parts=visibility_parts(np.array([-2.,0,0]),np.array([2.,0,0]),planes,np.array([0.,0,1.]))
    assert [r['dashed'] for r in parts]==[False,True,False]
    assert parts[0]['end']==pytest.approx(.25)
    assert parts[1]['end']==pytest.approx(.75)


def test_invalid_angle_range_and_dimension_fail_before_solving():
    spec,_=specimen('plane_angle',120)
    with pytest.raises(SpecError,match='invalid_spec'):
        realize_spec(spec,'fixture',candidates=1)
    spec,_=specimen('dihedral_angle',180)
    with pytest.raises(SpecError,match='invalid_spec'):
        realize_spec(spec,'fixture',candidates=1)
