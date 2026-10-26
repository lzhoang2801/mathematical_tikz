"""Source obligations, metric fidelity and admission without a model oracle."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from spec_first.instruction_constraints import scan_instruction
from spec_first.spec import GeometrySpec, Relation, SpecError, admit_instruction, check_constraints, realize_spec
from spec_first import workflow


@pytest.mark.parametrize('instruction,expected,value',[
    ('SE/SA = SF/SB = 1/3.', [['S','E','S','A'],['S','F','S','B']], 1/3),
    ('A1B1 / C1D1 = E1F1 / G1H1 = 0.4;', [['A1','B1','C1','D1'],['E1','F1','G1','H1']], .4),
    ("A′B′/CD=2/5.", [["A'","B'",'C','D']], .4),
])
def test_complete_segment_fraction_chains_do_not_become_denominator_assignments(instruction,expected,value):
    audit=scan_instruction(instruction)
    assert not audit['issues']
    assert [r['points'] for r in audit['obligations']]==expected
    assert all(r['kind']=='length_ratio' and r['value']==pytest.approx(value) for r in audit['obligations'])
    assert all(instruction[r['span'][0]:r['span'][1]]==r['quote'] for r in audit['obligations'])


@pytest.mark.parametrize('expression',['1/0','0','a','1/3 + x','1/3 cm'])
def test_fraction_chain_never_keeps_only_the_numeric_prefix(expression):
    audit=scan_instruction('SE/SA = SF/SB = '+expression+'.')
    assert audit['issues'] and not audit['obligations']


def test_fraction_chain_admission_preserves_missing_ratio_and_detects_wrong_geometry():
    instruction='SE/SA = SF/SB = 1/3.'
    spec=GeometrySpec.model_validate({'dimension':2,'points':[{'name':n} for n in 'SEAFB'],
        'relations':[{'kind':'on_segment','points':['E','S','A'],'source_quote':instruction},
                     {'kind':'on_segment','points':['F','S','B'],'source_quote':instruction}]})
    admitted,audit=admit_instruction(spec,instruction)
    assert len(audit['added_relations'])==2
    correct={'S':[0,0],'A':[6,0],'B':[0,9],'E':[2,0],'F':[0,3]}
    assert all(c['pass'] for c in check_constraints(admitted,correct))
    wrong={**correct,'F':[0,4.5]}
    assert any(c['kind']=='length_ratio' and not c['pass'] for c in check_constraints(admitted,wrong))


def circles(r=12, small=5, distance=13, *, names=('O',"O'",'A','B','H'), labels=True):
    o,p,a,b,h=names
    instruction=f"Two circles ({o}; {r} cm) and ({p}; {small} cm); {o}{p} = {distance} cm."
    if labels:
        instruction+=f' Label the lengths {r} cm, {small} cm, {distance} cm.'
    def relation(kind,points):
        return {'kind':kind,'points':points,'source_quote':instruction}
    # Deliberately incomplete extractor output: no dimensions or metric labels.
    spec=GeometrySpec.model_validate({'dimension':2,'points':[{'name':n} for n in names],
        'relations':[relation('reflection',[b,a,o,p]),relation('intersection',[h,a,b,o,p]),
                     relation('noncollinear',[o,p,a])],
        'draw':[{'kind':kind,'points':points} for kind,points in
                [('circle',[o,a]),('circle',[p,a]),('segment',[o,p]),('segment',[o,a]),('segment',[p,a]),('segment',[a,b])]]})
    return spec,instruction


@pytest.mark.parametrize('r,small,distance,names',[
    (12,5,13,('O',"O'",'A','B','H')),
    (5,4,6,('U','V','C','D','K')),
    (4,3,5,('P1','P2','Q1','Q2','M')),
])
def test_source_dimensions_and_carrier_labels_survive_incomplete_extraction(r,small,distance,names):
    spec,instruction=circles(r,small,distance,names=names)
    original=spec.model_dump_json()
    source,evidence=realize_spec(spec,instruction,candidates=4)
    assert spec.model_dump_json()==original
    points={n:np.array(evidence['witness']['world_points'][internal]) for n,internal in evidence['identifier_map'].items()}
    o,p,a,b,_h=(points[n] for n in names)
    assert np.linalg.norm(o-a)/np.linalg.norm(p-a)==pytest.approx(r/small,rel=1e-7)
    assert np.linalg.norm(o-p)/np.linalg.norm(o-a)==pytest.approx(distance/r,rel=1e-7)
    assert np.linalg.norm(o-b)==pytest.approx(np.linalg.norm(o-a),rel=1e-7)
    assert np.linalg.norm(p-b)==pytest.approx(np.linalg.norm(p-a),rel=1e-7)
    factor=evidence['metric_frame']['source_units_per_drawing_unit']
    assert np.linalg.norm(o-a)*factor==pytest.approx(r)
    for value,(start,end) in [(r,(names[0],names[2])),(small,(names[1],names[2])),(distance,(names[0],names[1]))]:
        i,j=evidence['identifier_map'][start],evidence['identifier_map'][end]
        assert rf'\path ({i})--node[midway,sloped,above,fill=white,inner sep=1pt] {{${value}\,\mathrm{{cm}}$}} ({j});' in source
    assert len(evidence['instruction_audit']['added_relations'])==3
    assert len(evidence['instruction_audit']['added_labels'])==3


def test_numeric_values_cannot_be_replaced_by_perpendicularity_or_quotes():
    spec,instruction=circles()
    admitted,_=admit_instruction(spec,instruction)
    wrong={'O':[0,0],"O'":[5,0],'A':[3.2,2.4],'B':[3.2,-2.4],'H':[3.2,0]}
    # A valid 3:4:5 pair of perpendicular radii does not establish 12:5:13.
    failures=[c for c in check_constraints(admitted,wrong) if not c['pass']]
    assert any(c['kind']=='length' for c in failures)


def test_model_metric_conflict_and_false_label_rejected():
    spec,instruction=circles()
    spec.relations.append(Relation(kind='length',points=['O','A'],values=[7],unit='cm',source_quote=instruction))
    with pytest.raises(SpecError,match='source_conflict'):
        realize_spec(spec,instruction,candidates=1)
    spec,instruction=circles()
    data=spec.model_dump()
    data['length_labels']=[{'points':['O','A'],'value':7,'unit':'cm','source_quote':instruction}]
    with pytest.raises(SpecError,match='Metric label must match'):
        realize_spec(GeometrySpec.model_validate(data),instruction,candidates=1)


def test_given_values_are_displayed_without_inventing_explicit_requests():
    spec,instruction=circles(labels=False)
    source,evidence=realize_spec(spec,instruction,candidates=1)
    assert not evidence['spec']['length_labels']
    assert all(value in source for value in (r'12\,\mathrm{cm}',r'5\,\mathrm{cm}',r'13\,\mathrm{cm}'))
    assert len(evidence['witness']['metric_marks'])==3


def test_units_convert_before_comparison_and_no_endpoint_can_disappear():
    spec,instruction=circles()
    instruction=instruction.replace('12 cm','120 mm')
    for relation in spec.relations:relation.source_quote=instruction
    source,evidence=realize_spec(spec,instruction,candidates=1)
    p={n:np.array(evidence['witness']['world_points'][i]) for n,i in evidence['identifier_map'].items()}
    assert np.linalg.norm(p['O']-p['A'])/np.linalg.norm(p["O'"]-p['A'])==pytest.approx(12/5,rel=1e-7)
    assert r'120\,\mathrm{mm}' in source
    spec.points=[p for p in spec.points if p.name!="O'"]
    with pytest.raises(SpecError,match='Unknown'):
        realize_spec(spec,instruction,candidates=1)


def test_numeric_labels_require_the_correct_drawn_carriers():
    spec,instruction=circles()
    spec.draw=[d for d in spec.draw if not(d.kind=='segment' and d.points==['O','A'])]
    with pytest.raises(SpecError,match='no drawn carrier'):
        realize_spec(spec,instruction,candidates=1)


@pytest.mark.parametrize('instruction',[
    'Trong không gian có mặt cầu (S) tâm O bán kính 1; OB=√3. Biểu diễn mặt cầu.',
    'Draw a sphere with center O and radius 1.',
    'AB=sqrt(a) cm.',
    'Prove AB=5 cm.',
])
def test_unsupported_source_stops_before_model_and_compile(instruction,tmp_path,monkeypatch):
    class NoModel:
        def with_structured_output(self,*args,**kwargs):
            raise AssertionError('Unsupported instruction reached model')
    def no_compile(*args,**kwargs):
        raise AssertionError('Unsupported instruction reached compiler')
    monkeypatch.setattr(workflow.render_tikz,'func',no_compile)
    with pytest.raises(SpecError,match='unsupported_instruction'):
        workflow.draw_spec_first(instruction=instruction,model=NoModel(),artifact_dir=tmp_path,compiler_http=None)
    stages=json.loads((tmp_path/'stages.json').read_text())
    assert stages['failure_stage']=='instruction_preflight' and stages['extraction_calls']==0
    assert not (tmp_path/'precompile.tikz').exists()


def test_dimension_mismatch_and_model_unsupported_excerpts_stop_without_render():
    spec,instruction=circles(labels=False)
    with pytest.raises(SpecError,match='dimension_mismatch'):
        realize_spec(spec,instruction+' A tetrahedron is required.',candidates=1)
    spec.unsupported=['sphere']
    with pytest.raises(SpecError,match='unsupported_instruction'):
        realize_spec(spec,instruction,candidates=1)


def test_supported_numeric_partitions_and_symbolic_circle_radii_are_admitted():
    scan=scan_instruction('AI = 3IG; BP=2DP. Circles (B; BA) and (D; DA).')
    assert not scan['issues']
    assert [r['kind'] for r in scan['obligations']]==['radius_segment','radius_segment','length_ratio','length_ratio']
    assert [r['value'] for r in scan['obligations'][-2:]]==[3,2]


@pytest.mark.parametrize('expression',[
    '2*AB/CD=1/3', '-AB/CD=1/3', 'AB/CD + EF/GH = 1/3',
    'AB/CD/EF=1/3', '2\u00d7AB/CD=1/3', '\u2212AB/CD=1/3',
    'AB/CD \u00b7 EF/GH=1/3', r'2\cdot AB/CD=1/3',
    '(AB) EF/GH=1/3', 'AB/CD EF/GH=1/3', '2 AB/CD=1/3',
    r'\frac{1}{2} AB/CD=1/3',
])
def test_fraction_reader_cannot_admit_a_suffix_of_an_unsupported_expression(expression):
    scan=scan_instruction(expression+'.')
    assert scan['issues']
    assert not scan['obligations']


@pytest.mark.parametrize('expression',['AB/CD=1,5.','AB/CD=1/3,5.','AB/CD=1/3, 5.'])
def test_fraction_reader_cannot_truncate_decimal_commas(expression):
    scan=scan_instruction(expression)
    assert scan['issues']
    assert not scan['obligations']


def test_comma_can_separate_two_complete_fraction_assignments():
    scan=scan_instruction('AB/CD=1/3, EF/GH=2/3.')
    assert not scan['issues']
    assert [r['value'] for r in scan['obligations']]==pytest.approx([1/3,2/3])


def test_less_than_branch_is_executable_not_merely_quoted():
    spec,instruction=circles(labels=False)
    instruction+=' OA < O\'A.'
    for r in spec.relations:r.source_quote=instruction
    with pytest.raises(SpecError,match='search_exhausted'):
        realize_spec(spec,instruction,candidates=1)


@pytest.mark.parametrize('expression',['-5 cm','sqrt(a) cm','a+1 cm','5e0 cm','O5'])
def test_unsupported_annotation_cannot_hide_behind_embedded_digits(expression):
    scan=scan_instruction(f'AB=5 cm. Label the length {expression}.')
    assert any(i['category']=='unsupported_annotation' for i in scan['issues'])
    assert not scan['annotations']


def test_decimal_annotation_and_requested_display_units_are_preserved():
    scan=scan_instruction('AB=2.5 cm. Label the length 25 mm.')
    assert not scan['issues']
    assert scan['annotations'][0]['quantities']==[{'value':25,'unit':'mm'}]
    spec,instruction=circles()
    instruction=instruction.replace('Label the lengths 12 cm','Label the lengths 120 mm')
    for r in spec.relations:r.source_quote=instruction
    admitted,_=admit_instruction(spec,instruction)
    label=next(l for l in admitted.length_labels if l.points==['O','A'])
    assert label.value==120 and label.unit=='mm'


@pytest.mark.parametrize('connector',['and','AND','và'])
def test_conjoined_assignments_have_separate_complete_source_spans(connector):
    text=f'PQ=a {connector} RS=a/3. UV=WX {connector} angle UVX is right.'
    scan=scan_instruction(text)
    assert not scan['issues']
    assert [(r['kind'],r['points']) for r in scan['obligations']]==[
        ('length',['P','Q']),('length',['R','S']),('length_ratio',['U','V','W','X'])]
    assert [r.get('expression') for r in scan['obligations'][:2]]==['a','a/3']
    assert all(text[s:e]==r['quote'] for r in scan['obligations'] for s,e in [r['span']])


def test_conjunction_does_not_truncate_bad_math_or_hide_bad_left_hand_side():
    for text,bad_points in (('PQ=2+ and RS=3.',['P','Q']), ('PQ=2 and 2*RS=3.',['R','S']), ('[P,QR,S]=120°+30° and PQ=2.',['P','Q','R','S'])):
        scan=scan_instruction(text)
        assert scan['issues']
        assert not any(r['points']==bad_points for r in scan['obligations'])


def test_prose_annotation_is_retained_as_unverified_instead_of_a_numeric_error():
    scan=scan_instruction('PQ=a và RS=a/3. Ghi nhãn các điểm và thể hiện các độ dài đã cho cùng các quan hệ vuông góc.')
    assert not scan['issues'] and len(scan['obligations'])==2
    assert not scan['annotations'] and len(scan['unparsed_annotations'])==1
    assert scan_instruction('Label the given lengths.')['coverage'].startswith('Explicit notation only')
    for expression in ('sqrt(a)','sin(a)','-5 cm','O5'):
        assert scan_instruction(f'Label the length {expression}.')['issues']


def test_angle_and_ratio_notation_share_conjunction_boundaries():
    scan=scan_instruction('PQ/RS=1/3 and TU/VW=2/3. ∠PQR=60° và [P,QR,S]=120°.')
    assert not scan['issues']
    assert sorted(r['kind'] for r in scan['obligations'])==['angle','dihedral_angle','length_ratio','length_ratio']
