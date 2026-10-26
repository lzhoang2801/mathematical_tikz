"""Pair scoring remains independent of PDFs and optional preview rendering."""
import inspect

import pytest

from evaluation.evaluator import EvaluationError, EvaluationInfrastructureError, _score_observations as score, evaluate


@pytest.mark.parametrize('options', [{'scale':1.7},{'reflection':True},{'rotation':True},
                                     {'rotation':True,'reflection':True},{'wrong_text':True}])
def test_similarity_and_text_changes_preserve_geometry(pgf_diagram, options):
    target=pgf_diagram(coordinates=[(30,100),(130,100),(30,30)])
    output=pgf_diagram(coordinates=[(30,100),(130,100),(30,30)],**options)
    assert score(target,output) == {'compile':1,'mathematical_correctness':100,'content_coverage':100,'visual_readability':100}


def test_missing_edge_and_free_proportions(pgf_diagram):
    target=pgf_diagram()
    missing=score(target,pgf_diagram(missing_edge=True))
    varied=score(target,pgf_diagram(coordinates=[(30,100),(160,100),(60,30)]))
    assert missing['mathematical_correctness']==100
    assert missing['content_coverage']==pytest.approx(500/6)
    assert varied['mathematical_correctness']==varied['content_coverage']==100


def test_readability_is_absolute(pgf_diagram):
    observed=pgf_diagram(collide=True)
    result=score(observed,observed)
    assert result['mathematical_correctness']==result['content_coverage']==100
    assert result['visual_readability']<100


def test_missing_native_box_preserves_other_scores(pgf_diagram):
    target,output=pgf_diagram(),pgf_diagram(missing_box=True)
    with pytest.raises(EvaluationError,match='readability') as failure:
        score(target,output)
    assert failure.value.scores=={'compile':1,'mathematical_correctness':100,'content_coverage':100,'visual_readability':None}


def test_missing_identity_keeps_target_denominator(pgf_diagram):
    result=score(pgf_diagram(),pgf_diagram(missing_point=True))
    assert result['mathematical_correctness']==0
    assert result['content_coverage']==50


def test_compiler_failure_and_unavailable_evidence_are_different(pgf_diagram):
    target=pgf_diagram()
    failed={'compile_success':False,'compile':{'outcome':'error'}}
    offline={'compile_success':False,'compile':{'outcome':'unknown','diagnostic':'offline'}}
    assert score(target,failed)=={'compile':0,'mathematical_correctness':0,'content_coverage':0,'visual_readability':0}
    with pytest.raises(EvaluationInfrastructureError): score(target,offline)
    with pytest.raises(EvaluationError) as failure: score(failed,target)
    assert failure.value.scores['compile']==1 and failure.value.scores['visual_readability']==100


@pytest.mark.parametrize('mutation', ['identity','radius','center','missing','style','duplicate','transform','ellipse'])
def test_circle_geometry_and_presence(pgf_diagram,mutation):
    coords=[(100,100),(140,100),(100,70)]
    target=pgf_diagram(coordinates=coords,circle='identity')
    options={'scale':1.7,'rotation':True,'reflection':True} if mutation=='transform' else {}
    output=pgf_diagram(coordinates=coords,circle=None if mutation=='missing' else mutation,**options)
    result=score(target,output)
    assert result['mathematical_correctness']==(0 if mutation in {'radius','center','missing','ellipse'} else 100)
    assert (result['content_coverage']==100)==(mutation not in {'missing','style','ellipse'})
    if mutation=='ellipse':
        with pytest.raises(EvaluationError,match='Unusable reference') as failure: score(output,target)
        assert failure.value.scores['compile']==1
        assert failure.value.scores['visual_readability'] is not None


def test_public_api_has_two_inputs_and_reuses_identical_source(pgf_diagram,monkeypatch):
    import evaluation.evaluator as evaluator
    assert list(inspect.signature(evaluate).parameters)==['target_tikz','output_tikz']
    target,output=pgf_diagram(),pgf_diagram(reflection=True)
    calls=[]
    def compile_stub(tikz,directory,compiler,*,preview=False):
        calls.append((tikz,preview))
        return {'target':target,'output':output}[tikz]
    monkeypatch.setattr(evaluator,'compile_observe',compile_stub)
    assert evaluate('target','output')==score(target,output)
    assert calls==[('target',False),('output',False)]
    calls.clear()
    assert evaluate('target','target')['mathematical_correctness']==100
    assert calls==[('target',False)]
    with pytest.raises(TypeError): evaluate({},'output')


def test_empty_geometry_does_not_manufacture_credit(pgf_records):
    empty=pgf_records([])
    assert score(empty,empty)=={'compile':1,'mathematical_correctness':0,'content_coverage':0,'visual_readability':100}


def test_missing_trace_cannot_erase_output_compile(pgf_diagram):
    target=pgf_diagram()
    output={**pgf_diagram(),'log_path':None}
    with pytest.raises(EvaluationError) as failure: score(target,output)
    assert failure.value.scores=={'compile':1,'mathematical_correctness':None,'content_coverage':None,'visual_readability':None}


def test_unmeasured_native_text_cannot_take_the_empty_label_pass(pgf_records):
    observed=pgf_records(['UNSUPPORTED|text_without_node'])
    with pytest.raises(EvaluationError,match='readability') as failure:
        score(pgf_records([]),observed)
    assert failure.value.scores['compile']==1
    assert failure.value.scores['visual_readability'] is None
