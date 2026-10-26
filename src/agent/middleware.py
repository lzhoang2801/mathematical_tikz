"""Shared native middleware for caller-owned execution lifetime checks."""

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelRequest, ToolCallRequest


class ExecutionCheckMiddleware(AgentMiddleware):
    """Stop synchronous model/tool loops when their owning request has ended."""

    def __init__(self, check: Callable[[], None]) -> None:
        """Reuse the owning request cancellation/deadline check."""
        self.check = check

    def wrap_model_call(self, request: ModelRequest, handler: Any) -> Any:
        """Check the request before a model call and before accepting its result."""
        self.check()
        result = handler(request)
        self.check()
        return result

    def wrap_tool_call(self, request: ToolCallRequest, handler: Any) -> Any:
        """Check the request before a tool call and before accepting its result."""
        self.check()
        result = handler(request)
        self.check()
        return result
