"""Native trace integrity, attachment identity and the shared compiler boundary."""
import base64
from pathlib import Path

import httpx
import pytest
from latex_compiler.schemas import CompileRequest

from evaluation.tikz_observations import compile_observe, read_scene
from evaluation.tikz_pgf import normalize_text, parse_trace
from conftest import label_records

TIKZ=r'\begin{tikzpicture}\draw (0,0)--(1,0);\end{tikzpicture}'


def test_visible_labels_own_identity_not_internal_coordinate_names(pgf_records):
    rows=label_records(1,'A',(5,8))
    rows+=label_records(2,'A',(900,900),text='',visible=False)
    rows+=label_records(3,'B',(20,8))
    observed=read_scene(pgf_records(rows))
    assert observed['points']=={'A':(5,8),'B':(20,8)}
    assert not observed['unresolved']
    ambiguous=read_scene(pgf_records(rows+label_records(4,'A',(80,80))))
    assert ambiguous['points']['A'] is None and ambiguous['unresolved']==['A']


def test_system_transform_is_applied_once_to_attachment_and_text(pgf_records):
    rows=['beginscope','transformcm|0|2|-2|0|10pt|20pt',*label_records(1,'A',(3,5)), 'endscope',
          *label_records(2,'B',(3,5))]
    scene=read_scene(pgf_records(rows))
    assert scene['points']=={'A':(0,26),'B':(3,5)}
    assert scene['text'][0]['boxes'][0]['corners'][0]==(12,22)
    assert [label['size'] for label in scene['text']]==[16,8]


@pytest.mark.parametrize('text,expected', [(r'$A^{\prime}$',"A'"),(r'$A_1$','A1'),(r'$60^{\circ}$','60\u00b0'),(r'$\mathrm{B}$','B')])
def test_simple_executed_text_normalization(text,expected):
    assert normalize_text(text)==expected


@pytest.mark.parametrize('damage', ['missing_done','unknown','nonfinite','scope','missing_node','truncated'])
def test_incomplete_or_malformed_trace_is_not_silently_accepted(pgf_records,damage):
    obs=pgf_records(label_records(1,'A',(0,0)))
    raw=Path(obs['log_path']).read_text()
    if damage=='missing_done': raw=raw.replace('PGFEVAL|DONE|ENDPGFEVAL','')
    if damage=='unknown': raw=raw.replace('PGFEVAL|DONE', 'PGFEVAL|unrecognized|ENDPGFEVAL\nPGFEVAL|DONE')
    if damage=='nonfinite': raw=raw.replace('|0pt|0pt','|nanpt|0pt',1)
    if damage=='scope': raw=raw.replace('PGFEVAL|DONE','PGFEVAL|beginscope|ENDPGFEVAL\nPGFEVAL|DONE')
    if damage=='missing_node': raw='\n'.join(line for line in raw.splitlines() if not line.startswith('PGFEVAL|ATTACH|'))
    if damage=='truncated': raw=raw.replace('PGFEVAL|DONE','PGFEVAL|TRUNCATED|ENDPGFEVAL\nPGFEVAL|DONE')
    with pytest.raises(ValueError): parse_trace(raw)


def test_log_wrapping_and_changed_artifacts(pgf_records):
    obs=pgf_records(label_records(1,'A',(0,0)))
    path=Path(obs['log_path']); raw=path.read_text()
    wrapped='\n'.join(raw[i:i+67] for i in range(0,len(raw),67))
    assert parse_trace(wrapped)['nodes'][0]['text']=='$A$'
    path.write_text(raw+'changed')
    with pytest.raises(ValueError,match='changed'): read_scene(obs)
    obs['metadata']['schema_version']='tikz-observations:v4'
    with pytest.raises(ValueError,match='Obsolete'): read_scene(obs)


@pytest.mark.parametrize('preview',[False,True])
def test_one_compile_without_pdf_observation(tmp_path,pgf_records,preview):
    fixture=pgf_records(label_records(1,'A',(0,0)))
    raw=Path(fixture['log_path']).read_bytes()
    calls=[]
    def handle(request):
        payload=CompileRequest.model_validate_json(request.content);calls.append(payload)
        assert payload.outputs.pdf is False
        assert bool(payload.outputs.images)==preview
        assert 'pgf_trace.tex' in payload.support_files
        artifacts=[{'name':'result.log','data_base64':base64.b64encode(raw).decode()}]
        if preview: artifacts.append({'name':'page-1.png','data_base64':base64.b64encode(b'preview-only').decode()})
        return httpx.Response(200,json={'toolchain_id':'fixture','source_digest':payload.digest('fixture'),
            'compile':{'outcome':'ok','exit_code':0},'raster':{'outcome':'ok' if preview else 'not_requested'},
            'page_count':1,'artifacts':artifacts})
    with httpx.Client(base_url='http://compiler',transport=httpx.MockTransport(handle)) as client:
        observation=compile_observe(TIKZ,tmp_path/'compiled',client,preview=preview)
    assert len(calls)==1
    assert bool(observation['image_path'])==preview
    assert read_scene(observation)['points']=={'A':(0,0)}
    assert not list((tmp_path/'compiled').glob('*.pdf'))


def test_instrumentation_failure_is_checked_against_original_compile(tmp_path):
    calls=[]
    def handle(request):
        payload=CompileRequest.model_validate_json(request.content);calls.append(payload)
        return httpx.Response(200,json={'toolchain_id':'fixture','source_digest':payload.digest('fixture'),
            'compile':{'outcome':'error' if payload.support_files else 'ok','exit_code':1 if payload.support_files else 0}})
    with httpx.Client(base_url='http://compiler',transport=httpx.MockTransport(handle)) as client:
        observed=compile_observe(TIKZ,tmp_path/'failed-hook',client)
    assert len(calls)==2 and observed['compile_success']
    with pytest.raises(ValueError,match='log unavailable'): read_scene(observed)


@pytest.mark.parametrize('source',[r'\input{secret}',r'\begin{tikzpicture}\write18{bad}\end{tikzpicture}',
                                   r'\begin{tikzpicture}^^61\end{tikzpicture}'])
def test_source_validation_precedes_instrumentation(tmp_path,source):
    def forbidden(request): raise AssertionError('Unsafe source reached compiler')
    with httpx.Client(base_url='http://compiler',transport=httpx.MockTransport(forbidden)) as client:
        result=compile_observe(source,tmp_path/'invalid',client)
    assert result['compile']['outcome']=='validation_failed'


def test_comments_and_shared_libraries_remain_accepted(tmp_path,pgf_records):
    raw=Path(pgf_records([])['log_path']).read_bytes()
    def handle(request):
        payload=CompileRequest.model_validate_json(request.content)
        assert '% source comment' in payload.source
        return httpx.Response(200,json={'toolchain_id':'fixture','source_digest':payload.digest('fixture'),
            'compile':{'outcome':'ok','exit_code':0},'artifacts':[{'name':'result.log','data_base64':base64.b64encode(raw).decode()}]})
    with httpx.Client(base_url='http://compiler',transport=httpx.MockTransport(handle)) as client:
        assert compile_observe('\\usetikzlibrary{calc}\n% source comment\n'+TIKZ,tmp_path/'comments',client)['compile_success']


def test_tracer_revision_is_part_of_observation_identity(pgf_records):
    observed=pgf_records([])
    observed['metadata']['tracer_sha256']='0'*64
    with pytest.raises(ValueError,match='tracer changed'):
        read_scene(observed)



def test_shipout_order_is_required_and_distinct_from_construction_order(pgf_records):
    observation=pgf_records(['ORDER|11','rect|0pt|0pt|10pt|10pt',
                             'ORDER|12','fill','ORDER|13','fill@opacity|0'])
    raw=Path(observation['log_path']).read_text()
    with pytest.raises(ValueError,match='shipout'):
        parse_trace(raw)
    ordered=raw+'PGFORDER|13|ENDPGFORDER\nPGFORDER|11|ENDPGFORDER\nPGFORDER|12|ENDPGFORDER\nPGFORDER|DONE|ENDPGFORDER'
    assert parse_trace(ordered)['paths'][0]['fill_opacity']==0
    with pytest.raises(ValueError,match='ambiguous paint occurrences'):
        parse_trace(ordered.replace('PGFORDER|DONE','PGFORDER|11|ENDPGFORDER\nPGFORDER|DONE'))
