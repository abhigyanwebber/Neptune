"""Tool execution boundary.

Resolves a tool call against a registry, executes it under a bounded
timeout and output-size envelope, and always returns a normalized
ToolResult -- never a raw exception (TOOL_CONTRACT responsibility:
"return structured success/error information").

Timeout/output-size defaults are an implementation detail, not a
contract fixture -- TOOL_CONTRACT explicitly defers "timeout
defaults" and "retry semantics" to implementation.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from neptune.core.contracts.tool_execution import (
    ToolCall,
    ToolInputError,
    ToolNotFoundError,
    ToolOutcome,
    ToolRegistry,
    ToolResult,
)

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_OUTPUT_BYTES = 32_000


class ToolExecutorService:
    """Reference ToolExecutor implementation.

    No provider-specific handling anywhere in this class -- it is
    handed a ToolCall (already normalized, already attributed to a
    task/session/turn) and a registry, and knows nothing about which
    model or provider produced the call. This satisfies "no special
    handling for any provider" (task requirement).
    """

    def __init__(
        self,
        registry: ToolRegistry,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    ) -> None:
        self._registry = registry
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="neptune-tool-exec")

    def execute(self, call: ToolCall) -> ToolResult:
        start = time.perf_counter()

        try:
            tool = self._registry.get(call.tool_name)
        except ToolNotFoundError as exc:
            return self._result(call, start, ToolOutcome.NOT_FOUND, error_message=str(exc))

        future = self._pool.submit(tool.execute, call.arguments)
        try:
            output = future.result(timeout=self._timeout_seconds)
        except FutureTimeoutError:
            future.cancel()
            return self._result(
                call,
                start,
                ToolOutcome.TIMEOUT,
                error_message=f"tool '{call.tool_name}' exceeded {self._timeout_seconds}s timeout",
            )
        except ToolInputError as exc:
            return self._result(call, start, ToolOutcome.ERROR, error_message=str(exc))
        except Exception as exc:  # noqa: BLE001 -- normalized at the boundary, per TOOL_CONTRACT
            return self._result(
                call, start, ToolOutcome.ERROR, error_message=f"unhandled tool error: {exc}"
            )

        size_error = self._check_output_size(output)
        if size_error:
            return self._result(call, start, ToolOutcome.ERROR, error_message=size_error)

        return self._result(call, start, ToolOutcome.SUCCESS, output=output)

    def _check_output_size(self, output: dict) -> str | None:
        """Invariant 3: tool output must have practical size limits."""
        try:
            serialized = json.dumps(output)
        except (TypeError, ValueError) as exc:
            return f"tool output is not JSON-serializable: {exc}"
        size = len(serialized.encode("utf-8"))
        if size > self._max_output_bytes:
            return f"tool output size {size}B exceeds limit {self._max_output_bytes}B"
        return None

    def _result(
        self,
        call: ToolCall,
        start: float,
        outcome: ToolOutcome,
        output: dict | None = None,
        error_message: str | None = None,
    ) -> ToolResult:
        duration_ms = (time.perf_counter() - start) * 1000
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            outcome=outcome,
            output=output,
            error_message=error_message,
            duration_ms=duration_ms,
            task_id=call.task_id,
            session_id=call.session_id,
            turn_id=call.turn_id,
        )
