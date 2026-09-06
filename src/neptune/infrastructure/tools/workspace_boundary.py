"""Explicit workspace/root boundary shared by the filesystem and shell
tools (B-010).

Not a sandbox (SANDBOX_CONTRACT is frozen/unimplemented, correctly so
per 07_SECURITY/01_THREAT_MODEL.md -- nothing here provides process
isolation, resource limits, or defense against a genuinely hostile
command). This is the one thing B-010 explicitly does require: an
*explicit* workspace root that path/cwd arguments cannot escape, using
the principle already stated in 07_SECURITY/01_THREAT_MODEL.md
("least privilege") and 02_PERMISSION_MODEL.md's assumption that a
real boundary exists for a policy layer to eventually sit in front of.
"""
from __future__ import annotations

from pathlib import Path

from neptune.core.contracts.tool_execution import ToolInputError


class WorkspaceBoundary:
    """Resolves a user/model-supplied relative path against a fixed
    root and rejects anything that would escape it -- absolute paths,
    `..` traversal, or symlink resolution that lands outside the root.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ToolInputError("path must be a non-empty string")

        # Reject absolute-looking input explicitly, before joining --
        # pathlib's `/` operator silently discards the left operand
        # when the right one is absolute (Path("/root") / "/etc/passwd"
        # == Path("/etc/passwd")), so an absolute path must never be
        # allowed to reach the join at all, not just be caught by the
        # relative_to() check afterward (which does still catch it,
        # but rejecting early gives a clearer error message).
        if Path(relative_path).is_absolute():
            raise ToolInputError(f"absolute paths are not allowed: {relative_path}")

        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            raise ToolInputError(f"path escapes workspace root: {relative_path}") from None
        return candidate
