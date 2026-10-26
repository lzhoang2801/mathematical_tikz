"""Coupled geometry and branch controls, independent of corpus IDs or targets."""
from pathlib import Path
import random
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from spec_first.construction import Construction, realize
from spec_first.planar_solver import forward_points, line_circle_parameters
from spec_first.spec import GeometrySpec, Relation, SpecError, check_constraints, realize_spec


def chord_spec():
    def r(kind,points):
        return {'kind':kind,'points':points.split(),'source_quote':'control'}
    return GeometrySpec.model_validate({'dimension':2,
        'points':[{'name':n} for n in ['A','B','C','O','H','M','I','D','E']],
        'relations':[r('midpoint','O A B'),r('equal_length','O C O A'),r('noncollinear','A B C'),
                     r('projection','H C A B'),r('midpoint','M C H'),r('projection','I M O C'),
                     r('on_line','D M I'),r('on_line','E M I'),r('equal_length','O D O A'),
                     r('equal_length','O E O A'),r('same_side','D C A B'),r('same_side','E C A B'),
                     r('on_segment','M D E'),r('distinct','D E')],
        'draw':[{'kind':kind,'points':names.split()} for kind,names in
                [('circle','O A'),('circle','C D'),('segment','A B'),('segment','C H'),('segment','O C'),('segment','D E')]]})


@pytest.mark.parametrize('scale',[.01,1,1000])
def test_line_circle_roots_external_tangent_and_no_intersection(scale):
    a,b,o = np.array([2.,0])*scale,np.array([3.,0])*scale,np.zeros(2)
    assert line_circle_parameters(a,b,o,scale) == pytest.approx((-3,-1))
    assert line_circle_parameters(a,b,o+[0,scale],scale) == pytest.approx((-2,-2))
    assert line_circle_parameters(a,b,o+[0,2*scale],scale) == ()
    assert line_circle_parameters([0,2],[1e9,2],[0,0],1) == ()
    with pytest.raises(ValueError,match='Degenerate'):
        line_circle_parameters(a,a,o,scale)


@pytest.mark.parametrize('rename,reverse',[(False,False),(True,True)])
def test_coupled_chord_is_solved_without_case_names_or_model_changes(rename,reverse):
    spec = chord_spec()
    mapping = {p.name:f'V{i}' if rename else p.name for i,p in enumerate(spec.points)}
    for p in spec.points:
        p.name = mapping[p.name]
    for r in spec.relations:
        r.points = [mapping[n] for n in r.points]
    for d in spec.draw:
        d.points = [mapping[n] for n in d.points]
    if reverse:
        random.Random(17).shuffle(spec.relations)
    source,evidence = realize_spec(spec,'control',seed=0,candidates=8)
    raw = evidence['witness']['world_points']
    p = {old:np.array(raw[evidence['identifier_map'][new]]) for old,new in mapping.items()}
    radius = np.linalg.norm(p['A']-p['O'])
    for n in 'CDE':
        assert np.linalg.norm(p[n]-p['O']) == pytest.approx(radius,rel=1e-7)
    u = p['I']-p['M']
    parameters = [float((p[n]-p['M'])@u/(u@u)) for n in 'DE']
    assert min(parameters)<-1 and max(parameters)>3
    assert np.dot(p['D']-p['M'],p['E']-p['M'])<0
    assert all(c['pass'] for c in evidence['checks'])
    assert 'node[midway,sloped]' not in source
    assert any(step['op']=='project' for step in evidence['execution_operations'])
    assert any(step['op']=='lerp' for step in evidence['execution_operations'])
    assert all(a['nfev']<=80 for a in evidence['solver_attempts'])
    assert any(a['line_circle_seeds'] for a in evidence['solver_attempts'])


def test_explicit_radius_marks_still_require_painted_carriers():
    spec = chord_spec()
    spec.relations[8].mark = True
    with pytest.raises(SpecError,match='no drawn carrier'):
        realize_spec(spec,'control',candidates=8)


def test_false_geometry_is_rejected_before_annotation_or_emission(monkeypatch):
    import spec_first.spec as worker
    spec = chord_spec()
    spec.relations.append(Relation(kind='on_line',points=['C','A','B'],source_quote='control'))
    def unexpected(*args,**kwargs):
        raise AssertionError('Invalid geometry reached the emitter')
    monkeypatch.setattr(worker,'_planar',unexpected)
    with pytest.raises(SpecError,match='search_exhausted'):
        realize_spec(spec,'control',candidates=2)


def test_numerical_forward_pass_matches_emission_executor():
    steps=[{'name':'A','op':'free','values':[0,0]}, {'name':'B','op':'free','values':[5,0]},
           {'name':'C','op':'free','values':[1,3]}, {'name':'D','op':'rotate','refs':['A','B'],'values':[70]},
           {'name':'H','op':'project','refs':['C','A','B']}, {'name':'R','op':'reflect','refs':['C','A','B']},
           {'name':'M','op':'lerp','refs':['A','C'],'values':[.3]},
           {'name':'I','op':'intersect','refs':['C','R','A','B']}]
    plan=Construction.model_validate({'points':steps,'segments':[{'a':'A','b':'B'}],
        'labels':[{'point':'A','text':'A','position':'below'}]})
    _,emitted=realize(plan)
    computed=forward_points(steps)
    for name in emitted:
        assert computed[name] == pytest.approx(emitted[name])


def test_solver_pass_does_not_certify_omitted_metric_constraints():
    spec=GeometrySpec.model_validate({'dimension':2,'points':[{'name':n} for n in 'OAB'],
        'relations':[{'kind':'perpendicular','points':['O','A','A','B'],'source_quote':'control'}],
        'draw':[{'kind':'polygon','points':['O','A','B']}]})
    _,evidence=realize_spec(spec,'control',candidates=4)
    raw=evidence['witness']['world_points'];p={n:raw[i] for n,i in evidence['identifier_map'].items()}
    assert all(c['pass'] for c in check_constraints(spec,p))
    assert 'source fidelity is independently evaluated' in evidence['scope']
    assert all(c['pass'] for c in check_constraints(spec,{'O':[0,0],'A':[1,0],'B':[1,1]}))
