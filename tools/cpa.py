"""Connect ChatOpenAI to CPA and verify one LangSmith-traced invocation."""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values, load_dotenv
from langchain_core.tracers.langchain import wait_for_all_tracers
from langchain_openai import ChatOpenAI
from langsmith import Client, tracing_context

ROOT = Path(__file__).resolve().parents[1]


def build_model(*, timeout: float = 60, max_tokens: int | None = None) -> ChatOpenAI:
    """Build the configured CPA model for injection into the existing harness."""
    load_dotenv(ROOT / ".env")
    inherited = dotenv_values(ROOT.parent / "mathmath/.env")
    for key, value in inherited.items():
        if key.startswith("LANGSMITH_") and value:
            os.environ.setdefault(key, value)
    for key in ("CPA_API_KEY", "CPA_BASE_URL", "CPA_MODEL"):
        if not os.environ.get(key):
            raise RuntimeError(f"Missing {key} in problem_tikz/.env or the process environment")
    return ChatOpenAI(
        base_url=os.environ["CPA_BASE_URL"],
        api_key=os.environ["CPA_API_KEY"],
        model=os.environ["CPA_MODEL"],
        use_responses_api=False,
        timeout=timeout,
        max_tokens=max_tokens,
        max_retries=0,
    )


def main() -> None:
    model = build_model()
    if not os.environ.get("LANGSMITH_API_KEY") or not os.environ.get("LANGSMITH_PROJECT"):
        raise RuntimeError("LANGSMITH_API_KEY and LANGSMITH_PROJECT are required for the traced check")
    client = Client()
    run_id = uuid4()
    with tracing_context(enabled=True, client=client, project_name=os.environ["LANGSMITH_PROJECT"]):
        response = model.invoke(
            "Reply exactly: CPA connection OK",
            config={"run_id": run_id, "run_name": "CPA connectivity",
                    "tags": ["cpa", "connectivity"], "metadata": {"requested_model": model.model_name}},
        )
    wait_for_all_tracers()
    client.flush()
    run = client.read_run(run_id)
    result = {"requested_model": model.model_name, "response": response.content,
              "response_model": response.response_metadata.get("model_name"),
              "usage": response.usage_metadata, "trace_id": str(run_id),
              "trace_url": client.get_run_url(run=run), "trace_error": run.error}
    output = ROOT / "runs/cpa-connectivity" / str(run_id)
    output.mkdir(parents=True)
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    client.close()


if __name__ == "__main__":
    main()
