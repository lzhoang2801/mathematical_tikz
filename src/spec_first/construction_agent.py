"""Construction experiment tools, kept outside the native drawing agent."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException
from langgraph.graph.state import CompiledStateGraph

from agent.latex.tikz import standalone_tikz_document
from agent.prompts.tikz import TIKZ_PROMPT_VERSION
from agent.schemas.tikz import DEFAULT_TIKZ_MAX_MODEL_CALLS, TikzCompletion, TikzResult
from agent.workflows.tikz import Context, render_tikz
from spec_first.construction import Construction, realize
from spec_first.spatial_construction import SpatialConstruction, realize_spatial


@tool(description="Realize a typed planar construction, reject invalid dependencies or false marks before compiling, then return the rendered image. Submit the whole revised construction for each attempt.", response_format="content_and_artifact")
def render_construction(construction: Construction, runtime: ToolRuntime[Context]) -> tuple[list[dict[str, object]], dict[str, str]]:
    """Use deterministic construction before the existing renderer."""
    try:
        source, _ = realize(construction)
    except ValueError as error:
        raise ToolException(f"Construction rejected before compile: {error}") from error
    return render_tikz.func(source, runtime)


render_construction.handle_tool_error = True


@tool(description="Construct one closed convex solid in XYZ, select a clear parallel view, compute actual hidden segments, then compile through the existing renderer. Submit all points, cyclic boundary faces, requested segments and labels. No per-edge dash guesses.", response_format="content_and_artifact")
def render_spatial_construction(construction: SpatialConstruction, runtime: ToolRuntime[Context]) -> tuple[list[dict[str, object]], dict[str, str]]:
    """Execute a bounded spatial construction before the same native renderer."""
    try:
        source, witness = realize_spatial(construction)
    except ValueError as error:
        raise ToolException(f"Spatial construction rejected before compile: {error}") from error
    content, artifact = render_tikz.func(source, runtime)
    witness["tikz_sha256"] = hashlib.sha256(artifact["tikz"].encode()).hexdigest()
    path = Path(artifact["rendered_png_path"]).with_name("spatial-witness.json")
    path.write_text(json.dumps(witness, indent=2) + "\n", encoding="utf-8")
    artifact["spatial_witness_path"] = str(path)
    return content, artifact


render_spatial_construction.handle_tool_error = True


def build_construction_agent(
    model: BaseChatModel,
    *,
    max_model_calls: int = DEFAULT_TIKZ_MAX_MODEL_CALLS,
    spatial: bool = False,
) -> CompiledStateGraph[Any, Context, Any, Any]:
    """Build the existing bounded construction experiment with structured completion."""
    if max_model_calls < 1:
        raise ValueError("max_model_calls must be positive.")
    middleware: list[Any] = [ModelCallLimitMiddleware(run_limit=max_model_calls, exit_behavior="end")]
    return create_agent(
        model=model,
        tools=[render_spatial_construction if spatial else render_construction],
        context_schema=Context,
        middleware=middleware,
        response_format=ToolStrategy(TikzCompletion),
        name="tikz",
    ).with_config(tags=["tikz-harness"], metadata={"prompt_version": TIKZ_PROMPT_VERSION})


def draw_construction(
    *,
    messages: list[Any],
    artifact_dir: str | Path,
    agent: CompiledStateGraph[Any, Context, Any, Any],
    compiler_http: httpx.Client | None = None,
) -> TikzResult:
    """Invoke the construction agent and expose its last rendered source and image."""
    if compiler_http is None:
        raise ValueError("A compiler HTTP client is required.")
    directory = Path(artifact_dir).resolve()
    output = agent.invoke({"messages": messages}, context=Context(directory, compiler_http), config={"run_name": "tikz"})
    last_render = next((message for message in reversed(output["messages"]) if isinstance(message, ToolMessage) and message.name in {render_construction.name, render_spatial_construction.name}), None)
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
