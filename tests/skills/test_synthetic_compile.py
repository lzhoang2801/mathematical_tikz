import base64
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest
from latex_compiler.schemas import CompileRequest, StageResult

SCRIPT = Path(__file__).resolve().parents[2] / ".agents/skills/synthetic-tikz/scripts/compile.py"
SPEC = importlib.util.spec_from_file_location("synthetic_tikz_compile", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
compile_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = compile_module
SPEC.loader.exec_module(compile_module)

TOOLCHAIN = "test-toolchain-v1"
TIKZ_A = r"\begin{tikzpicture}\coordinate (A) at (0,0);\end{tikzpicture}"
TIKZ_B = r"\begin{tikzpicture}\coordinate (B) at (1,0);\end{tikzpicture}"
PDF = b"%PDF-1.4 test PDF bytes"
PNG = b"\x89PNG\r\n\x1a\n test PNG bytes"


def _artifact(name: str, data: bytes) -> dict:
    return {"name": name, "complete": True, "data_base64": base64.b64encode(data).decode("ascii")}


def _compiler(failures: dict[str, str] | None = None):
    sources, failures = [], failures or {}

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/readyz":
            return httpx.Response(200, json={"toolchain_id": TOOLCHAIN})
        assert request.url.path == "/compile"
        typed = CompileRequest.model_validate_json(request.content)
        sources.append(typed.source)
        mode = next((value for marker, value in failures.items() if marker in typed.source), None)
        if mode == "unavailable":
            return httpx.Response(503, json={"detail": "compiler offline"})
        compiled, raster = StageResult(outcome="ok", exit_code=0), StageResult(outcome="ok", exit_code=0)
        artifacts = [_artifact("result.log", b"log"), _artifact("result.pdf", PDF), _artifact("page-1.png", PNG)]
        if mode == "compile_failed":
            compiled, raster = StageResult(outcome="error", exit_code=1, failure_code="process_exit", diagnostic="Undefined control sequence"), StageResult(outcome="not_run")
            artifacts = [_artifact("result.log", b"Undefined control sequence")]
        elif mode == "render_failed":
            raster = StageResult(outcome="error", failure_code="renderer_error", diagnostic="renderer unavailable")
            artifacts = artifacts[:2]
        return httpx.Response(200, json={"source_digest": typed.digest(TOOLCHAIN), "toolchain_id": TOOLCHAIN,
            "page_count": 1, "compile": compiled.model_dump(), "raster": raster.model_dump(), "artifacts": artifacts})

    return sources, httpx.Client(base_url="http://compiler.test", transport=httpx.MockTransport(handle))


def _candidate(case_id: str, task: str, target: str, current: str | None = None):
    return {"id": case_id, "task": task, "instruction": f"Givens for {case_id}.",
            "current_tikz": current, "target_tikz": target, "source_group": f"source-{case_id}",
            "provenance": {"source_path": f"source/{case_id}.tex"}}


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _run(tmp_path: Path, rows: list[dict], compiler: httpx.Client):
    source = tmp_path / "candidates.jsonl"
    _write_jsonl(source, rows)
    return source, tmp_path / "run", compile_module.compile_batch(source, tmp_path / "run", compiler)


def test_success_artifacts_edit_dedup_and_provenance(tmp_path: Path):
    rows = [_candidate("gen-1", "Generate", TIKZ_A), _candidate("edit-1", "Edit", TIKZ_B, TIKZ_A)]
    source = tmp_path / "candidates.jsonl"
    _write_jsonl(source, rows)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    calls, compiler = _compiler()
    with compiler:
        result = compile_module.compile_batch(source, tmp_path / "run", compiler)
    assert len(calls) == 2 and result["counts"] == {"needs_review": 2}
    enriched = [json.loads(line) for line in Path(result["candidates_path"]).read_text(encoding="utf-8").splitlines()]
    assert [row["provenance"]["source_path"] for row in enriched] == [
        row["provenance"]["source_path"] for row in rows
    ]
    assert all(row["provenance"]["harness_profile"] for row in enriched)
    assert all(row["verification"]["status"] == "candidate" and row["verification"]["reviewed_by"] is None for row in enriched)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    report = json.loads(Path(result["results"][1]["report_path"]).read_text(encoding="utf-8"))
    assert report["target"]["compile"]["outcome"] == report["current"]["raster"]["outcome"] == "ok"
    for role in ("target", "current"):
        record = report[role]
        assert len(record["input_tikz_sha256"]) == 64 and record["artifacts"]["result.pdf"]["complete"]
        for artifact in record["artifacts"].values():
            content = Path(artifact["path"]).read_bytes()
            assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
            assert len(content) == artifact["size_bytes"]


def test_invalid_wrapper_is_reported_without_compiler_call(tmp_path: Path):
    calls, compiler = _compiler()
    with compiler:
        _, _, result = _run(tmp_path, [_candidate("invalid", "Generate", r"\documentclass{article}\begin{document}x\end{document}")], compiler)
    assert calls == []
    assert result["results"][0]["status"] == "validation_failed"


@pytest.mark.parametrize(
    ("failure", "expected"),
    [("compile_failed", "compile_failed"), ("unavailable", "unavailable")],
)
def test_compile_error_and_transport_failure_are_distinguished(tmp_path: Path, failure: str, expected: str):
    marker = "FAILCOMPILE" if failure == "compile_failed" else "UNAVAILABLE"
    tikz = rf"\begin{{tikzpicture}}\node {{{marker}}};\end{{tikzpicture}}"
    calls, compiler = _compiler({marker: failure})
    with compiler:
        _, _, result = _run(tmp_path, [_candidate(failure, "Generate", tikz)], compiler)
    assert len(calls) == 1
    assert result["results"][0]["status"] == expected
    report = json.loads(Path(result["results"][0]["report_path"]).read_text(encoding="utf-8"))
    assert report["target"]["compile"]["outcome"] == ("error" if failure == "compile_failed" else "not_run")
    if failure == "compile_failed":
        assert "result.log" in report["target"]["artifacts"]
        assert "result.pdf" not in report["target"]["artifacts"]


def test_raster_failure_keeps_compiled_pdf_but_does_not_approve_candidate(
    tmp_path: Path,
):
    calls, compiler = _compiler({"FAILRASTER": "render_failed"})
    tikz = r"\begin{tikzpicture}\node {FAILRASTER};\end{tikzpicture}"
    with compiler:
        _, _, result = _run(tmp_path, [_candidate("raster", "Generate", tikz)], compiler)
    assert result["results"][0]["status"] == "render_failed"
    enriched = json.loads(Path(result["candidates_path"]).read_text(encoding="utf-8"))
    assert enriched["verification"]["status"] == "candidate"
    report = json.loads(Path(result["results"][0]["report_path"]).read_text(encoding="utf-8"))
    artifacts = report["target"]["artifacts"]
    assert artifacts["result.pdf"]["complete"] is True
    assert "page-1.png" not in artifacts
    assert Path(artifacts["result.pdf"]["path"]).read_bytes() == PDF
    assert len(calls) == 1


@pytest.mark.parametrize("rows", [[_candidate("dup", "Generate", TIKZ_A), _candidate("dup", "Generate", TIKZ_B)],
                                  [_candidate("edit-no-current", "Edit", TIKZ_B)],
                                  [{**_candidate("bad-task", "Generate", TIKZ_A), "task": []}]])
def test_invalid_batch_is_rejected_before_compile(tmp_path: Path, rows: list[dict]):
    calls, compiler = _compiler()
    source = tmp_path / "candidates.jsonl"
    _write_jsonl(source, rows)
    with compiler, pytest.raises(ValueError):
        compile_module.compile_batch(source, tmp_path / "run", compiler)
    assert calls == []


def test_existing_output_directory_is_preserved(tmp_path: Path):
    calls, compiler = _compiler()
    source = tmp_path / "candidates.jsonl"
    _write_jsonl(source, [_candidate("one", "Generate", TIKZ_A)])
    output = tmp_path / "run"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("existing", encoding="utf-8")
    with compiler, pytest.raises(FileExistsError):
        compile_module.compile_batch(source, output, compiler)
    assert sentinel.read_text(encoding="utf-8") == "existing"
    assert calls == []
