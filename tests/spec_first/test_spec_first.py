"""Constraint/compiler controls; these hand-authored specs never enter model inputs."""
import json
from itertools import pairwise
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from spec_first.spec import GeometrySpec, SpecError, check_constraints, realize_spec
from spec_first import workflow
from agent.latex.tikz import validate_tikz
from tools.spec_first.construction_pilot_cases import requirements
from evaluation.requirements import check_relations


def fixture(case):
    def relation(kind,points,**extra):
        return dict(kind=kind,points=points.split(),source_quote='fixture',**extra)
    def draw(kind,points,**extra):
        return dict(kind=kind,points=points.split(),**extra)
    solid = None
    hidden = set()
    if case == 'isosceles':
        names = 'A B M O'
        relations = [relation('equal_length','M A M B'),relation('midpoint','O A B'),
                     relation('noncollinear','M A B'),relation('perpendicular','M O A B',mark=True),
                     relation('equal_angle','A M O O M B',mark=True)]
        drawings = [draw('polygon','M A B'),draw('segment','M O')]
    elif case == 'tangency':
        names,hidden = 'O X Y M H K',{'X','Y'}
        relations = [relation('projection','H M O X'),relation('projection','K M O Y'),
                     relation('equal_length','M H M K'),relation('inside_angle','M O X Y')]
        drawings = [draw('ray','O X',label='x'),draw('ray','O Y',label='y'),draw('segment','M H'),draw('segment','M K'),draw('circle','M H')]
    elif case == 'reflection':
        names,hidden = "U V A B B' C H M",{'U','V'}
        relations = [relation('reflection',"B' B U V"),relation('intersection',"H B B' U V"),
                     relation('intersection',"C A B' U V"),relation('on_line','M U V'),
                     relation('same_side','A B U V'),relation('distinct','M C'),
                     relation('noncollinear',"M B B'"),relation('equal_length',"M B M B'")]
        drawings = [draw('line','U V',label='d'),draw('polyline','A C B'),draw('polyline','A M B'),draw('polygon',"M B B'")]
    elif case == 'tetrahedron':
        names = 'S A B C A1 A2 B1 B2 C1 C2'
        solid = {'kind':'tetrahedron','vertices':['S','A','B','C'],'source_quote':'fixture'}
        relations = [relation('partition','A A1 A2 S'),relation('parallel_section','S A B C A1 B1 C1'),relation('parallel_section','S A B C A2 B2 C2')]
        drawings = [draw('polygon','A1 B1 C1'),draw('polygon','A2 B2 C2')]
    elif case == 'pyramid':
        names = 'S A B C D O M N P Q I'
        solid = {'kind':'pyramid','vertices':['S','A','B','C','D'],'source_quote':'fixture'}
        relations = [relation('parallelogram','A B C D'),relation('intersection','O A C B D'),
                     *[relation('midpoint',f'{m} S {b}') for m,b in zip('MNPQ','ABCD')],
                     relation('intersection','I M P N Q')]
        drawings = [draw('polygon','M N P Q'),draw('segment','M P'),draw('segment','N Q'),draw('segment','S O')]
    else:
        names = "A B C D A' B' C' D' O G"
        solid = {'kind':'parallelepiped','vertices':["A","B","C","D","A'","B'","C'","D'"],'source_quote':'fixture'}
        relations = [relation('midpoint','O B D'),relation('centroid',"G B D A'")]
        drawings = [draw('polygon',"B D A'"),draw('segment',"A' O")]
    return GeometrySpec.model_validate({'dimension':3 if solid else 2,
        'points':[{'name':n,'visible':n not in hidden} for n in names.split()],
        'relations':relations,'draw':drawings,'solid':solid})


@pytest.mark.parametrize('case',['isosceles','tangency','reflection','tetrahedron','pyramid','parallelepiped'])
def test_real_cases_lower_to_valid_named_constructions_without_compile(case):
    spec = fixture(case)
    source,evidence = realize_spec(spec,'fixture',candidates=4)
    assert all(r['pass'] for r in evidence['checks'])
    assert evidence['valid_candidates'] > 0
    assert validate_tikz(source) == source
    assert 'target_tikz' not in json.dumps(evidence)
    if case == 'reflection':
        assert 'dashed' not in source
    if case == 'tangency':
        assert source.count(r'\draw[->]') == 2
    if case in {'tetrahedron','pyramid'}:
        assert 'intersection of' in source
    if case == 'tetrahedron':
        ticks = evidence['witness']['tick_marks']
        ids = evidence['identifier_map']
        assert {frozenset(t['points']) for t in ticks} == {
            frozenset((ids[a],ids[b])) for a,b in pairwise(['A','A1','A2','S'])}
        assert len(ticks)==3 and all(t['group']==1 for t in ticks)
        for tick in ticks:
            a,b = tick['points']
            assert f'({a})--node[pos={tick["fraction"]:.12g},sloped] {{$|$}} ({b})' in source


def test_spec_has_no_coordinates_camera_or_dash_escape_hatch():
    for field,value in [('coordinates',[0,0]),('dashed',True),('camera',[1,2,3])]:
        data = fixture('isosceles').model_dump()
        data[field] = value
        with pytest.raises(ValidationError):
            GeometrySpec.model_validate(data)


def test_source_quotes_and_unknown_references_are_checked():
    spec = fixture('isosceles')
    with pytest.raises(SpecError,match='Nonverbatim'):
        realize_spec(spec,'different text',candidates=1)
    spec.relations[0].points[0] = 'Unknown'
    with pytest.raises(SpecError,match='Unknown'):
        realize_spec(spec,'fixture',candidates=1)


def test_contradiction_and_cycle_fail_without_a_render():
    spec = fixture('isosceles')
    spec.relations.append(spec.relations[1].model_copy(update={'kind':'on_segment','points':['M','A','B']}))
    with pytest.raises(SpecError,match='search_exhausted'):
        realize_spec(spec,'fixture',candidates=3)
    spec = fixture('isosceles')
    spec.relations.append(spec.relations[1].model_copy(update={'points':['A','O','B']}))
    with pytest.raises(SpecError,match='Cyclic'):
        realize_spec(spec,'fixture',candidates=1)


def test_wrong_ray_branch_and_incomplete_spec_are_not_certificates():
    spec = fixture('tangency')
    _,evidence = realize_spec(spec,'fixture',candidates=2)
    p = {n:evidence['witness']['world_points'][internal] for n,internal in evidence['identifier_map'].items()}
    p['M'] = [-v for v in p['M']]
    assert any(not row['pass'] for row in check_constraints(spec,p))
    incomplete = fixture('isosceles')
    incomplete.relations = [r for r in incomplete.relations if r.kind == 'midpoint']
    _,evidence = realize_spec(incomplete,'fixture',candidates=4)
    p = {n:evidence['witness']['world_points'][internal] for n,internal in evidence['identifier_map'].items()}
    assert all(row['pass'] for row in evidence['checks'])
    assert any(row['status'] != 'pass' for row in check_relations(requirements('isosceles'),p))


def test_parameter_variants_preserve_supplied_relations():
    spec = fixture('isosceles')
    positions = []
    for seed in range(4):
        _,evidence = realize_spec(spec,'fixture',seed=seed,candidates=2)
        assert all(row['pass'] for row in evidence['checks'])
        positions.append(evidence['witness']['world_points'][evidence['identifier_map']['M']])
    assert len(set(map(tuple,positions))) == 4


def test_single_extraction_then_deterministic_execution(monkeypatch,tmp_path):
    calls = []
    spec = fixture('isosceles')
    class Model:
        def with_structured_output(self,schema,**kwargs):
            assert schema is GeometrySpec and kwargs == {'method':'function_calling','include_raw':True}
            return self
        def invoke(self,messages):
            calls.append('model')
            assert messages[1] == {'role':'user','content':'fixture'}
            return {'raw':SimpleNamespace(model_dump=lambda **_: {'content':'fixture'}),'parsed':spec,'parsing_error':None}
    def render(source,runtime):
        calls.append('compile')
        return [],{'tikz':source,'rendered_png_path':str(tmp_path/'fixture.png')}
    monkeypatch.setattr(workflow.render_tikz,'func',render)
    result = workflow.draw_spec_first(instruction='fixture',model=Model(),artifact_dir=tmp_path,compiler_http=object())
    assert calls == ['model','compile'] and result.usable
    assert result.status == 'usable_with_issues' and not result.success
    assert result.unresolved_issues
    stages = json.loads((tmp_path/'stages.json').read_text())
    assert stages['status'] == 'rendered_without_model_review'
    spec.relations[0].source_quote = 'fabricated'
    calls.clear()
    with pytest.raises(SpecError):
        workflow.draw_spec_first(instruction='fixture',model=Model(),artifact_dir=tmp_path,compiler_http=object())
    assert calls == ['model']
    assert json.loads((tmp_path/'stages.json').read_text())['failure_stage'] == 'realization'


def test_traced_workflow_records_exactly_one_model_call(monkeypatch,tmp_path):
    from functools import partial
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration,ChatResult
    from langchain_core.runnables import RunnableLambda
    from langchain_openai import ChatOpenAI
    from tools.spec_first.run_construction_pilot import Recorder,_invoke_spec_first
    spec=fixture('isosceles')
    class LocalModel(ChatOpenAI):
        def _generate(self,messages,stop=None,run_manager=None,**kwargs):
            message=AIMessage(content='',tool_calls=[{'name':'GeometrySpec','args':spec.model_dump(),'id':'local','type':'tool_call'}])
            return ChatResult(generations=[ChatGeneration(message=message)])
    monkeypatch.setattr(workflow.render_tikz,'func',lambda source,runtime:([],{'tikz':source,'rendered_png_path':str(tmp_path/'control.png')}))
    recorder=Recorder(tmp_path)
    model=LocalModel(api_key='local-test-only',model='local-test-only')
    runnable=RunnableLambda(partial(_invoke_spec_first,model=model,directory=tmp_path,http=object()),name='spec_first')
    result=runnable.invoke('fixture',config={'callbacks':[recorder]})
    assert result.usable and len(recorder.calls)==1
    assert recorder.calls[0]['seconds'] is not None


def test_section_requires_a_plane_and_an_apex_outside_it():
    from spec_first.spec import Relation,SpecPoint,DrawObject
    spec=fixture('parallelepiped')
    spec.points=[p for p in spec.points if p.name not in {'O','G'}]
    spec.points.extend(SpecPoint(name=n) for n in 'PQRT')
    spec.relations=[Relation(kind='midpoint',points=['P','D','A'],source_quote='fixture'),
                    Relation(kind='parallel_section',points=['D','A','B','C',"A'",'P','Q','R','T'],source_quote='fixture')]
    spec.draw=[DrawObject(kind='polygon',points=list('PQRT'))]
    with pytest.raises(SpecError,match='parallel_section'):
        realize_spec(spec,'fixture',candidates=1)
    valid=fixture('tetrahedron')
    _,evidence=realize_spec(valid,'fixture',candidates=1)
    p={n:evidence['witness']['world_points'][internal] for n,internal in evidence['identifier_map'].items()}
    p['S']=[sum(p[n][i] for n in 'ABC')/3 for i in range(3)]
    for first,fraction in [('A1',2/3),('A2',1/3)]:
        for base,name in zip('ABC',[first,first.replace('A','B'),first.replace('A','C')]):
            p[name]=[p['S'][i]+fraction*(p[base][i]-p['S'][i]) for i in range(3)]
    assert all(not r['pass'] for r in check_constraints(valid,p) if r['kind']=='parallel_section')


def test_parallel_section_definition_precedes_redundant_fraction():
    from spec_first.spec import Relation
    spec=fixture('tetrahedron')
    spec.relations.insert(0,Relation(kind='interpolation',points=['B1','S','B'],values=[2/3],source_quote='fixture'))
    _,evidence=realize_spec(spec,'fixture',candidates=1)
    definition=next(r for r in evidence['lowered_operations'] if r['name']=='B1')
    assert definition['op']=='intersect' and 'A1' in definition['refs']


@pytest.mark.parametrize('reversed_feet',[['H'],['K'],['H','K']])
def test_projection_support_order_preserves_bisector_and_ray_branch(reversed_feet):
    spec=fixture('tangency')
    for r in spec.relations:
        if r.kind=='projection' and r.points[0] in reversed_feet:
            r.points[2:]=reversed(r.points[2:])
    _,evidence=realize_spec(spec,'fixture',candidates=2)
    p={n:evidence['witness']['world_points'][internal] for n,internal in evidence['identifier_map'].items()}
    assert all(r['pass'] for r in check_constraints(spec,p))
    for name in ['M','H','K']:
        p[name]=[-x for x in p[name]]
    branches=[r for r in check_constraints(spec,p) if r['kind']=='projection_on_positive_ray']
    assert len(branches)==2 and all(not r['pass'] for r in branches)


@pytest.mark.parametrize('kind,points,values,case',[
    ('length_ratio',['M','N','A','B'],[2],'pyramid'),
    ('partition',['A','A1','A2','S'],[1,2,3],'tetrahedron'),
])
def test_unsupported_selected_marks_are_rejected(kind,points,values,case):
    from spec_first.spec import Relation
    spec=fixture(case)
    spec.relations.append(Relation(kind=kind,points=points,values=values,mark=True,source_quote='fixture'))
    with pytest.raises(SpecError,match='Visible annotation'):
        realize_spec(spec,'fixture',candidates=1)


def test_spatial_selected_perpendicular_is_bound_to_verified_world_rays():
    from spec_first.spec import Relation
    spec=fixture('tetrahedron')
    spec.relations.append(Relation(kind='perpendicular',points=['S','A','A','B'],mark=True,source_quote='fixture'))
    _,evidence=realize_spec(spec,'fixture')
    assert all(check['pass'] for check in evidence['checks'])
    marks=evidence['witness']['relation_marks']
    assert marks and all(mark['status']=='drawn' for mark in marks)


def test_angle_marks_require_drawn_arms():
    spec=fixture('isosceles')
    spec.draw=spec.draw[:1]
    with pytest.raises(SpecError,match='no drawn carrier'):
        realize_spec(spec,'fixture',candidates=1)
    spec=fixture('tangency')
    spec.draw=[r for r in spec.draw if r.kind!='segment']
    spec.relations[2].mark=False
    source,_=realize_spec(spec,'fixture',candidates=1)
    assert 'right angle' not in source
    spec.relations[0].mark=True
    with pytest.raises(SpecError,match='no drawn carrier'):
        realize_spec(spec,'fixture',candidates=1)



@pytest.mark.parametrize('implicit_closure',[False,True])
@pytest.mark.parametrize('vertices',[[[10,0],[7,-1],[8,0],[7,1]],[[10,0],[7,-1],[7,1]]])
def test_filled_ray_head_requires_shape_direction_and_attached_shaft(implicit_closure,vertices):
    import numpy as np
    from shapely.geometry import LineString
    from tools.spec_first.spec_first_pilot_cases import _filled_ray_arrow
    path=vertices if implicit_closure else vertices+vertices[:1]
    items=[['l',a,b] for a,b in pairwise(path)]
    drawing={'operation':'fill','subpaths':[[['m',path[0]],*items]]}
    scene={'paths':[drawing],'strokes':[{'dashed':False,'components':[LineString([[0,0],[9.5,0]])]}]}
    origin,end=np.asarray([0,0]),np.asarray([5,0])
    assert _filled_ray_arrow(scene,origin,end)
    assert not _filled_ray_arrow(scene,end,origin)
    scene['strokes'][0]['components']=[LineString([[0,0],[5,0]])]
    assert not _filled_ray_arrow(scene,origin,end)
    scene['strokes'][0]['components']=[LineString([[0,0],[9.5,0]])]
    items[0][2]=[7,-2]
    assert not _filled_ray_arrow(scene,origin,end)



@pytest.mark.parametrize('wrapping',['plain','fenced','prose','truncated','extra_field'])
def test_json_transport_is_complete_and_schema_validated(monkeypatch,tmp_path,wrapping):
    from langchain_core.messages import AIMessage
    payload=fixture('isosceles').model_dump()
    if wrapping=='extra_field':payload['camera']=[1,2,3]
    content=json.dumps(payload)
    if wrapping=='fenced':content='```json\n'+content+'\n```'
    if wrapping=='prose':content='Here is the specification: '+content
    if wrapping=='truncated':content=content[:-1]
    calls=[]
    class Model:
        def with_structured_output(self,*args,**kwargs):return self
        def invoke(self,messages):
            calls.append('model')
            return {'raw':AIMessage(content=content),'parsed':None,'parsing_error':None}
    def render(source,runtime):
        calls.append('compile')
        return [],{'tikz':source,'rendered_png_path':str(tmp_path/'control.png')}
    monkeypatch.setattr(workflow.render_tikz,'func',render)
    if wrapping in {'plain','fenced'}:
        assert workflow.draw_spec_first(instruction='fixture',model=Model(),artifact_dir=tmp_path,compiler_http=object()).usable
        assert calls==['model','compile']
        assert json.loads((tmp_path/'stages.json').read_text())['response_format']=='json_text_fallback'
    else:
        with pytest.raises(SpecError,match='invalid_spec'):
            workflow.draw_spec_first(instruction='fixture',model=Model(),artifact_dir=tmp_path,compiler_http=object())
        assert calls==['model']
