"""Spatial validation, fair PDF checks and visibility edge-case regressions."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pytest
from shapely.geometry import LineString

from spec_first.spatial_construction import SpatialConstruction, realize_spatial
from spec_first.prompts.spatial_construction import spatial_construction_messages
from agent.prompts.problem_tikz import problem_tikz_messages
from agent.latex.tikz import validate_tikz
from tools.spec_first.spatial_pilot_cases import canonical, expected_styles, fit_projection, style_support


def pyramid():
    points = [{'name':n,'op':'free','values':v} for n,v in {'A':[0,0,0],'B':[5,0,0],'D':[1,3,0],'S':[1.3,1,4]}.items()]
    points += [{'name':'C','op':'translate','refs':['B','A','D']}, {'name':'O','op':'lerp','refs':['A','C'],'values':[0.5]}]
    points += [{'name':name,'op':'lerp','refs':['S',base],'values':[0.5]} for name,base in zip('MNPQ','ABCD')]
    points += [{'name':'I','op':'intersect','refs':['M','P','N','Q']}]
    return SpatialConstruction(points=points, faces=[['A','B','C','D'],['S','A','B'],['S','B','C'],['S','C','D'],['S','D','A']],
        segments=[{'a':a,'b':b} for a,b in [('M','N'),('N','P'),('P','Q'),('Q','M'),('M','P'),('N','Q'),('S','O')]],
        labels=[{'point':n,'text':n} for n in 'ABCDSOMNPQI'])


def test_spatial_dependencies_camera_and_internal_visibility():
    source,witness = realize_spatial(pyramid())
    assert validate_tikz(source) == source
    assert 'intersection of M--P and N--Q' in source
    assert '$(B)+(D)-(A)$' in source
    assert np.allclose(witness['world_points']['I'], (np.array(witness['world_points']['S'])+witness['world_points']['O'])/2)
    styles = {tuple(row['points']):row['dashed'] for row in witness['segments']}
    assert styles[('M','P')] and styles[('N','Q')] and styles[('O','S')]
    assert any(not row['dashed'] for row in witness['segments'])
    assert len(witness['projection']) == 2


@pytest.mark.parametrize('mutation,match', [
    (lambda p: p.faces.pop(), 'closed'),
    (lambda p: p.faces.__setitem__(0,['A','C','B','D']), 'cycle'),
    (lambda p: setattr(p.points[3],'values',[1.3,1,0]), 'volume'),
    (lambda p: setattr(p.points[-1],'refs',['S','A','B','C']), 'Skew'),
    (lambda p: setattr(p.points[0],'values',[100,0,0]), 'oversized'),
])
def test_invalid_spatial_plans_rejected_before_tex(mutation,match):
    plan=pyramid();mutation(plan)
    with pytest.raises(ValueError,match=match):
        realize_spatial(plan)


def test_affine_check_holds_auxiliaries_out_of_fit_and_allows_other_views():
    matrix=np.array([[90,-40,25],[12,30,-110]])
    for case in ('tetrahedron','pyramid','parallelepiped'):
        world,anchors,_,_,_=canonical(case)
        observed={name:matrix@point+[200,170] for name,point in world.items()}
        assert fit_projection(case,observed)['status']=='pass'
        auxiliary=next(name for name in world if name not in anchors)
        observed[auxiliary]=observed[auxiliary]+[2,1]
        assert fit_projection(case,observed)['status']=='fail'


def test_tetrahedron_can_have_no_hidden_edges_and_sign_is_global():
    near,_=expected_styles('tetrahedron',np.array([-1.,-1.,3.])/np.sqrt(11))
    far,_=expected_styles('tetrahedron',np.array([1.,1.,-3.])/np.sqrt(11))
    assert not any(near.values())
    assert any(far.values())


def test_opposite_style_overlay_is_measured_but_crossings_are_not():
    def stroke(a,b,dashed):
        line=LineString([a,b]);return {'geometry':line,'components':[line],'dashed':dashed}
    scene={'strokes':[stroke([0,0],[100,0],False),stroke([50,-30],[50,30],True)]}
    assert style_support(scene,[0,0],[100,0],False)==pytest.approx(1)
    assert style_support(scene,[0,0],[100,0],True)==0
    scene['strokes'].append(stroke([0,0],[100,0],True))
    assert style_support(scene,[0,0],[100,0],True)==pytest.approx(1)


def test_spatial_prompt_keeps_identical_user_input():
    assert spatial_construction_messages('Opaque instruction')[1] == problem_tikz_messages('Opaque instruction')[1]


def test_shared_spatial_visibility_convention_in_both_arms():
    from spec_first.prompts.spatial_construction import SPATIAL_VIEW_CONVENTION, spatial_task_messages
    assert SPATIAL_VIEW_CONVENTION in spatial_task_messages('Opaque')[0]['content']
    assert SPATIAL_VIEW_CONVENTION in spatial_construction_messages('Opaque')[0]['content']


def test_spatial_prepare_freezes_distinct_real_cases_without_model_invocation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import httpx
    from tools.spec_first import run_construction_pilot as runner
    model = SimpleNamespace(model_name='fixture',openai_api_base='http://fixture',temperature=0,top_p=None,seed=None,max_tokens=8192,max_retries=0)
    monkeypatch.setattr(runner,'build_model',lambda **kwargs:model)
    monkeypatch.setattr(runner,'code_hashes',dict)
    client_type = httpx.Client
    monkeypatch.setattr(runner.httpx,'Client',lambda **kwargs:client_type(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'toolchain':'fixture'})),**kwargs))
    runner.prepare(tmp_path,'http://compiler','spatial')
    protocol=runner.read(tmp_path/'protocol.json')
    assert protocol['suite']=='spatial' and len(protocol['order'])==12
    inputs=runner.read(tmp_path/'inputs.json')
    assert {row['case'] for row in inputs} == {'tetrahedron','pyramid','parallelepiped'}
    assert all(set(row)=={'case','id','instruction'} for row in inputs)
