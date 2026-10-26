"""One native drawing agent with a compiler-backed image tool."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain.agents.structured_output import ProviderStrategy
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException
from langgraph.graph.state import CompiledStateGraph
from latex_compiler.client import compile
from latex_compiler.schemas import CompileRequest, Images, Outputs

from agent.latex.tikz import standalone_tikz_document, validate_tikz
from agent.middleware import ExecutionCheckMiddleware
from agent.prompts.tikz import RENDER_TIKZ_DESCRIPTION, TIKZ_PROMPT_VERSION
from agent.schemas.tikz import (
    DEFAULT_TIKZ_MAX_MODEL_CALLS,
    TikzCompletion,
    TikzResult,
)
from agent.utils.media import image_content_block


@dataclass(frozen=True)
class Context:
    """Provide the compiler and image output directory for this invocation."""

    artifact_dir: Path
    compiler_http: httpx.Client


@tool(description=RENDER_TIKZ_DESCRIPTION, response_format="content_and_artifact")
def render_tikz(tikz: str, runtime: ToolRuntime[Context]) -> tuple[list[dict[str, object]], dict[str, str]]:
    """Compile the submitted TikZ and return its rendered image."""
    try:
        tikz = validate_tikz(tikz)
    except ValueError as error:
        raise ToolException(f"TikZ input rejected: {error}") from error
    response = compile(runtime.context.compiler_http, CompileRequest(source=standalone_tikz_document(tikz), outputs=Outputs(pdf=False, images=Images())))
    if response.compile.outcome == "error" and response.compile.failure_code == "process_exit":
        diagnostic = response.compile.diagnostic or "No compiler diagnostic was returned."
        raise ToolException(f"TeX build failed (exit {response.compile.exit_code}): {diagnostic}")
    if "timeout" in {response.compile.outcome, response.raster.outcome}:
        raise TimeoutError("Rendering timed out.")
    if not response.compile.success or not response.raster.success:
        failed = response.compile if not response.compile.success else response.raster
        raise RuntimeError(f"Rendering execution failed ({failed.failure_code or failed.outcome}): {failed.diagnostic}")
    image = next(artifact.data for artifact in response.artifacts if artifact.name == "page-1.png")
    path = runtime.context.artifact_dir / uuid4().hex / "diagram.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image)
    return [image_content_block(image)], {"tikz": tikz, "rendered_png_path": str(path)}


render_tikz.handle_tool_error = True


def build_tikz_agent(
    model: BaseChatModel,
    *,
    max_model_calls: int = DEFAULT_TIKZ_MAX_MODEL_CALLS,
    check_cancelled: Callable[[], None] | None = None,
) -> CompiledStateGraph[Any, Context, Any, Any]:
    """Build the bounded native model/tool loop with structured completion."""
    if max_model_calls < 1:
        raise ValueError("max_model_calls must be positive.")
    middleware: list[Any] = [ModelCallLimitMiddleware(run_limit=max_model_calls, exit_behavior="end")]
    if check_cancelled is not None:
        middleware.insert(0, ExecutionCheckMiddleware(check_cancelled))
    return create_agent(
        model=model,
        tools=[render_tikz],
        context_schema=Context,
        middleware=middleware,
        response_format=ProviderStrategy(TikzCompletion),
        name="tikz",
    ).with_config(tags=["tikz-harness"], metadata={"prompt_version": TIKZ_PROMPT_VERSION})


def draw_tikz(
    *,
    messages: list[Any],
    artifact_dir: str | Path,
    agent: CompiledStateGraph[Any, Context, Any, Any],
    compiler_http: httpx.Client | None = None,
) -> TikzResult:
    """Invoke the native agent and expose its last rendered source and image."""
    if compiler_http is None:
        raise ValueError("A compiler HTTP client is required.")
    directory = Path(artifact_dir).resolve()
    output = agent.invoke({"messages": messages}, context=Context(directory, compiler_http), config={"run_name": "tikz"})
    last_render = next((message for message in reversed(output["messages"]) if isinstance(message, ToolMessage) and message.name == render_tikz.name), None)
    artifact = last_render.artifact if last_render and last_render.status == "success" and isinstance(last_render.artifact, dict) else None
    completion = output.get("structured_response")
    success = bool(artifact and isinstance(completion, TikzCompletion) and completion.incomplete_reason is None)
    reason = completion.incomplete_reason if isinstance(completion, TikzCompletion) else "Drawing did not complete."
    issues = [] if success else [reason or "No rendered image."]
    result = TikzResult(
        success=success,
        status="accepted" if success else "usable_with_issues" if artifact else "failed",
        usable=artifact is not None,
        tikz=artifact["tikz"] if artifact else "",
        rendered_png_path=artifact["rendered_png_path"] if artifact else None,
        unresolved_issues=issues,
    )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "messages.jsonl").write_text("\n".join(message.model_dump_json() for message in output["messages"]), encoding="utf-8")
    if result.tikz:
        (directory / "main.tex").write_bytes(standalone_tikz_document(result.tikz).encode("utf-8"))
    (directory / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
