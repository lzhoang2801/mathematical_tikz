"""Native render and cancellation controls adapted from mathmath's drawing tests."""
import base64
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import httpx
import pytest
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import Field
from latex_compiler.schemas import Artifact, CompileRequest, CompileResponse, StageResult

from agent.latex.tikz import standalone_tikz_document
from agent.workflows import tikz as tikz_workflow
from agent.workflows.tikz import Context, render_tikz


class DrawingModel(FakeMessagesListChatModel):
    conversations: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, **kwargs):
        self.conversations.append(messages)
        return super()._generate(messages, **kwargs)


def test_native_task_entrypoints_keep_explicit_inputs(tmp_path, monkeypatch):
    from agent.workflows import geometry_tikz, problem_tikz
    from agent.schemas.tikz import TikzResult

    calls = []
    result = TikzResult(success=False, status="failed", usable=False, tikz="")
    def draw(**kwargs):
        calls.append(kwargs)
        return result
    monkeypatch.setattr(problem_tikz, "draw_tikz", draw)
    monkeypatch.setattr(geometry_tikz, "draw_tikz", draw)
    image = tmp_path / "source.png"
    image.write_bytes(b"source-image-fixture")
    current = r"\begin{tikzpicture}\end{tikzpicture}"
    assert problem_tikz.problem_tikz(
        instruction="Add H.", source_statement="AB=AC", current_tikz=current,
        reference_images=[image], artifact_dir=tmp_path, agent=object(),
    ) is result
    user = calls[-1]["messages"][1]["content"]
    assert "AB=AC" in user[0]["text"]
    assert user[1]["text"] == "Drawing instruction:\nAdd H."
    assert current in user[2]["text"] and user[3]["type"] == "image_url"
    problem_tikz.problem_tikz(instruction="Fresh input.", artifact_dir=tmp_path, agent=object())
    assert calls[-1]["messages"][1]["content"] == [
        {"type": "text", "text": "Drawing instruction:\nFresh input."}]
    assert geometry_tikz.geometry_region_to_tikz(
        image_path=image, artifact_dir=tmp_path, agent=object(),
    ) is result
    assert calls[-1]["messages"][1]["content"][1]["type"] == "image_url"
    with pytest.raises(FileNotFoundError):
        geometry_tikz.geometry_region_to_tikz(
            image_path=tmp_path / "missing.png", artifact_dir=tmp_path, agent=object())


@pytest.mark.parametrize("case", ["ok", "escaped_percent", "definition", "conditional", "definition_file", "file_input", "dynamic_name", "comment", "tex_error", "output_error"])
def test_render_tikz_returns_image_or_actionable_failure(tmp_path, case):
    tikz = r"""\begin{tikzpicture}
\coordinate (A) at (0,0);
\coordinate (B) at (4,0);
\path ($(A)!0.5!(B)$) coordinate (M);
\path[overlay] (80,80) coordinate (helper);
\draw (A)--(B);
\foreach \Point/\Ref in {A/M,B/M,M/A}
  \path let \p1=($(\Point)-(\Ref)$),
            \n1={scalar(atan2(\y1,\x1))}
    in (\Point) node[circle,fill,inner sep=1.35pt,label={\n1:$\Point$}] {};
\end{tikzpicture}"""
    if case == "definition":
        tikz = tikz.replace(r"\coordinate (A)", r"\def\R{3}" + "\n" + r"\coordinate (A)", 1)
    elif case == "conditional":
        tikz = tikz.replace(r"\draw (A)--(B);", r"\ifnum1=1\relax \draw (A)--(B);\fi", 1)
    elif case == "definition_file":
        tikz = tikz.replace(r"\coordinate (A)", r"\def\Leak{\input{external.tex}}" + "\n" + r"\coordinate (A)", 1)
    elif case == "file_input":
        tikz = tikz.replace(r"\coordinate (A)", r"\input{external.tex}" + "\n" + r"\coordinate (A)", 1)
    elif case == "dynamic_name":
        tikz = tikz.replace(r"\coordinate (A)", r"\csname A\endcsname" + "\n" + r"\coordinate (A)", 1)
    elif case == "comment":
        tikz = tikz.replace(r"\coordinate (A)", "% frame\n" + r"\coordinate (A)", 1)
    elif case == "escaped_percent":
        tikz = tikz.replace(r"\end{tikzpicture}", r"\node at (0,1) {$50\%$};" + "\n" + r"\end{tikzpicture}")
    compile_outcome = "error" if case in {"tex_error", "output_error"} else "ok"
    diagnostic = "Undefined control sequence: \\unknown" if case == "tex_error" else "TeX succeeded without a usable PDF"
    toolchain_id = "test-toolchain"
    pdf = b"%PDF-1.4\n%%EOF\n"
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/"
        "x8AAwMCAO+/2e0AAAAASUVORK5CYII="
    )
    requests = []

    def compile_once(request):
        requests.append(request)
        compile_request = CompileRequest.model_validate_json(request.content)
        response = CompileResponse(
            source_digest=compile_request.digest(toolchain_id),
            toolchain_id=toolchain_id,
            page_count=1 if compile_outcome == "ok" else None,
            compile=StageResult(
                outcome=compile_outcome,
                exit_code=1 if case == "tex_error" else 0,
                failure_code="process_exit" if case == "tex_error" else "pdf_missing" if case == "output_error" else None,
                diagnostic=diagnostic if compile_outcome == "error" else "",
            ),
            raster=StageResult(outcome="ok" if compile_outcome == "ok" else "not_run"),
            artifacts=[
                Artifact(
                    name="result.pdf",
                    complete=True,
                    data_base64=base64.b64encode(pdf).decode("ascii"),
                ),
                Artifact(
                    name="page-1.png",
                    complete=True,
                    data_base64=base64.b64encode(png).decode("ascii"),
                ),
            ] if compile_outcome == "ok" else [],
        )
        return httpx.Response(200, json=response.model_dump(mode="json"))

    with httpx.Client(
        base_url="http://compiler",
        transport=httpx.MockTransport(compile_once),
    ) as compiler_http:
        runtime = ToolRuntime(
            state={"messages": []},
            context=Context(tmp_path, compiler_http),
            config={},
            stream_writer=lambda _chunk: None,
            tool_call_id="render-call",
            store=None,
        )
        call = {
            "name": "render_tikz",
            "type": "tool_call",
            "id": "render-call",
            "args": {"tikz": tikz, "runtime": runtime},
        }
        if case == "output_error":
            with pytest.raises(RuntimeError, match="pdf_missing"):
                render_tikz.invoke(call)
        else:
            message = render_tikz.invoke(call)

    if case in {"definition_file", "file_input", "dynamic_name", "comment"}:
        assert requests == []
        assert isinstance(message, ToolMessage)
        assert message.status == "error"
        assert message.content.startswith("TikZ input rejected: ")
        expected = {
            "definition_file": (r"\input", "file access and resource loading"),
            "file_input": (r"\input", "file access and resource loading"),
            "dynamic_name": (r"\csname", "dynamic tokenization and control names"),
            "comment": ("comments", "blank lines"),
        }[case]
        assert all(part in message.content for part in expected)
        assert message.artifact is None
        return

    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].url.path == "/compile"
    sent = CompileRequest.model_validate_json(requests[0].content)
    assert sent.source == standalone_tikz_document(tikz)

    if case == "output_error":
        return

    assert isinstance(message, ToolMessage)
    if case == "tex_error":
        assert message.status == "error"
        assert message.content == f"TeX build failed (exit 1): {diagnostic}"
        assert message.artifact is None
        return

    assert message.artifact["tikz"] == tikz
    assert Path(message.artifact["rendered_png_path"]).read_bytes() == png

    assert message.status == "success"
    assert message.content == [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64.b64encode(png).decode('ascii')}"
            },
        }
    ]


@pytest.mark.parametrize("cancel_after", [None, "model", "tool"])
def test_native_drawing_stops_between_calls_when_parent_ends(tmp_path, monkeypatch, cancel_after):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    cancelled = False
    renders = []

    def check():
        if cancelled:
            raise RuntimeError("The parent request was cancelled.")

    @tool("render_tikz", response_format="content_and_artifact")
    def render(source: str):
        """Render one requested diagram."""
        nonlocal cancelled
        renders.append(source)
        cancelled = cancel_after == "tool"
        return "Rendered diagram.", {"tikz": source, "rendered_png_path": str(tmp_path / "diagram.png")}

    class Model(DrawingModel):
        def _generate(self, messages, **kwargs):
            nonlocal cancelled
            result = super()._generate(messages, **kwargs)
            cancelled = cancel_after == "model"
            return result

    source = r"\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}"
    model = Model(responses=[
        AIMessage(content="", tool_calls=[{
            "id": "draw", "name": "render_tikz", "args": {"source": source},
        }]),
        AIMessage(content='{"incomplete_reason":null}'),
    ])
    monkeypatch.setattr(tikz_workflow, "render_tikz", render)
    graph = tikz_workflow.build_tikz_agent(model, check_cancelled=check if cancel_after else None)
    if cancel_after:
        with pytest.raises(RuntimeError, match="parent request was cancelled"):
            tikz_workflow.draw_tikz(messages=[{"role": "user", "content": "Draw a line."}],
                artifact_dir=tmp_path, agent=graph, compiler_http=object())
        assert len(model.conversations) == 1
        assert len(renders) == (1 if cancel_after == "tool" else 0)
        assert not (tmp_path / "result.json").exists()
        assert not (tmp_path / "main.tex").exists()
    else:
        result = tikz_workflow.draw_tikz(messages=[{"role": "user", "content": "Draw a line."}],
            artifact_dir=tmp_path, agent=graph, compiler_http=object())
        assert result.success
        assert result.tikz == source
        assert len(model.conversations) == 2
        assert len(renders) == 1
        assert (tmp_path / "result.json").exists()

