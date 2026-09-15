"""Filesystem tools, scoped to an explicit WorkspaceBoundary (B-010).

Three separate Tool implementations (read/write/list), matching the
one-tool-one-bounded-capability shape already established by EchoTool
(B-004) rather than one tool with an "operation" switch -- keeps each
tool's model-facing schema minimal and matches how the research corpus
(04_RESEARCH/tool_candidates.md) describes mature coding-agent harnesses
exposing file operations as separate functions.

No raw OS exceptions leak upward: every filesystem error (missing
path, wrong type, permission denied, encoding failure) is caught and
re-raised as ToolInputError, which ToolExecutor (B-004, unmodified)
already normalizes into a structured ToolResult.
"""
from __future__ import annotations

from neptune.core.contracts.model_gateway import ToolDefinition
from neptune.core.contracts.tool_execution import ToolInputError
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary

# Read/write size guard, independent of and smaller than
# ToolExecutorService's own downstream max_output_bytes (B-004,
# default 32000) -- this one exists so a huge file is never even fully
# read into memory just to have the executor reject it afterward.
_MAX_FILE_BYTES = 200_000


class ReadFileTool:
    name = "read_file"

    def __init__(self, boundary: WorkspaceBoundary) -> None:
        self._boundary = boundary

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Read the contents of a text file within the workspace. "
                "path is relative to the workspace root."
            ),
            parameters_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )

    def execute(self, arguments: dict) -> dict:
        if "path" not in arguments:
            raise ToolInputError("missing required argument: path")
        path = self._boundary.resolve(arguments["path"])

        if not path.exists():
            raise ToolInputError(f"file not found: {arguments['path']}")
        if not path.is_file():
            raise ToolInputError(f"not a file: {arguments['path']}")

        try:
            size = path.stat().st_size
        except OSError as exc:
            raise ToolInputError(f"could not stat file: {exc}") from exc
        if size > _MAX_FILE_BYTES:
            raise ToolInputError(
                f"file too large to read: {size}B exceeds limit {_MAX_FILE_BYTES}B"
            )

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ToolInputError(f"file is not valid UTF-8 text: {exc}") from exc
        except OSError as exc:
            raise ToolInputError(f"could not read file: {exc}") from exc

        return {"path": arguments["path"], "content": content}


class WriteFileTool:
    name = "write_file"

    def __init__(self, boundary: WorkspaceBoundary) -> None:
        self._boundary = boundary

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Write text content to a file within the workspace, creating "
                "parent directories and overwriting any existing file. path "
                "is relative to the workspace root."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        )

    def execute(self, arguments: dict) -> dict:
        if "path" not in arguments:
            raise ToolInputError("missing required argument: path")
        if "content" not in arguments:
            raise ToolInputError("missing required argument: content")
        content = arguments["content"]
        if not isinstance(content, str):
            raise ToolInputError(
                f"argument 'content' must be a string, got {type(content).__name__}"
            )

        content_bytes = content.encode("utf-8")
        if len(content_bytes) > _MAX_FILE_BYTES:
            raise ToolInputError(
                f"content too large to write: {len(content_bytes)}B exceeds "
                f"limit {_MAX_FILE_BYTES}B"
            )

        path = self._boundary.resolve(arguments["path"])
        if path.exists() and path.is_dir():
            raise ToolInputError(f"path is a directory, not a file: {arguments['path']}")

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise ToolInputError(f"could not write file: {exc}") from exc

        return {"path": arguments["path"], "bytes_written": len(content_bytes)}


class ListDirectoryTool:
    name = "list_directory"

    def __init__(self, boundary: WorkspaceBoundary) -> None:
        self._boundary = boundary

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "List the immediate contents of a directory within the "
                'workspace. path is relative to the workspace root; use "." '
                "for the workspace root itself."
            ),
            parameters_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )

    def execute(self, arguments: dict) -> dict:
        raw_path = arguments.get("path", ".")
        if not isinstance(raw_path, str):
            raise ToolInputError(
                f"argument 'path' must be a string, got {type(raw_path).__name__}"
            )
        # WorkspaceBoundary.resolve() rejects empty strings, but "." is
        # a normal, expected way to refer to the workspace root itself.
        path = self._boundary.resolve(raw_path if raw_path.strip() else ".")

        if not path.exists():
            raise ToolInputError(f"directory not found: {raw_path}")
        if not path.is_dir():
            raise ToolInputError(f"not a directory: {raw_path}")

        try:
            entries = [
                {"name": child.name, "type": "dir" if child.is_dir() else "file"}
                for child in sorted(path.iterdir(), key=lambda p: p.name)
            ]
        except OSError as exc:
            raise ToolInputError(f"could not list directory: {exc}") from exc

        return {"path": raw_path, "entries": entries}
