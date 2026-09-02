"""Integration test (B-008): canonical registry -> resolver -> gateway
-> Groq adapter -> normalized ModelResponse, using a mocked HTTP path.

This is the "at minimum" integration test B-008 requires: the full
real chain (Postgres-backed canonical registry, real ProviderResolver,
real CapabilityRouter, real ModelGatewayService, real GroqAdapter)
except the actual network call to Groq, which is mocked -- proving the
wiring is correct without spending a live API call on every test run.
The live-network variant is tests/integration/gateway/
test_live_first_agent_turn.py.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.registry.capability_registry import CapabilityRegistry
from core.registry.model_registry import ModelRegistry as CanonicalModelRegistry
from core.registry.provider_registry import ProviderRegistry
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry
from core.resolution.capability_resolver import CapabilityResolver
from core.resolution.provider_resolver import ProviderResolver
from core.resolution.resource_resolver import ResourceResolver
from infrastructure.persistence.database import make_engine, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyModelRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)

from neptune.application.gateway_service import ModelGatewayService
from neptune.infrastructure.config import GroqConfig
from neptune.infrastructure.gateway.model_gateway_adapter import ModelGatewayAdapter
from neptune.infrastructure.models.canonical_registry_adapter import (
    CanonicalRegistryCandidateSource,
)
from neptune.infrastructure.providers.groq_adapter import GroqAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter


def _postgres_available() -> bool:
    try:
        engine = make_engine(get_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason="Postgres not reachable at NEPTUNE_DATABASE_URL; run `docker compose up -d`",
)


def _build_mock_response(status_code: int, json_body: dict):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.text = str(json_body)
    return resp


def _build_adapter() -> ModelGatewayAdapter:
    engine = make_engine(get_database_url())
    sf = make_session_factory(engine)
    cap_reg = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    prov_reg = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    res_reg = ResourceRegistry(SqlAlchemyResourceRepository(sf))
    tool_reg = ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    model_reg = CanonicalModelRegistry(SqlAlchemyModelRepository(sf))

    cap_resolver = CapabilityResolver(cap_reg, prov_reg, tool_reg)
    res_resolver = ResourceResolver(cap_reg, prov_reg, res_reg, tool_reg)
    prov_resolver = ProviderResolver(cap_resolver, res_resolver, prov_reg)

    candidate_source = CanonicalRegistryCandidateSource(prov_resolver, model_reg)
    gateway = ModelGatewayService(
        registry=candidate_source,
        router=CapabilityRouter(),
        adapters={"groq": GroqAdapter(config=GroqConfig(api_key="fake-key-for-mocked-tests"))},
    )
    return ModelGatewayAdapter(gateway, task_id="int-task-1", session_id="int-session-1")


def test_canonical_path_reaches_groq_adapter_with_correct_model_id() -> None:
    """The full real chain -- Postgres registry, real resolver, real
    router, real GroqAdapter -- with only the HTTP call mocked. Proves
    the canonical-registry swap (B-008 item 3 / C-005's cutover) works
    end-to-end, and that the provider-facing model name reaches the
    HTTP payload correctly (not the registry entry key)."""
    adapter = _build_adapter()
    body = {
        "choices": [{"message": {"content": "NEPTUNE_GATEWAY_OK"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
    }

    with patch("requests.post", return_value=_build_mock_response(200, body)) as mock_post:
        response = adapter.send(
            {
                "requirements": ["Respond with exactly: NEPTUNE_GATEWAY_OK"],
                "constraints": {"capability": "coding"},
            }
        )

    assert response["content"] == "NEPTUNE_GATEWAY_OK"
    assert response["provider_id"] == "groq"
    assert response["model_id"] == "openai/gpt-oss-120b"
    assert "error" not in response

    # The actual HTTP payload sent must carry the provider-facing name.
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "openai/gpt-oss-120b"


def test_canonical_path_normalizes_a_404_without_leaking_http_detail() -> None:
    adapter = _build_adapter()
    with patch(
        "requests.post",
        return_value=_build_mock_response(404, {"error": {"message": "model not found"}}),
    ):
        response = adapter.send(
            {"requirements": ["hi"], "constraints": {"capability": "coding"}}
        )

    assert response["content"] is None
    assert response["error"]["error_type"] == "invalid_request"
    # No raw requests.Response, HTTPError, or provider payload leaked --
    # only the normalized dict shape.
    assert isinstance(response["error"]["message"], str)
    assert set(response["error"].keys()) == {"error_type", "message", "retriable", "provider_id"}
