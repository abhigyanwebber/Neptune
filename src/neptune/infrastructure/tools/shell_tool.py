"""Shell/command execution tool, scoped to an explicit workspace cwd
(B-010).

Not sandboxed (SANDBOX_CONTRACT.md is frozen/unimplemented; explicitly
out of scope for this task -- see 06_REGISTRIES/data/tools.yaml's own
"terminal" entry, risk_class R3, depends_on: [docker], acknowledging
real isolation is future work). The only boundary this tool enforces
is: commands always run with cwd fixed to the workspace root -- there
is no argument that can change that, so a command cannot "cd" its way
into operating outside the workspace as its starting point (it can
still affect files outside the workspace via absolute paths inside
the command string itself, exactly the risk 07_SECURITY/01_THREAT_MODEL.md
names as "destructive shell commands" and explicitly assigns to a
future policy/permission/sandbox layer, not this tool).

No raw subprocess exceptions leak upward: FileNotFoundError (command
not found) and other OSErrors are caught and re-raised as
ToolInputError. A command that times out is treated as a normal,
informative SUCCESS result (timed_out: true, partial output) rather
than a tool-execution failure -- the tool succeeded at running and
timing the command; that is different from the tool itself failing.
"""
from __future__ import annotations

import subprocess

from neptune.core.contracts.model_gateway import ToolDefinition
from neptune.core.contracts.tool_execution import ToolInputError

# Independent of and shorter than ToolExecutorService's own
# thread-level timeout (B-004, default 10s) -- this fires first and
# actually kills the OS process via subprocess's own timeout handling,
# which a thread-pool cancellation alone would not do for a blocking
# subprocess.run() call.
_DEFAULT_TIMEOUT_SECONDS = 8.0
_MAX_OUTPUT_CHARS = 20_000


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) <= _MAX_OUTPUT_CHARS:
        return text, False
    return text[:_MAX_OUTPUT_CHARS], True


class RunCommandTool:
    name = "run_command"

    def __init__(
        self,
        workspace_root,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._cwd = str(workspace_root)
        self._timeout_seconds = timeout_seconds

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Run a shell command with its working directory fixed to the "
                "workspace root. Returns exit_code, stdout, and stderr."
            ),
            parameters_schema={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )

    def execute(self, arguments: dict) -> dict:
        if "command" not in arguments:
            raise ToolInputError("missing required argument: command")
        command = arguments["command"]
        if not isinstance(command, str) or not command.strip():
            raise ToolInputError("argument 'command' must be a non-empty string")

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self._cwd,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout, _ = _truncate(exc.stdout or "" if isinstance(exc.stdout, str) else "")
            stderr, _ = _truncate(exc.stderr or "" if isinstance(exc.stderr, str) else "")
            return {
                "exit_code": None,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": True,
                "timeout_seconds": self._timeout_seconds,
            }
        except OSError as exc:
            raise ToolInputError(f"could not execute command: {exc}") from exc

        stdout, stdout_truncated = _truncate(proc.stdout or "")
        stderr, stderr_truncated = _truncate(proc.stderr or "")

        return {
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }
