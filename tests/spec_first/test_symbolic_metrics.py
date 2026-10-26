"""Symbolic quantities retain their dimensions through admission and emission."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from spec_first.instruction_constraints import scan_instruction
from spec_first.metric_expression import parse_measure
from spec_first.spec import GeometrySpec, Relation, SpecError, check_constraints, admit_instruction, realize_spec


@pytest.mark.parametrize('expression,coefficient,parameter',[
    ('a',1,'a'),('2a',2,'a'),('a/(2√3)',1/(2*np.sqrt(3)),'a'),
    ('a√2',np.sqrt(2),'a'),(r'\frac{a}{2\sqrt{3}}',1/(2*np.sqrt(3)),'a'),
    ('a/2+a/3',5/6,'a'),('2*(R/3)',2/3,'R'),('sqrt(5)',np.sqrt(5),''),
])
def test_dimension_preserving_expression_grammar(expression,coefficient,parameter):
    value=parse_measure(expression)
    assert value.coefficient==pytest.approx(coefficient)
    assert value.parameter==parameter


@pytest.mark.parametrize('expression',[
    'a+b','a+1','a*b','a/b','sqrt(a)','a^2','a/0','0','-a',
    'a/(2√3) + unknown','O5','1e5','__import__("os")','a;exit()',
    'sqrt(-1)','1'+'0'*40,'('*15+'a'+')'*15,r'\input{secret}',
    'a*(0.1+0.2-0.3)','a*(sqrt(2)*sqrt(2)-2)','a/(sqrt(2)*sqrt(2)-2)',
    'a*(1.000000000000001-1)',
])
def test_unsupported_expressions_never_become_partial_lengths(expression):
    with pytest.raises(ValueError):
        parse_measure(expression)


def symbolic_pyramid(parameter='a', names='SABCM'):
    s,a,b,c,m=names
    instruction=f'Pyramid {s}.{a}{b}{c}. {a}{b}={a}{c}={parameter}, ∠{b}{a}{c}=120°, {s}{a}={parameter}/(2√3). {s}{a} perpendicular to the base; {m} is midpoint of {b}{c}; draw {a}{m}, {s}{m}.'
    def r(kind,points):
        return {'kind':kind,'points':list(points),'source_quote':instruction,'mark':False}
    spec=GeometrySpec.model_validate({'dimension':3,'points':[{'name':n} for n in names],
        'relations':[r('perpendicular',s+a+a+b),r('perpendicular',s+a+a+c),r('midpoint',m+b+c)],
        'solid':{'kind':'pyramid','vertices':list(s+a+b+c),'source_quote':instruction},
        'draw':[{'kind':'segment','points':list(a+m)},{'kind':'segment','points':list(s+m)}]})
    return spec,instruction


@pytest.mark.parametrize('parameter,names,seed',[('a','SABCM',0),('t','PXYZH',7)])
def test_missing_symbolic_dimensions_and_fixed_angle_reach_spatial_solver(parameter,names,seed):
    spec,instruction=symbolic_pyramid(parameter,names)
    original=spec.model_dump_json()
    source,evidence=realize_spec(spec,instruction,seed=seed,candidates=3)
    assert spec.model_dump_json()==original
    p={n:np.array(evidence['witness']['world_points'][i]) for n,i in evidence['identifier_map'].items()}
    s,a,b,c,m=(p[n] for n in names)
    ab=np.linalg.norm(b-a)
    assert np.linalg.norm(c-a)/ab==pytest.approx(1,abs=1e-7)
    assert np.linalg.norm(s-a)/ab==pytest.approx(1/(2*np.sqrt(3)),abs=1e-7)
    assert np.dot(b-a,c-a)/(ab*np.linalg.norm(c-a))==pytest.approx(-.5,abs=1e-7)
    assert np.dot(s-a,b-a)==pytest.approx(0,abs=1e-6)
    assert np.dot(s-a,c-a)==pytest.approx(0,abs=1e-6)
    assert m==pytest.approx((b+c)/2,abs=1e-6)
    assert evidence['metric_frame']['parameter']==parameter
    assert len(evidence['instruction_audit']['added_relations'])==4
    assert source and evidence['valid_candidates']>0


def test_symbolic_labels_bind_to_same_world_metric_and_drawing():
    spec,instruction=symbolic_pyramid()
    instruction+=' Label the lengths a, a/(2√3).'
    source,evidence=realize_spec(spec,instruction,candidates=1)
    labels=evidence['spec']['length_labels']
    assert {tuple(l['points']) for l in labels}=={('A','B'),('A','C'),('S','A')}
    assert r'\frac{a}{2\,\sqrt{3}}' in source
    assert all(l['expression'] and l['value'] is None for l in labels)


def test_symbolic_source_conflicts_and_independent_parameters_are_not_normalized_away():
    spec,instruction=symbolic_pyramid()
    spec.relations.append(Relation(kind='length',points=['S','A'],expression='a/2',source_quote=instruction))
    with pytest.raises(SpecError,match='source_conflict'):
        realize_spec(spec,instruction,candidates=1)
    for expression in ('b','3'):
        spec,instruction=symbolic_pyramid()
        instruction=instruction.replace('SA=a/(2√3)',f'SA={expression}')
        for relation in spec.relations: relation.source_quote=instruction
        spec.solid.source_quote=instruction
        with pytest.raises(SpecError,match='shared positive parameter'):
            realize_spec(spec,instruction,candidates=1)


def test_fixed_angle_and_lengths_reject_wrong_world_even_when_extractor_omits_them():
    spec,instruction=symbolic_pyramid()
    admitted,_=admit_instruction(spec,instruction)
    wrong={'A':[0,0,0],'B':[1,0,0],'C':[0,1,0],'S':[0,0,1],'M':[.5,.5,0]}
    failures=[r['kind'] for r in check_constraints(admitted,wrong) if not r['pass']]
    assert 'angle' in failures and 'length' in failures


@pytest.mark.parametrize('text',['AB=AC=a+b.','2AB=a.','AB=a,5.','AB=AC=a/0.','∠BAC=120°+x.',
    '2∠BAC=120°.','180°-∠BAC=120°.','∠BAC=120°,5.','k∠BAC=120°.','k ∠BAC=120°.','sin ∠BAC=120°.'])
def test_complete_source_notation_is_required(text):
    scan=scan_instruction(text)
    assert scan['issues'] and not scan['obligations']


@pytest.mark.parametrize('text',['Angle BAC=120°.','Cho góc BAC=120°.'])
def test_fixed_angle_words_remain_supported(text):
    scan=scan_instruction(text)
    assert not scan['issues'] and scan['obligations'][0]['value']==120
