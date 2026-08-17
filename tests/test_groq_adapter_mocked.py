"""GroqAdapter failure-mode tests (mocked HTTP, no live credentials).

Covers task item 5 (Failure Validation): invalid API key, unavailable
model, timeout, rate limit. These run in CI without GROQ_API_KEY by
monkeypatching `requests` so no network call is made. The live,
credentialed counterpart is in test_groq_live_e2e.py (skipped unless
GROQ_API_KEY is set).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from neptune.core.contracts.model_gateway import ContextMessage
from neptune.core.contracts.provider_adapter import ProviderInvocationError, ProviderRequest
from neptune.core.domain import ErrorType
from neptune.infrastructure.config import GroqConfig
from neptune.infrastructure.providers.groq_adapter import GroqAdapter


@pytest.fixture
def adapter() -> GroqAdapter:
    # Fixed config so no real GROQ_API_KEY is required for these tests.
    return GroqAdapter(config=GroqConfig(api_key="fake-key-for-mocked-tests"))


@pytest.fixture
def sample_request() -> ProviderRequest:
    return ProviderRequest(
        correlation_id="corr-mocked-1",
        model_id="llama-3.3-70b-versatile",
        messages=[ContextMessage(role="user", content="hello")],
    )


def _mock_response(status_code: int, json_body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.text = str(json_body)
    return resp


def test_invalid_api_key_maps_to_authentication_error(
    adapter: GroqAdapter, sample_request: ProviderRequest
) -> None:
    body = {"error": {"message": "Invalid API Key"}}
    with patch("requests.post", return_value=_mock_response(401, body)):
        with pytest.raises(ProviderInvocationError) as exc_info:
            adapter.invoke(sample_request)
    assert exc_info.value.error_type == ErrorType.AUTHENTICATION
    assert exc_info.value.retriable is False
    assert exc_info.value.provider_id == "groq"


def test_unavailable_model_maps_to_invalid_request_error(
    adapter: GroqAdapter, sample_request: ProviderRequest
) -> None:
    body = {"error": {"message": "The model does not exist"}}
    with patch("requests.post", return_value=_mock_response(404, body)):
        with pytest.raises(ProviderInvocationError) as exc_info:
            adapter.invoke(sample_request)
    assert exc_info.value.error_type == ErrorType.INVALID_REQUEST
    assert exc_info.value.retriable is False


def test_timeout_maps_to_timeout_error_and_is_retriable(
    adapter: GroqAdapter, sample_request: ProviderRequest
) -> None:
    with patch("requests.post", side_effect=requests.exceptions.Timeout("timed out")):
        with pytest.raises(ProviderInvocationError) as exc_info:
            adapter.invoke(sample_request)
    assert exc_info.value.error_type == ErrorType.TIMEOUT
    assert exc_info.value.retriable is True


def test_rate_limit_maps_to_rate_limited_error_and_is_retriable(
    adapter: GroqAdapter, sample_request: ProviderRequest
) -> None:
    body = {"error": {"message": "Rate limit reached"}}
    with patch("requests.post", return_value=_mock_response(429, body)):
        with pytest.raises(ProviderInvocationError) as exc_info:
            adapter.invoke(sample_request)
    assert exc_info.value.error_type == ErrorType.RATE_LIMITED
    assert exc_info.value.retriable is True


def test_connection_error_maps_to_provider_unavailable_and_is_retriable(
    adapter: GroqAdapter, sample_request: ProviderRequest
) -> None:
    with patch(
        "requests.post",
        side_effect=requests.exceptions.ConnectionError("connection refused"),
    ):
        with pytest.raises(ProviderInvocationError) as exc_info:
            adapter.invoke(sample_request)
    assert exc_info.value.error_type == ErrorType.PROVIDER_UNAVAILABLE
    assert exc_info.value.retriable is True


def test_server_error_maps_to_provider_unavailable_and_is_retriable(
    adapter: GroqAdapter, sample_request: ProviderRequest
) -> None:
    body = {"error": {"message": "internal server error"}}
    with patch("requests.post", return_value=_mock_response(503, body)):
        with pytest.raises(ProviderInvocationError) as exc_info:
            adapter.invoke(sample_request)
    assert exc_info.value.error_type == ErrorType.PROVIDER_UNAVAILABLE
    assert exc_info.value.retriable is True


def test_missing_api_key_never_reaches_network(sample_request: ProviderRequest) -> None:
    """If GROQ_API_KEY isn't set and no config was injected, invoke()
    must fail fast with AUTHENTICATION and never attempt a request."""
    import os

    adapter = GroqAdapter()
    original = os.environ.pop("GROQ_API_KEY", None)
    try:
        with patch("requests.post") as mock_post:
            with pytest.raises(ProviderInvocationError) as exc_info:
                adapter.invoke(sample_request)
            mock_post.assert_not_called()
        assert exc_info.value.error_type == ErrorType.AUTHENTICATION
        assert exc_info.value.retriable is False
    finally:
        if original is not None:
            os.environ["GROQ_API_KEY"] = original


def test_successful_response_parses_tool_calls_and_usage(
    adapter: GroqAdapter, sample_request: ProviderRequest
) -> None:
    body = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Lucknow"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
    }
    with patch("requests.post", return_value=_mock_response(200, body)):
        result = adapter.invoke(sample_request)

    assert result.finish_reason == "tool_calls"
    assert len(result.tool_intents) == 1
    assert result.tool_intents[0].tool_name == "get_weather"
    assert result.tool_intents[0].arguments == {"city": "Lucknow"}
    assert result.usage.total_tokens == 17
