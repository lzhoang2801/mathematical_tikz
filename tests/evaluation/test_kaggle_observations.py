"""Notebook transport and persisted observations obey the native evaluator contract."""
import base64
import hashlib
import json

import httpx
import pytest
from latex_compiler.schemas import CompileRequest, Outputs
from train.evaluate import observation, worker_response


def test_worker_accepts_log_only_receipt_when_no_pdf_is_requested():
    payload=CompileRequest(source='trusted source',outputs=Outputs(pdf=False))
    raw=json.dumps({'compile':{'outcome':'ok','exit_code':0},'artifacts':[
        {'name':'result.log','data_base64':base64.b64encode(b'log').decode()}]}).encode()
    response=worker_response(payload,raw,'fixture')
    assert [a.name for a in response.artifacts]==['result.log']
    assert response.source_digest==payload.digest('fixture')
    payload.outputs.pdf=True
    with pytest.raises(ValueError,match='PDF'): worker_response(payload,raw,'fixture')


def test_old_pdf_cache_requires_a_new_run_directory(tmp_path):
    code='drawing'
    (tmp_path/'observations.json').write_text(json.dumps({'metadata':{
        'input_tikz_sha256':hashlib.sha256(code.encode()).hexdigest(),'schema_version':'tikz-observations:v4'}}))
    with httpx.Client(base_url='http://unused') as client:
        with pytest.raises(ValueError,match='schema changed'): observation(code,tmp_path,client)


def test_invalid_tikz_cache_retains_the_compile_failure(tmp_path):
    def forbidden(request):
        raise AssertionError('Invalid TikZ reached the compiler')
    with httpx.Client(base_url='http://unused',transport=httpx.MockTransport(forbidden)) as client:
        first=observation('not a TikZ picture',tmp_path,client)
        cached=observation('not a TikZ picture',tmp_path,client)
    assert cached==first
    assert cached['compile']['outcome']=='validation_failed'
    assert cached['compile_success'] is False
