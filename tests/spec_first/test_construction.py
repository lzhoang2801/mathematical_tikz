"""Meaningful geometry, trust-boundary and native-loop regression checks."""
import base64
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx
from langchain_core.tools import ToolException
from pydantic import ValidationError
import pytest

from spec_first.construction import Construction, realize
from agent.latex.tikz import validate_tikz, standalone_tikz_document
from spec_first.prompts.construction import construction_messages
from agent.prompts.problem_tikz import problem_tikz_messages
from spec_first import construction_agent as harness
from latex_compiler.schemas import Artifact, CompileRequest, CompileResponse, StageResult
from tools.spec_first.construction_pilot_cases import requirements
from evaluation.requirements import check_relations
from tools.spec_first.run_construction_pilot import MeasuredCompiler, Recorder


def plan(**changes):
    value = {"points": [
        {"name": "A", "op": "free", "values": [0, 0]},
        {"name": "B", "op": "free", "values": [4, 0]},
        {"name": "P", "op": "free", "values": [1, 3]},
        {"name": "H", "op": "project", "refs": ["P", "A", "B"]},
        {"name": "C", "op": "reflect", "refs": ["P", "A", "B"]},
        {"name": "O", "op": "lerp", "refs": ["A", "B"], "values": [0.5]},
        {"name": "R", "op": "rotate", "refs": ["A", "B"], "values": [90]},
        {"name": "X", "op": "intersect", "refs": ["P", "C", "A", "B"]}],
        "segments": [{"a": "A", "b": "B"}, {"a": "P", "b": "H"}],
        "angles": [{"a": "A", "vertex": "H", "b": "P", "kind": "right"}],
        "labels": [{"point": name, "text": name, "position": "below"} for name in ("A", "B", "P", "H")]}
    value.update(changes)
    return Construction.model_validate(value)


def test_operations_keep_named_dependencies_and_geometric_truth():
    source, points = realize(plan())
    assert points["H"] == pytest.approx((1, 0))
    assert points["C"] == pytest.approx((1, -3))
    assert points["O"] == pytest.approx((2, 0))
    assert points["R"] == pytest.approx((0, 4))
    assert points["X"] == pytest.approx((1, 0))
    assert r"$(A)!(P)!(B)$" in source
    assert r"$(A)!0.5!(B)$" in source
    assert "intersection of P--C and A--B" in source
    assert validate_tikz(source) == source


@pytest.mark.parametrize("mutation,match", [
    (lambda p: p.points[3].refs.__setitem__(0, "Later"), "forward"),
    (lambda p: setattr(p.points[1], "name", "A"), "Duplicate"),
    (lambda p: setattr(p.points[1], "values", [0, 0]), "Degenerate"),
    (lambda p: setattr(p.points[-1], "refs", ["A", "B", "H", "O"]), "Parallel"),
    (lambda p: setattr(p.angles[0], "vertex", "B"), "False right"),
    (lambda p: setattr(p.segments[0], "ticks", 1), "equality class"),
])
def test_invalid_construction_never_calls_compiler(tmp_path, mutation, match):
    value = plan()
    mutation(value)
    requests = []
    with httpx.Client(transport=httpx.MockTransport(lambda request: requests.append(request))) as client:
        runtime = SimpleNamespace(context=harness.Context(tmp_path, client))
        with pytest.raises(ToolException, match=match):
            harness.render_construction.func(value, runtime)
    assert not requests


@pytest.mark.parametrize("field,value", [("values", [float("inf"), 0]), ("name", "A);\\input{x}")])
def test_untrusted_values_are_validated(field, value):
    data = plan().model_dump()
    data["points"][0][field] = value
    with pytest.raises(ValidationError):
        Construction.model_validate(data)


def test_method_override_preserves_identical_user_input_and_baseline_prompt():
    native = problem_tikz_messages("Opaque instruction")
    construction = construction_messages("Opaque instruction")
    assert native[1] == construction[1]
    assert "render_tikz" in native[0]["content"]
    assert "render_tikz" not in construction[0]["content"]
    assert "target_tikz" not in str(construction)


@pytest.mark.parametrize("construction", [False, True])
def test_both_tools_use_exact_same_compiler_and_wrapper(tmp_path, construction):
    requests = []
    source, _ = realize(plan())
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/2e0AAAAASUVORK5CYII=")
    def respond(request):
        payload = CompileRequest.model_validate_json(request.content)
        requests.append(payload)
        response = CompileResponse(source_digest=payload.digest("test-toolchain"), toolchain_id="test-toolchain", page_count=1,
            compile=StageResult(outcome="ok", exit_code=0), raster=StageResult(outcome="ok"),
            artifacts=[Artifact(name="page-1.png", complete=True, data_base64=base64.b64encode(png).decode())])
        return httpx.Response(200, json=response.model_dump())
    with httpx.Client(base_url="http://compiler", transport=httpx.MockTransport(respond)) as http:
        runtime = SimpleNamespace(context=harness.Context(tmp_path, http))
        tool = harness.render_construction if construction else harness.render_tikz
        content, artifact = tool.func(plan() if construction else source, runtime)
    assert len(requests) == 1
    assert requests[0].source == standalone_tikz_document(source)
    assert artifact["tikz"] == source
    assert Path(artifact["rendered_png_path"]).read_bytes() == png
    assert content[0]["type"] == "image_url"


def test_compile_count_includes_http_failure_and_budget_is_enforced(tmp_path):
    with MeasuredCompiler(tmp_path, limit=1, base_url="http://compiler",
                          transport=httpx.MockTransport(lambda request: httpx.Response(503))) as http:
        with pytest.raises(httpx.HTTPStatusError), http.stream("POST", "/compile", json={"source": "fixture"}) as response:
            response.raise_for_status()
        assert len(http.records) == 1 and http.records[0]["status"] == 503
        assert http.records[0]["seconds"] is not None
        with pytest.raises(RuntimeError, match="budget"), http.stream("POST", "/compile", json={}):
            pass
        assert len(http.records) == 1


def test_independent_math_checks_accept_similarity_and_reject_wrong_midpoint():
    good = {"A": [0, 0], "B": [4, 0], "O": [2, 0], "M": [2, 3]}
    for points in (good, {name: [-3 * y + 4, 3 * x - 2] for name, (x, y) in good.items()}):
        assert all(check["status"] == "pass" for check in check_relations(requirements("isosceles"), points))
    bad = {**good, "O": [1.5, 0]}
    assert any(check["id"] == "midpoint:O-A-B" and check["status"] == "fail"
               for check in check_relations(requirements("isosceles"), bad))


def test_model_error_retained_without_counting_synthetic_budget_messages(tmp_path):
    recorder = Recorder(tmp_path)
    recorder.on_chat_model_start({}, [], run_id="call")
    recorder.on_llm_error(TimeoutError("fixture"), run_id="call")
    assert len(recorder.calls) == 1
    assert recorder.calls[0]["error"] == "TimeoutError: fixture"


def test_schema_and_runtime_tool_failures_are_counted(tmp_path):
    recorder = Recorder(tmp_path)
    recorder.on_tool_start({"name": "render_construction"}, "{}", run_id="tool")
    recorder.on_tool_error(ValueError("invalid schema"), run_id="tool")
    assert len(recorder.tool_events) == 1
    assert recorder.tool_events[0]["status"] == "error"
    assert recorder.tool_events[0]["name"] == "render_construction"


def test_relocated_construction_loop_delivers_its_render(tmp_path, monkeypatch):
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage

    class Model(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    source, _ = realize(plan())
    monkeypatch.setattr(harness.render_construction, "func", lambda **kwargs: (
        [], {"tikz": source, "rendered_png_path": str(tmp_path / "diagram.png")}))
    model = Model(responses=[
        AIMessage(content="", tool_calls=[{
            "id": "draw", "name": "render_construction", "args": {"construction": plan().model_dump()}}]),
        AIMessage(content="", tool_calls=[{
            "id": "complete", "name": "TikzCompletion", "args": {"incomplete_reason": None}}]),
    ])
    result = harness.draw_construction(
        messages=construction_messages("fixture"), artifact_dir=tmp_path,
        agent=harness.build_construction_agent(model, max_model_calls=2), compiler_http=object())
    assert result.success and result.tikz == source
    assert (tmp_path / "main.tex").read_text(encoding="utf-8") == standalone_tikz_document(source)
