"""Batch adapter tests use deterministic evaluator stubs, never models or a live compiler."""
import json
from unittest.mock import Mock

import pytest

from evaluation import batch


SCORES = dict(compile=1, mathematical_correctness=80.0, content_coverage=100.0, visual_readability=60.0)
ZERO = dict.fromkeys(SCORES, 0)


def prediction(task='reconstruct', index=0, **overrides):
    return dict(
        task=task, split='test', row_index=index, id='repeated-image-hash',
        target_tikz='% exact reference\n\\usetikzlibrary{calc}\nreference',
        output_tikz='prediction' + str(index), **overrides,
    )


def write_predictions(path, rows):
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def test_exact_pairs_duplicate_ids_and_error_denominators(tmp_path, monkeypatch):
    source, destination = tmp_path / 'predictions.jsonl', tmp_path / 'scores.jsonl'
    rows = [prediction(index=0), prediction(index=1), prediction('edit', 0), prediction('edit', 1)]
    write_predictions(source, rows)
    evaluator = Mock(side_effect=[SCORES, ZERO, SCORES, ValueError('Unusable reference geometry: ellipse')])
    monkeypatch.setattr(batch, 'evaluate', evaluator)

    summary = batch.evaluate_file(source, destination)

    assert evaluator.call_args_list == [
        ((row['target_tikz'], row['output_tikz']),) for row in rows
    ]
    results = read_rows(destination)
    assert len(results) == 4
    assert [row['row_index'] for row in results] == [0, 1, 0, 1]
    assert results[-1]['status'] == 'evaluation_error' and results[-1]['scores'] is None
    assert summary['status'] == 'completed_with_errors'
    assert summary['overall']['scored'] == 3
    assert summary['overall']['mean_scores']['compile'] == pytest.approx(2 / 3)
    assert summary['by_task']['reconstruct']['mean_scores']['mathematical_correctness'] == 40
    assert summary['by_task']['edit']['scored'] == 1
    assert summary['by_task']['edit']['errors'] == {'evaluation_error': 1}
    assert json.loads(destination.with_suffix('.summary.json').read_text()) == summary
    assert read_rows(source) == rows


def test_infrastructure_failure_stops_and_preserves_completed_results(tmp_path, monkeypatch):
    source, destination = tmp_path / 'predictions.jsonl', tmp_path / 'scores.jsonl'
    write_predictions(source, [prediction(index=index) for index in range(3)])
    evaluator = Mock(side_effect=[SCORES, RuntimeError('output compiler unavailable'), SCORES])
    monkeypatch.setattr(batch, 'evaluate', evaluator)

    summary = batch.evaluate_file(source, destination)

    assert evaluator.call_count == 2
    assert summary['status'] == 'incomplete'
    assert summary['processed'] == 2 and summary['pending'] == 1
    assert summary['overall']['scored'] == 1
    assert read_rows(destination)[-1]['status'] == 'infrastructure_error'


def test_invalid_records_do_not_reach_evaluator_or_become_zero_scores(tmp_path, monkeypatch):
    source, destination = tmp_path / 'predictions.jsonl', tmp_path / 'scores.jsonl'
    source.write_text(
        'not json\n[]\n{"task": []}\n{"task": "edit", "target_tikz": null, "output_tikz": ""}\n',
        encoding='utf-8',
    )
    evaluator = Mock()
    monkeypatch.setattr(batch, 'evaluate', evaluator)

    summary = batch.evaluate_file(source, destination)

    evaluator.assert_not_called()
    assert summary['overall']['scored'] == 0
    assert summary['overall']['errors'] == {'invalid_record': 4}
    assert all(value is None for value in summary['overall']['mean_scores'].values())


def test_input_and_existing_results_cannot_be_overwritten(tmp_path, monkeypatch):
    source, destination = tmp_path / 'predictions.jsonl', tmp_path / 'scores.jsonl'
    write_predictions(source, [prediction()])
    original = source.read_bytes()
    with pytest.raises(ValueError, match='different files'):
        batch.evaluate_file(source, source)
    destination.write_text('previous expensive results', encoding='utf-8')
    with pytest.raises(FileExistsError, match='preserved'):
        batch.evaluate_file(source, destination)
    assert destination.read_text() == 'previous expensive results'
    assert source.read_bytes() == original


def test_unexpected_bug_propagates_after_saving_partial_summary(tmp_path, monkeypatch):
    source, destination = tmp_path / 'predictions.jsonl', tmp_path / 'scores.jsonl'
    write_predictions(source, [prediction(index=0), prediction(index=1)])
    monkeypatch.setattr(batch, 'evaluate', Mock(side_effect=[SCORES, KeyError('bug')]))
    with pytest.raises(KeyError, match='bug'):
        batch.evaluate_file(source, destination)
    assert len(read_rows(destination)) == 1
    summary = json.loads(destination.with_suffix('.summary.json').read_text())
    assert summary['pending'] == 1 and summary['status'] == 'incomplete'


def test_cli_prints_summary_and_signals_errors(tmp_path, monkeypatch, capsys):
    source, destination = tmp_path / 'predictions.jsonl', tmp_path / 'scores.jsonl'
    write_predictions(source, [prediction()])
    monkeypatch.setattr(batch, 'evaluate', Mock(side_effect=ValueError('target_tikz does not compile')))
    monkeypatch.setattr('sys.argv', ['evaluation.batch', '--predictions', str(source), '--results', str(destination)])
    with pytest.raises(SystemExit) as error:
        batch.main()
    assert error.value.code == 1
    assert json.loads(capsys.readouterr().out)['overall']['scored'] == 0

def test_partial_results_use_a_separate_denominator_for_each_metric(tmp_path, monkeypatch):
    from evaluation.evaluator import EvaluationError
    source,destination = tmp_path/'predictions.jsonl',tmp_path/'scores.jsonl'
    write_predictions(source,[prediction(index=0),prediction(index=1)])
    partial = dict(compile=1,mathematical_correctness=None,content_coverage=None,visual_readability=100.0)
    monkeypatch.setattr(batch,'evaluate',Mock(side_effect=[SCORES,EvaluationError('unsupported reference',partial)]))
    summary = batch.evaluate_file(source,destination)
    assert read_rows(destination)[1]['scores'] == partial
    assert summary['overall']['scored'] == 1
    assert summary['overall']['scored_by_metric'] == dict(compile=2,mathematical_correctness=1,content_coverage=1,visual_readability=2)
    assert summary['overall']['mean_scores'] == dict(compile=1,mathematical_correctness=80,content_coverage=100,visual_readability=80)


def test_caller_owned_native_transport_reuses_batch_error_and_identity_handling(tmp_path, monkeypatch):
    source, destination = tmp_path / 'predictions.jsonl', tmp_path / 'scores.jsonl'
    rows = [prediction(index=0), prediction(index=1)]
    write_predictions(source, rows)
    native = Mock(side_effect=[SCORES, batch.EvaluationError('partial native evidence', {
        'compile': 1, 'mathematical_correctness': None, 'content_coverage': None, 'visual_readability': 60,
    })])
    remote = Mock(side_effect=AssertionError('Notebook must use the supplied native transport'))
    monkeypatch.setattr(batch, 'evaluate', remote)
    summary = batch.evaluate_file(source, destination, evaluator=native)
    assert native.call_args_list == [((r['target_tikz'], r['output_tikz']),) for r in rows]
    remote.assert_not_called()
    assert summary['overall']['scored_by_metric']['compile'] == 2
    assert summary['overall']['scored_by_metric']['mathematical_correctness'] == 1
    assert read_rows(destination)[1]['scores']['mathematical_correctness'] is None
