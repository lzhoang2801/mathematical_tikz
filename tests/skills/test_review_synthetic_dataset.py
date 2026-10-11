"""Review decisions use temporary snapshots and local request doubles only."""
from __future__ import annotations

import hashlib
import http.client
import json
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest
from PIL import Image

from tools import review_synthetic_dataset as reviewer
from tools import run_synthetic_dataset as production


def _row(identifier: str, task: str = "Generate", **updates) -> dict:
    row = {
        "schema_version": "synthetic-tikz:v2",
        "id": identifier,
        "task": task,
        "instruction": f"Draw {identifier}.",
        "current_tikz": None,
        "target_tikz": rf"\begin{{tikzpicture}}\coordinate (A) at ({identifier[-1:]},0);\end{{tikzpicture}}",
        "source": "temporary source",
        "source_group": "temporary family",
        "split": None,
        "grade": 8,
        "diagram_types": ["G03"],
        "provenance": {"parents": ["temporary-source"]},
        "verification": {"status": "candidate", "reviewed_by": None},
        "success": True,
    }
    row.update(updates)
    return row


def _output(tmp_path: Path, generated: list[dict], edits: list[dict] | None = None) -> Path:
    output = tmp_path / "synthetic"
    output.mkdir()
    for name, rows in (("generate", generated), ("edit", edits or [])):
        (output / f"{name}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
        )
        (output / f"{name}.parquet").write_bytes(b"old snapshot")
    (output / "report.json").write_text('{"preserved": true}', encoding="utf-8")
    return output


def _exports(monkeypatch, events: list[tuple]):
    write_rows = production.write_rows
    save_json = reviewer.drawing.save_json

    def record_rows(path: Path, rows: list[dict]) -> None:
        events.append((path.name, [row["id"] for row in rows]))
        write_rows(path, rows)

    def record_parquet(rows: list[dict], path: Path) -> None:
        events.append((path.name, [row["id"] for row in rows]))
        path.write_bytes(json.dumps([row["id"] for row in rows]).encode())

    def record_json(path: Path, value: object) -> None:
        events.append((path.name, None))
        save_json(path, value)

    def record_review(output: Path, rows: list[dict], latest: dict[str, dict]) -> None:
        events.append(("review.html", [row["id"] for row in rows]))
        (output / "review.html").write_text("review refreshed", encoding="utf-8")

    monkeypatch.setattr(reviewer, "production", production)
    monkeypatch.setattr(production, "write_rows", record_rows)
    monkeypatch.setattr(reviewer.drawing, "write_parquet", record_parquet)
    monkeypatch.setattr(reviewer.drawing, "save_json", record_json)
    monkeypatch.setattr(production, "write_review", record_review)


def test_delete_archives_full_rows_first_and_removes_only_selected_ids(tmp_path, monkeypatch):
    base = _row("base-1")
    unrelated = _row("keep-2", provenance={"parents": ["other-source"]})
    edit = _row("edit-1", "Edit", current_tikz=base["target_tikz"],
                provenance={"parents": ["temporary-source"], "starting_record_id": base["id"]})
    output = _output(tmp_path, [base, unrelated], [edit])
    (output / "state.json").write_text(json.dumps({"source_hashes": {"temporary-source": "hash", "other-source": "hash"}}), encoding="utf-8")
    review = reviewer.Review(output)
    events: list[tuple] = []
    _exports(monkeypatch, events)

    review.delete([base["id"]], review.revision)

    archived = [json.loads(line) for line in (output / "excluded.jsonl").read_text(encoding="utf-8").splitlines()]
    assert archived == [base]
    assert [row["id"] for row in production.drawing.load_rows(output / "generate.jsonl")] == [unrelated["id"]]
    assert [row["id"] for row in production.drawing.load_rows(output / "edit.jsonl")] == [edit["id"]]
    assert json.loads((output / "report.json").read_text(encoding="utf-8"))["completed_candidates"] == {
        "Generate": 1, "Edit": 1
    }
    coverage = json.loads((output / "report.json").read_text(encoding="utf-8"))["source_coverage"]
    assert coverage["missing"] == {"Generate": ["temporary-source"], "Edit": ["other-source"]}
    names = [name for name, _ in events]
    assert names == ["excluded.jsonl", "generate.jsonl", "generate.parquet", "edit.jsonl",
                     "edit.parquet", "report.json", "review.html"]
    assert (output / "generate.parquet").read_bytes() == b'["keep-2"]'
    assert (output / "edit.parquet").read_bytes() == b'["edit-1"]'


def test_restart_replays_archived_exclusion_after_export_interruption(tmp_path, monkeypatch):
    removed, kept = _row("remove-1"), _row("keep-1")
    output = _output(tmp_path, [removed, kept])
    review = reviewer.Review(output)
    events: list[tuple] = []
    _exports(monkeypatch, events)
    original_parquet = reviewer.drawing.write_parquet
    failed = False

    def fail_once(rows: list[dict], path: Path) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("simulated interrupted export")
        original_parquet(rows, path)

    monkeypatch.setattr(reviewer.drawing, "write_parquet", fail_once)
    with pytest.raises(OSError, match="interrupted"):
        review.delete([removed["id"]], review.revision)

    assert [json.loads(line) for line in (output / "excluded.jsonl").read_text(encoding="utf-8").splitlines()] == [removed]
    monkeypatch.setattr(reviewer.drawing, "write_parquet", original_parquet)
    restarted = reviewer.Review(output)

    assert set(restarted.rows) == {kept["id"]}
    assert [row["id"] for row in production.drawing.load_rows(output / "generate.jsonl")] == [kept["id"]]
    assert [json.loads(line) for line in (output / "excluded.jsonl").read_text(encoding="utf-8").splitlines()] == [removed]


def test_stale_revision_and_unknown_ids_leave_snapshots_unchanged(tmp_path, monkeypatch):
    first, second = _row("first-1"), _row("second-2")
    output = _output(tmp_path, [first, second])
    review = reviewer.Review(output)
    stale_revision = review.revision
    (output / "generate.jsonl").write_text(json.dumps({**first, "instruction": "updated"}) + "\n"
                                               + json.dumps(second) + "\n", encoding="utf-8")
    current = {name: (output / name).read_bytes() for name in ("generate.jsonl", "edit.jsonl", "report.json")}
    events: list[tuple] = []
    _exports(monkeypatch, events)

    with pytest.raises(RuntimeError, match="Reload"):
        review.delete([first["id"]], stale_revision)
    assert not events
    assert {name: (output / name).read_bytes() for name in current} == current
    revision = review.revision
    with pytest.raises(ValueError, match="existing candidate IDs"):
        review.delete([first["id"], "missing-id"], revision)
    assert not events
    assert not (output / "excluded.jsonl").exists()
    assert {name: (output / name).read_bytes() for name in current} == current


@contextmanager
def _server(review):
    server = reviewer.make_server(review, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(server, method: str, path: str, headers: dict[str, str] | None = None, body: bytes | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    request_headers = {"Host": f"127.0.0.1:{server.server_port}"}
    request_headers.update(headers or {})
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    result = response.status, response.read()
    connection.close()
    return result


@pytest.mark.parametrize('endpoint', ['/api/delete', '/api/reconstruct'])
def test_http_rejects_foreign_origin_host_token_and_traversal(tmp_path, endpoint):
    row = _row("safe-1")
    review = reviewer.Review(_output(tmp_path, [row]))
    with _server(review) as server:
        origin = f"http://127.0.0.1:{server.server_port}"
        payload = json.dumps({"ids": [row["id"]], "revision": review.revision}).encode()
        assert _request(server, "GET", "/api/rows", {"Host": "attacker.example"})[0] == 403
        assert _request(server, "GET", "/api/rows", {"Sec-Fetch-Site": "cross-site"})[0] == 403
        assert _request(server, "POST", endpoint, {
            "Origin": "https://attacker.example", "X-Review-Token": review.token,
            "Content-Type": "application/json",
        }, payload)[0] == 403
        assert _request(server, "POST", endpoint, {
            "Origin": origin, "X-Review-Token": "wrong-token", "Content-Type": "application/json",
        }, payload)[0] == 403
        assert _request(server, "POST", endpoint, {
            "Host": "attacker.example", "Origin": origin, "X-Review-Token": review.token,
            "Content-Type": "application/json",
        }, payload)[0] == 403
        assert _request(server, "GET", "/api/row?id=..%2F..%2Fetc%2Fpasswd")[0] == 404
        assert _request(server, "GET", "/image?id=%2Fetc%2Fpasswd")[0] == 404
    assert set(review.rows) == {row["id"]}
    assert not (review.output / "excluded.jsonl").exists()


def test_previews_require_exact_edit_base_and_target_image_bindings(tmp_path):
    base_tikz = r"\begin{tikzpicture}\coordinate (A) at (0,0);\end{tikzpicture}"
    target_tikz = r"\begin{tikzpicture}\coordinate (A) at (1,0);\end{tikzpicture}"
    base_png = tmp_path / "base.png"
    target_png = tmp_path / "target.png"
    Image.new("RGB", (4, 4), "white").save(base_png)
    Image.new("RGB", (4, 4), "black").save(target_png)

    def rendered(row: dict, tikz: str, image: Path) -> dict:
        return {**row, "rendered_tikz_sha256": hashlib.sha256(tikz.encode()).hexdigest(),
                "rendered_png_path": str(image),
                "rendered_png_sha256": hashlib.sha256(image.read_bytes()).hexdigest()}

    base = rendered(_row("base-1", target_tikz=base_tikz), base_tikz, base_png)
    edit = rendered(_row("edit-1", "Edit", current_tikz=base_tikz, target_tikz=target_tikz,
                         provenance={"starting_record_id": base["id"]}), target_tikz, target_png)
    output = _output(tmp_path, [base], [edit])
    drawings = output / "drawings" / "cases" / base["id"]
    drawings.mkdir(parents=True)
    reviewer.drawing.save_json(drawings / "candidate.json", base)
    review = reviewer.Review(output)

    assert review.preview(edit, before=True)["bytes"] == base_png.read_bytes()
    assert review.preview({**edit, "current_tikz": target_tikz}, before=True) is None
    assert review.preview(edit, before=False)["bytes"] == target_png.read_bytes()
    mismatched_target = {**edit, "rendered_tikz_sha256": hashlib.sha256(base_tikz.encode()).hexdigest()}
    assert review.preview(mismatched_target, before=False) is None


def _rendered(tmp_path: Path, row: dict) -> dict:
    image = tmp_path / (row['id'] + '.png')
    Image.new('RGB', (4, 4), 'white').save(image)
    return {**row, 'rendered_png_path': str(image),
            'rendered_png_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
            'rendered_tikz_sha256': hashlib.sha256(row['target_tikz'].encode()).hexdigest()}


def test_move_deduplicates_exact_pairs_preserves_lineage_and_refreshes_hf(tmp_path):
    import pyarrow.parquet as pq

    from tools.export_hf_dataset import export

    generate = _rendered(tmp_path, _row('generate-1', split='test', evaluation_rubric={'stale': True}))
    edit = _rendered(tmp_path, _row('edit-1', 'Edit', current_tikz='starting code',
        source_group='another family', provenance={'parents': ['another-source']}))
    kept = _rendered(tmp_path, _row('keep-2', source_group='another family'))
    output = _output(tmp_path, [generate, kept], [edit])
    (output / 'hf').mkdir()
    review = reviewer.Review(output)

    assert review.move_to_reconstruct([generate['id'], generate['id']], review.revision) == {'moved': 1, 'added': 1}
    assert review.move_to_reconstruct([edit['id']], review.revision) == {'moved': 1, 'added': 0}
    assert set(review.rows) == {kept['id']}
    assert len(review.reconstructed) == 1
    row = next(iter(review.reconstructed.values()))
    assert row['task'] == 'Reconstruct' and row['current_tikz'] is None
    assert row['instruction'] not in (generate['instruction'], edit['instruction'])
    assert 'evaluation_rubric' not in row
    assert row['target_tikz'] == generate['target_tikz'] == edit['target_tikz']
    assert row['split'] == 'test'
    assert set(row['provenance']['moved_from']) == {generate['id'], edit['id']}
    assert set(row['provenance']['parents']) == {'temporary-source', 'another-source'}
    assert set(row['provenance']['source_groups']) == {'temporary family', 'another family'}
    assert row['verification']['original_instruction_match'] is False
    assert row['verification']['reviewed_input_sha256'] == reviewer.drawing.review_digest(row)
    assert sorted(review.excluded) == sorted([generate['id'], edit['id']])
    assert review.excluded[generate['id']] == generate
    assert review.excluded[edit['id']] == edit
    original_bytes = Path(generate['rendered_png_path']).read_bytes()
    assert reviewer.drawing.source_image(row)['bytes'] == original_bytes
    assert reviewer.drawing.target_image(row)['bytes'] == original_bytes
    table = pq.read_table(output / 'reconstruct/candidates.parquet').to_pylist()
    assert table[0]['image']['bytes'] == table[0]['tikz_image']['bytes'] == original_bytes
    assert table[0]['target_tikz'] == generate['target_tikz']
    assert pq.read_table(output / 'hf/reconstruct/test.parquet').num_rows == 1
    assert pq.read_table(output / 'hf/generate/test.parquet').num_rows == 1
    assert pq.read_table(output / 'hf/edit/test.parquet').num_rows == 0
    restarted = reviewer.Review(output)
    assert restarted.reconstructed == review.reconstructed
    assert set(restarted.rows) == {kept['id']}

    Path(generate['rendered_png_path']).unlink()
    assert reviewer.drawing.source_image(row)['bytes'] == original_bytes
    Path(row['image']['path']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='exact image/target binding'):
        export(None, output, output / 'hf')


def test_move_validates_entire_selection_and_reconstruct_revision_before_writing(tmp_path):
    first = _rendered(tmp_path, _row('first-1'))
    second = _rendered(tmp_path, _row('second-2'))
    second['rendered_tikz_sha256'] = 'wrong'
    output = _output(tmp_path, [first, second])
    review = reviewer.Review(output)
    before = (output / 'generate.jsonl').read_bytes()
    with pytest.raises(ValueError, match='verified target preview'):
        review.move_to_reconstruct([first['id'], second['id']], review.revision)
    assert not (output / 'reconstruct').exists()
    assert not (output / 'excluded.jsonl').exists()
    assert (output / 'generate.jsonl').read_bytes() == before
    old_revision = review.revision
    (output / 'reconstruct').mkdir()
    (output / 'reconstruct/candidates.jsonl').write_text('\n', encoding='utf-8')
    with pytest.raises(RuntimeError, match='Reload'):
        review.move_to_reconstruct([first['id']], old_revision)
    assert (output / 'generate.jsonl').read_bytes() == before


def test_move_replays_after_committed_export_failure(tmp_path, monkeypatch):
    row = _rendered(tmp_path, _row('move-1'))
    output = _output(tmp_path, [row])
    review = reviewer.Review(output)
    original_parquet = reviewer.drawing.write_parquet

    def interrupted(rows, path):
        raise OSError('interrupted export')

    monkeypatch.setattr(reviewer.drawing, 'write_parquet', interrupted)
    with pytest.raises(OSError, match='interrupted'):
        review.move_to_reconstruct([row['id']], review.revision)
    assert (output / 'reconstruct/moves.jsonl').is_file()
    monkeypatch.setattr(reviewer.drawing, 'write_parquet', original_parquet)
    restarted = reviewer.Review(output)
    assert not restarted.rows
    assert restarted.excluded[row['id']] == row
    assert len(restarted.reconstructed) == len(restarted.moves) == 1
    assert (output / 'generate.jsonl').read_bytes() == b''
    assert (output / 'reconstruct/candidates.parquet').is_file()


def test_http_move_updates_counts_and_original_rows(tmp_path):
    row = _rendered(tmp_path, _row('move-1'))
    review = reviewer.Review(_output(tmp_path, [row]))
    with _server(review) as server:
        origin = f'http://127.0.0.1:{server.server_port}'
        payload = json.dumps({'ids': [row['id']], 'revision': review.revision}).encode()
        status, response = _request(server, 'POST', '/api/reconstruct', {
            'Origin': origin, 'X-Review-Token': review.token, 'Content-Type': 'application/json',
        }, payload)
        assert status == 200
        assert json.loads(response) == {'moved': 1, 'added': 1}
        status, response = _request(server, 'GET', '/api/rows')
        data = json.loads(response)
        assert status == 200 and not data['rows']
        assert data['excluded'] == data['reconstruct'] == data['moved'] == 1
