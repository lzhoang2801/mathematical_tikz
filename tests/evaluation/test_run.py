"""The CLI exposes the same two-input evaluator, without case metadata."""
import json
from contextlib import contextmanager

import pytest
from unittest.mock import Mock

from evaluation import run


def test_cli_reads_two_tikz_files_and_prints_only_scores(tmp_path, monkeypatch, capsys):
    target, output = tmp_path / 'target.tex', tmp_path / 'output.tex'
    target.write_text('target code', encoding='utf-8')
    output.write_text('output code', encoding='utf-8')
    scores = {'compile': 1, 'mathematical_correctness': 75.0, 'content_coverage': 100.0, 'visual_readability': 50.0}
    evaluator = Mock(return_value=scores)
    monkeypatch.setattr(run, 'evaluate', evaluator)
    monkeypatch.setattr('sys.argv', ['evaluation.run', '--target', str(target), '--output', str(output)])
    run.main()
    evaluator.assert_called_once_with('target code', 'output code')
    assert json.loads(capsys.readouterr().out) == scores


def test_cli_preview_reuses_the_compiled_pair(tmp_path, monkeypatch, capsys):
    target, output, preview = tmp_path / 'target.tex', tmp_path / 'output.tex', tmp_path / 'preview.html'
    target.write_text('target code', encoding='utf-8')
    output.write_text('output code', encoding='utf-8')
    events = []
    @contextmanager
    def observe_pair(first, second, **options):
        assert options["preview"]
        events.append((first, second))
        yield {'compile_success': True}, {'compile_success': False}
        assert preview.is_file()
    scores = {'compile': 0, 'mathematical_correctness': 0.0, 'content_coverage': 0.0, 'visual_readability': 0.0}
    monkeypatch.setattr(run, '_observe_pair', observe_pair)
    monkeypatch.setattr(run, '_score_observations', Mock(return_value=scores))
    evaluator = Mock(side_effect=AssertionError('Preview must not recompile through evaluate'))
    monkeypatch.setattr(run, 'evaluate', evaluator)
    monkeypatch.setattr('sys.argv', ['evaluation.run', '--target', str(target), '--output', str(output), '--preview', str(preview)])
    run.main()
    assert events == [('target code', 'output code')]
    assert json.loads(capsys.readouterr().out) == scores
    assert 'target code' in preview.read_text(encoding='utf-8')
    assert 'output code' in preview.read_text(encoding='utf-8')
    evaluator.assert_not_called()
    monkeypatch.setattr('sys.argv', ['evaluation.run', '--target', str(target), '--output', str(output), '--preview', str(output)])
    with pytest.raises(SystemExit):
        run.main()
    assert output.read_text(encoding='utf-8') == 'output code'

def test_preview_and_known_scores_survive_unsupported_reference(tmp_path, monkeypatch, capsys):
    from evaluation.evaluator import EvaluationError
    target, output, preview = tmp_path/'target.tex',tmp_path/'output.tex',tmp_path/'preview.html'
    target.write_text('target code')
    output.write_text('output code')
    partial = {'compile':1,'mathematical_correctness':None,'content_coverage':None,'visual_readability':100.0}
    @contextmanager
    def observed(*args, **kwargs):
        yield {'compile_success':True},{'compile_success':True}
        assert preview.is_file()
    monkeypatch.setattr(run,'_observe_pair',observed)
    monkeypatch.setattr(run,'_score_observations',Mock(side_effect=EvaluationError('Unsupported <curve>',partial)))
    monkeypatch.setattr('sys.argv',['evaluation.run','--target',str(target),'--output',str(output),'--preview',str(preview)])
    with pytest.raises(SystemExit) as failure:
        run.main()
    assert failure.value.code == 1
    assert json.loads(capsys.readouterr().out) == {'scores':partial,'error':'Unsupported <curve>'}
    document = preview.read_text()
    assert 'Unsupported &lt;curve&gt;' in document and 'Unavailable' in document
    assert 'target code' in document and 'output code' in document
