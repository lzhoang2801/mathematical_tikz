"""Regression checks for bounded pilot accounting and infrastructure failures."""
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parents[2] / 'src')]

import httpx
import pytest

from tools.spec_first import run_construction_pilot as runner


@pytest.mark.parametrize('failure', ['unavailable', 'changed_toolchain', 'connection'])
def test_compiler_loss_after_startup_stops_before_model_invocation(tmp_path, monkeypatch, failure):
    output = tmp_path / 'runs' / 'pilot'
    job = {'case': 'fixture', 'arm': 'native', 'repetition': 1, 'key': 'fixture-1-native'}
    protocol = {'code_sha256': {}, 'data_sha256': {}, 'model': 'fixture', 'model_settings': {},
                'compiler_url': 'http://compiler', 'compiler_readiness': {'toolchain': 'pinned'},
                'maximum_model_calls': 4, 'order': [job], 'method': 'spec_first'}
    runner.save(output / 'protocol.json', protocol)
    runner.save(output / 'calibration.json', {'fixture:target': {'pass': True}})
    runner.save(output / 'references/fixture/original-record.json', {'target_tikz': 'calibration only'})
    runner.save(output / 'inputs.json', [{'case': 'fixture', 'instruction': 'fixture'}])
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'code_hashes', dict)
    monkeypatch.setattr(runner, 'frozen_data_hashes', lambda output: {})
    monkeypatch.setattr(runner, 'model_settings', lambda model: {})
    monkeypatch.setattr(runner, 'build_model', lambda **kwargs: SimpleNamespace(model_name='fixture'))
    monkeypatch.setattr(runner, 'construction_pilot_cases', SimpleNamespace(CASES=['fixture'], calibration_variants=lambda *args: {'target': None}))
    monkeypatch.setattr(runner.harness, 'build_tikz_agent', lambda *args, **kwargs: object())
    def unexpected_model_call(**kwargs):
        pytest.fail('An unavailable compiler must stop the next paid drawing call')
    monkeypatch.setattr(runner.harness, 'draw_tikz', unexpected_model_call)
    monkeypatch.setenv('LANGSMITH_API_KEY', 'unit-test-only')
    monkeypatch.setenv('LANGSMITH_PROJECT', 'unit-test-only')
    closed = []
    monkeypatch.setattr(runner, 'Client', lambda: SimpleNamespace(flush=lambda: None, close=lambda: closed.append(True)))
    monkeypatch.setattr(runner, 'wait_for_all_tracers', lambda: None)
    requests = []
    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, json=protocol['compiler_readiness'])
        if failure == 'connection':
            raise httpx.ConnectError('Compiler stopped', request=request)
        return httpx.Response(503 if failure == 'unavailable' else 200, json={'toolchain': 'changed'})
    client_type = httpx.Client
    monkeypatch.setattr(runner.httpx, 'Client', lambda **kwargs: client_type(transport=httpx.MockTransport(respond), **kwargs))
    runner.draw(output, 'http://compiler')
    assert len(requests) == 2 and closed == [True]
    assert runner.read(output / 'infrastructure-stop.json')['next_job'] == job
    assert not (output / 'drawings').exists()
    with pytest.raises(RuntimeError, match='Infrastructure-stopped'):
        runner.draw(output, 'http://compiler')
    assert len(requests) == 2


def test_undelivered_output_is_unavailable_not_false_mathematics(tmp_path):
    directory = tmp_path / 'drawings/fixture-1-native'
    runner.save(directory / 'attempt.json', {'error': 'compiler unavailable'})
    runner.evaluate_outputs(tmp_path, 'http://must-not-be-called')
    result = runner.read(directory / 'evaluation.json')
    assert result['status'] == 'unavailable'
    assert result['mathematics_pass'] is None and result['geometry_content_pass'] is None


def test_comparison_completeness_uses_frozen_order_and_handles_unknown_scores(tmp_path):
    jobs = [{'case': 'fixture', 'arm': arm, 'repetition': 1, 'key': f'fixture-1-{arm}'} for arm in ('native', 'spec_first')]
    runner.save(tmp_path / 'protocol.json', {'method': 'spec_first', 'order': jobs})
    for job in jobs:
        folder = tmp_path / 'drawings' / job['key']
        runner.save(folder / 'attempt.json', {**job, 'seconds': 1, 'model_calls': 1, 'compile_calls': 0, 'model_seconds': 1, 'compile_seconds': 0})
        runner.save(folder / 'evaluation.json', {'status': 'unavailable', 'mathematics_pass': None, 'geometry_content_pass': None})
    runner.summarize(tmp_path)
    summary = runner.read(tmp_path / 'summary.json')
    assert summary['comparison_complete'] and summary['complete_pairs'] == ['fixture-1']
    assert all(row['mathematics_pass'] == 0 and row['geometry_content_pass'] == 0 for row in summary['arms'].values())


def test_manifest_hashes_pin_inputs_checks_and_initial_worker_freeze(tmp_path):
    runner.save(tmp_path / 'inputs.json', [])
    runner.save(tmp_path / 'manifest.json', {'cases': []})
    runner.save(tmp_path / 'worker-freeze.json', {'files': {}})
    checker = tmp_path / 'checks' / 'source.py'
    checker.parent.mkdir()
    checker.write_text('VERSION = 1', encoding='utf-8')
    before = runner.frozen_data_hashes(tmp_path)
    checker.write_text('VERSION = 2', encoding='utf-8')
    after = runner.frozen_data_hashes(tmp_path)
    assert before.keys() == after.keys()
    assert before['checks/source.py'] != after['checks/source.py']
    assert 'manifest.json' in before and 'worker-freeze.json' in before


@pytest.mark.parametrize('change', ['empty', 'failed', 'missing', 'worker'])
def test_manifest_rejects_incomplete_calibration_or_changed_worker_before_model_call(tmp_path, monkeypatch, change):
    worker = tmp_path / 'worker.py'
    worker.write_text('frozen', encoding='utf-8')
    runner.save(tmp_path / 'worker-freeze.json', {'files': {'worker.py': runner.hashlib.sha256(worker.read_bytes()).hexdigest()}})
    runner.save(tmp_path / 'protocol.json', {'code_sha256': {}, 'data_sha256': {}, 'case_manifest': 'manifest.json',
                                           'order': [{'case': 'new', 'repetition': 1, 'arm': arm, 'key': arm} for arm in ('native', 'spec_first')],
                                           'calibration_keys': [] if change == 'empty' else ['new:valid', 'new:mutation']})
    calibration = {'new:valid': {'pass': True}, 'new:mutation': {'pass': change != 'failed'}}
    if change == 'missing':
        calibration.pop('new:mutation')
    if change == 'worker':
        worker.write_text('changed', encoding='utf-8')
    runner.save(tmp_path / 'calibration.json', calibration)
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'code_hashes', dict)
    monkeypatch.setattr(runner, 'frozen_data_hashes', lambda output: {})
    monkeypatch.setattr(runner, 'build_model', lambda **kwargs: pytest.fail('Must reject before any provider setup'))
    with pytest.raises(RuntimeError, match='worker changed' if change == 'worker' else 'calibration'):
        runner.draw(tmp_path, 'http://unused', 'mixed')


@pytest.mark.parametrize('outcome, expected', [('unknown', None), ('failure', False)])
def test_compiler_unavailable_and_invalid_tex_have_different_truth_status(tmp_path, monkeypatch, outcome, expected):
    directory = tmp_path / 'drawings/new-1-native'
    runner.save(directory / 'attempt.json', {'case': 'new', 'key': 'new-1-native', 'result': {'tikz': 'drawing'}})
    runner.save(tmp_path / 'calibration/new/target/observations.json', {})
    runner.save(tmp_path / 'protocol.json', {'case_manifest': 'manifest.json'})
    monkeypatch.setattr(runner, 'compile_observe', lambda *args, **kwargs: {'compile_success': False, 'compile': {'outcome': outcome}, 'image_path': None})
    monkeypatch.setattr(runner, '_score_observations', lambda *args: {'compilation': None})
    runner.evaluate_outputs(tmp_path, 'http://unused', 'mixed')
    result = runner.read(directory / 'evaluation.json')
    assert result['mathematics_pass'] is expected
    assert result['geometry_content_pass'] is expected


def test_completeness_uses_manifest_job_keys(tmp_path):
    order = [{'case': 'new', 'arm': arm, 'repetition': 1, 'key': key}
             for arm, key in [('native', 'opaque-a'), ('spec_first', 'opaque-b')]]
    runner.save(tmp_path / 'protocol.json', {'method': 'spec_first', 'order': order})
    for job in order:
        directory = tmp_path / 'drawings' / job['key']
        runner.save(directory / 'attempt.json', {**job, 'seconds': 1, 'model_calls': 1, 'compile_calls': 0, 'model_seconds': 1, 'compile_seconds': 0})
        runner.save(directory / 'evaluation.json', {'status': 'unavailable', 'mathematics_pass': None, 'geometry_content_pass': None})
    runner.summarize(tmp_path, 'mixed')
    result = runner.read(tmp_path / 'summary.json')
    assert result['comparison_complete'] and not result['missing_jobs']
    assert all(row['mathematics_unavailable'] == 1 for row in result['arms'].values())


@pytest.mark.parametrize('invalid', ['duplicate_key', 'duplicate_identity', 'missing_arm'])
def test_manifest_rejects_ambiguous_job_identity(tmp_path, monkeypatch, invalid):
    jobs = [{'case': 'new', 'repetition': 1, 'arm': arm, 'key': arm} for arm in ('native', 'spec_first')]
    if invalid == 'duplicate_key':
        jobs[1]['key'] = jobs[0]['key']
    elif invalid == 'duplicate_identity':
        jobs[1]['arm'] = jobs[0]['arm']
    else:
        jobs.pop()
    runner.save(tmp_path / 'protocol.json', {'case_manifest': 'manifest.json', 'order': jobs, 'code_sha256': {}, 'data_sha256': {}})
    monkeypatch.setattr(runner, 'code_hashes', dict)
    monkeypatch.setattr(runner, 'frozen_data_hashes', lambda output: {})
    with pytest.raises(ValueError, match='unique paired'):
        runner.draw(tmp_path, 'http://unused', 'mixed')
