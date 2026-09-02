"""Unit tests: provider error mapping through ModelGatewayAdapter
(B-008 item 6).

GroqAdapter's own error-type mapping (401->AUTHENTICATION,
404->INVALID_REQUEST, 429->RATE_LIMITED, timeout->TIMEOUT,
connection error->PROVIDER_UNAVAILABLE, 5xx->PROVIDER_UNAVAILABLE) is
already covered by tests/test_groq_adapter_mocked.py (B-003) and is
NOT re-tested here -- that would duplicate coverage. This file tests
the one thing B-008 actually adds: that GroqAdapter's normalized
ProviderInvocationError, once it becomes a ModelGatewayError inside
ModelGatewayService, comes out the far side of ModelGatewayAdapter as
a plain dict with no raised exception and no raw HTTP/SDK detail --
for every required failure class B-008 lists (item 6): authentication,
invalid model, invalid request, timeout, rate limit, connection
failure, provider/server failure.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from neptune.application.gateway_service import ModelGatewayService
from neptune.core.contracts.router import RoutingCandidate
from neptune.core.domain import Availability, Capability, CostClass
from neptune.infrastructure.config import GroqConfig
from neptune.infrastructure.gateway.model_gateway_adapter import ModelGatewayAdapter
from neptune.infrastructure.providers.groq_adapter import GroqAdapter


class _GroqOnlySource:
    def candidates_for(self, capabilities: list[Capability]) -> list[RoutingCandidate]:
        del capabilities
        return [
            RoutingCandidate(
                model_id="llama-3.3-70b-versatile",
                provider_id="groq",
                capabilities=[Capability.CODING],
                cost_class=CostClass.FREE,
                availability=Availability.AVAILABLE,
            )
        ]


def _build_adapter() -> ModelGatewayAdapter:
    groq_adapter = GroqAdapter(config=GroqConfig(api_key="fake-key-for-mocked-tests"))
    gateway = ModelGatewayService(
        registry=_GroqOnlySource(),
        router=__import__(
            "neptune.infrastructure.routing.capability_router", fromlist=["CapabilityRouter"]
        ).CapabilityRouter(),
        adapters={"groq": groq_adapter},
    )
    return ModelGatewayAdapter(gateway, task_id="t1", session_id="s1")


def _mock_response(status_code: int, json_body: dict):
    from unittest.mock import MagicMock

    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.text = str(json_body)
    return resp


@pytest.mark.parametrize(
    "status_code,expected_error_type",
    [
        (401, "authentication"),
        (404, "invalid_request"),
        (429, "rate_limited"),
        (400, "invalid_request"),
        (503, "provider_unavailable"),
    ],
)
def test_http_error_never_raises_and_maps_to_neptune_error(status_code, expected_error_type) -> None:
    adapter = _build_adapter()
    with patch("requests.post", return_value=_mock_response(status_code, {"error": {"message": "boom"}})):
        response = adapter.send({"requirements": ["hi"], "constraints": {"capability": "coding"}})

    assert response["content"] is None
    assert response["tool_calls"] == []
    assert response["error"]["error_type"] == expected_error_type
    assert response["error"]["provider_id"] == "groq"


def test_timeout_never_raises_and_maps_to_neptune_error() -> None:
    adapter = _build_adapter()
    with patch("requests.post", side_effect=requests.exceptions.Timeout("timed out")):
        response = adapter.send({"requirements": ["hi"], "constraints": {"capability": "coding"}})

    assert response["content"] is None
    assert response["error"]["error_type"] == "timeout"
    # retriable is False here by design (ModelGatewayService.infer()
    # always sets retriable=False once the fallback_chain is
    # exhausted -- "nothing left to try within this call" is a
    # different concept than "was the underlying HTTP error itself
    # retriable", which GroqAdapter's own mocked tests (B-003) already
    # confirm is True at the ProviderInvocationError level.
    assert response["error"]["retriable"] is False


def test_connection_failure_never_raises_and_maps_to_neptune_error() -> None:
    adapter = _build_adapter()
    with patch(
        "requests.post", side_effect=requests.exceptions.ConnectionError("refused")
    ):
        response = adapter.send({"requirements": ["hi"], "constraints": {"capability": "coding"}})

    assert response["content"] is None
    assert response["error"]["error_type"] == "provider_unavailable"
    assert response["error"]["retriable"] is False


def test_successful_response_has_no_error_key() -> None:
    adapter = _build_adapter()
    body = {
        "choices": [{"message": {"content": "NEPTUNE_GATEWAY_OK"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }
    with patch("requests.post", return_value=_mock_response(200, body)):
        response = adapter.send({"requirements": ["hi"], "constraints": {"capability": "coding"}})

    assert response["content"] == "NEPTUNE_GATEWAY_OK"
    assert "error" not in response
