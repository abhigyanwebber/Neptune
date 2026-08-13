"""Model Gateway boundary contract.

Core Runtime depends on this Protocol, never on a provider SDK. Claude B's
Model Gateway will implement it for real; Core ships FakeModelGateway
(src/core/runtime/fakes.py) so the runtime is fully testable without a
real provider (director brief: "The Core must be testable without a real
provider").

Request/response shape is intentionally an opaque dict, mirroring how
Turn.model_request / Turn.model_response are already persisted
(core/domain/turn.py) -- Core does not interpret provider-specific fields,
it only stores and forwards them.
"""
from __future__ import annotations

from typing import Any, Protocol


class ModelGatewayPort(Protocol):
    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Submit a model request and return a normalized response.

        Core does not know or care which provider/model served this --
        that routing/fallback/cost decision belongs entirely to Claude B's
        Model Gateway (ADR-003, ADR-032). Core only needs a response dict
        it can store on the Turn and inspect for a `tool_calls` list.
        """
        ...
