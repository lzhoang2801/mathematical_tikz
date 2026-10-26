"""Spatial solving controls independent of model calls, dataset IDs and targets."""
from pathlib import Path
import random
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from spec_first.planar_solver import forward_points
from spec_first.spatial_construction import SpatialPoint, realize_points
from spec_first.spec import GeometrySpec, Relation, SpecError, realize_spec


def spatial_spec(kind):
    def relation(kind, names):
        return {'kind':kind,'points':names.split(),'source_quote':'control','mark':False}
    if kind == 'trapezoid':
        names = 'S A B C D E F G H'
        solid = {'kind':'pyramid','vertices':['S','A','B','C','D'],'source_quote':'control'}
        relations = [relation('parallel','A B C D'),relation('on_segment','E S A'),
                     relation('parallel_section','S A B C D E F G H')]
        draw = [{'kind':'polygon','points':['E','F','G','H']}]
    elif kind == 'regular':
        names = 'A B C D M H'
        solid = {'kind':'tetrahedron','vertices':['A','B','C','D'],'source_quote':'control'}
        relations = [relation('equal_length','A B A C A D B C B D C D'),
                     relation('midpoint','M C D'),relation('centroid','H B C D'),
                     relation('perpendicular','A H B C'),relation('perpendicular','A H B D')]
        draw = [{'kind':'segment','points':s.split()} for s in ('A M','B M','A H')]
    else:
        names = 'A B C D M N'
        solid = {'kind':'tetrahedron','vertices':['A','B','C','D'],'source_quote':'control'}
        relations = [relation('perpendicular','A C A B'),relation('perpendicular','B D A B'),
                     relation('midpoint','M A B'),relation('midpoint','N C D')]
        draw = [{'kind':'segment','points':['M','N']}]
    return GeometrySpec.model_validate({'dimension':3,'points':[{'name':n} for n in names.split()],
        'solid':solid,'relations':relations,'draw':draw})


@pytest.mark.parametrize('kind',['perpendicular','trapezoid','regular'])
@pytest.mark.parametrize('renamed,seed',[(False,0),(True,7)])
def test_spatial_constraints_solve_before_projection_without_case_dispatch(kind,renamed,seed):
    spec = spatial_spec(kind)
    mapping = {p.name:f'V{i}' if renamed else p.name for i,p in enumerate(spec.points)}
    for point in spec.points:
        point.name = mapping[point.name]
    for relation in spec.relations:
        relation.points = [mapping[n] for n in relation.points]
    for obj in spec.draw:
        obj.points = [mapping[n] for n in obj.points]
    spec.solid.vertices = [mapping[n] for n in spec.solid.vertices]
    random.Random(seed).shuffle(spec.relations)
    source,evidence = realize_spec(spec,'control',seed=seed,candidates=3)
    world = evidence['witness']['world_points']
    p = {old:np.array(world[evidence['identifier_map'][new]]) for old,new in mapping.items()}
    assert source and evidence['valid_candidates'] > 0
    assert evidence['candidate_count'] <= evidence['candidate_budget'] == 3
    assert evidence['solver_attempts']
    assert all(s['nfev'] <= 80 and s['dimension'] == 3 for s in evidence['solver_attempts'])
    assert all(c['pass'] for c in evidence['checks'])
    if kind == 'perpendicular':
        assert abs(np.dot(p['C']-p['A'],p['B']-p['A'])) < 1e-5
        assert abs(np.dot(p['D']-p['B'],p['B']-p['A'])) < 1e-5
        assert p['M'] == pytest.approx((p['A']+p['B'])/2)
        assert p['N'] == pytest.approx((p['C']+p['D'])/2)
    elif kind == 'trapezoid':
        assert np.linalg.norm(np.cross(p['B']-p['A'],p['D']-p['C'])) < 1e-5
        normal = np.cross(p['B']-p['A'],p['D']-p['A'])
        assert abs(np.dot(p['C']-p['A'],normal)) < 1e-5
        axis = p['A']-p['S']
        t = float(np.dot(p['E']-p['S'],axis)/np.dot(axis,axis))
        assert 0 < t < 1
        for base,cut in zip('ABCD','EFGH'):
            assert p[cut] == pytest.approx(p['S']+t*(p[base]-p['S']),abs=1e-6)
    else:
        lengths = [np.linalg.norm(p[a]-p[b]) for a,b in ('AB','AC','AD','BC','BD','CD')]
        assert max(lengths)-min(lengths) < 1e-5
        assert p['H'] == pytest.approx((p['B']+p['C']+p['D'])/3)
        assert abs(np.dot(p['A']-p['H'],p['C']-p['B'])) < 1e-5
    # A 3D residual pass is checked again by the independent emission executor.
    executed,_,_ = realize_points([SpatialPoint.model_validate(s) for s in evidence['execution_operations']])
    for name,value in executed.items():
        assert value == pytest.approx(world[name])


def test_inconsistent_spatial_relations_never_reach_camera_or_emitter(monkeypatch):
    import spec_first.spec as worker
    spec = spatial_spec('perpendicular')
    spec.relations.append(Relation(kind='parallel',points=['A','C','A','B'],source_quote='control'))
    def unexpected(*args,**kwargs):
        raise AssertionError('Inconsistent geometry reached the renderer')
    monkeypatch.setattr(worker,'realize_spatial',unexpected)
    with pytest.raises(SpecError,match='search_exhausted'):
        realize_spec(spec,'control',candidates=2)


def test_spatial_search_stops_after_three_valid_configurations():
    _,evidence = realize_spec(spatial_spec('perpendicular'),'control',candidates=12)
    assert evidence['valid_candidates'] == 3
    assert evidence['candidate_count'] == 3
    assert evidence['candidate_budget'] == 12


def test_spatial_forward_search_does_not_certify_skew_intersections():
    steps = [{'name':n,'op':'free','values':p} for n,p in
             [('A',[0,0,0]),('B',[3,0,0]),('C',[1,-1,0]),('D',[1,2,0])]]
    steps += [{'name':'I','op':'intersect','refs':['A','B','C','D']},
              {'name':'T','op':'translate','refs':['I','A','C']}]
    raw = forward_points(steps)
    exact,_,_ = realize_points([SpatialPoint.model_validate(s) for s in steps])
    for name in raw:
        assert raw[name] == pytest.approx(exact[name])
    steps[2]['values'][2] = steps[3]['values'][2] = 1
    assert np.isfinite(forward_points(steps)['I']).all()
    with pytest.raises(ValueError,match='Skew'):
        realize_points([SpatialPoint.model_validate(s) for s in steps])
