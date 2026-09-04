"""Groq provider adapter -- live implementation (B-003).

Real HTTPS requests to Groq's OpenAI-compatible chat completions
endpoint via the `requests` library. No provider SDK is used and none
of this module's types are imported by neptune.core -- the adapter
sits entirely on the infrastructure side of the boundary
(PROVIDER_CONTRACT invariant 3).

Configuration is fully externalized (GroqConfig.from_env()): no
secret is hardcoded, and GROQ_API_KEY is only read when invoke() or
health() is actually called, never at import or construction time, so
this module can be imported with no key present.
"""

from __future__ import annotations

import time

import requests

from neptune.core.contracts.model_gateway import ModelUsage, ToolIntent
from neptune.core.contracts.provider_adapter import (
    ProviderHealth,
    ProviderInvocationError,
    ProviderRequest,
    ProviderResult,
)
from neptune.core.domain import Capability, CostClass, ErrorType, HealthStatus
from neptune.infrastructure.config import GroqConfig, MissingConfigError


class GroqAdapter:
    """Live adapter for Groq's OpenAI-compatible endpoint.

    Groq is not architecturally privileged: it satisfies the same
    ProviderAdapter Protocol as MockProviderAdapter and is fully
    replaceable (PROVIDER_CONTRACT invariant 3; ADR-001).
    """

    provider_id = "groq"

    _DECLARED_CAPABILITIES = [
        Capability.FAST_GENERAL,
        Capability.TOOL_USE,
        Capability.CODING,
        Capability.SUMMARIZATION,
        Capability.CLASSIFICATION,
    ]

    def __init__(self, config: GroqConfig | None = None) -> None:
        self._config = config  # may be None; resolved lazily from env

    def _resolve_config(self) -> GroqConfig:
        return self._config or GroqConfig.from_env()

    def capabilities(self) -> list[Capability]:
        return list(self._DECLARED_CAPABILITIES)

    def cost_class(self) -> CostClass:
        return CostClass.FREE

    def health(self) -> ProviderHealth:
        try:
            config = self._resolve_config()
        except MissingConfigError as exc:
            return ProviderHealth(status=HealthStatus.UNKNOWN, detail=str(exc))

        try:
            resp = requests.get(
                f"{config.base_url}/models",
                headers={"Authorization": f"Bearer {config.api_key}"},
                timeout=config.timeout_seconds,
            )
        except requests.exceptions.Timeout:
            return ProviderHealth(status=HealthStatus.DEGRADED, detail="health check timed out")
        except requests.exceptions.RequestException as exc:
            return ProviderHealth(status=HealthStatus.UNHEALTHY, detail=str(exc))

        if resp.status_code == 200:
            return ProviderHealth(status=HealthStatus.HEALTHY, detail="GET /models succeeded")
        if resp.status_code in (401, 403):
            return ProviderHealth(status=HealthStatus.UNHEALTHY, detail="authentication rejected")
        if resp.status_code == 429:
            return ProviderHealth(status=HealthStatus.DEGRADED, detail="rate limited")
        return ProviderHealth(
            status=HealthStatus.DEGRADED, detail=f"unexpected status {resp.status_code}"
        )

    def list_live_models(self) -> list[dict]:
        """Fetch the live model catalog for capability registration
        (task item 4). Not part of the ProviderAdapter Protocol --
        an extra, Groq-specific capability-discovery helper used by
        the registry-refresh script, not by the Gateway/Router path.
        """
        config = self._resolve_config()
        resp = requests.get(
            f"{config.base_url}/models",
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=config.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def invoke(self, request: ProviderRequest) -> ProviderResult:
        try:
            config = self._resolve_config()
        except MissingConfigError as exc:
            raise ProviderInvocationError(
                error_type=ErrorType.AUTHENTICATION,
                message=str(exc),
                retriable=False,
                provider_id=self.provider_id,
            ) from exc

        payload: dict = {
            "model": request.model_id,
            "messages": [
                {"role": m.role, "content": m.content} for m in request.messages
            ],
        }
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters_schema or {"type": "object", "properties": {}},
                    },
                }
                for t in request.tools
            ]
            # Groq's default tool_choice when omitted behaves as "none"
            # (confirmed via a live 400: "Tool choice is none, but
            # model called a tool" -- B-009 live validation), unlike
            # some OpenAI-compatible surfaces that default to "auto"
            # when tools are present. Must be explicit whenever tools
            # are offered, or the model choosing to call a tool is
            # itself a request-level error rather than a normal
            # tool_calls response.
            payload["tool_choice"] = "auto"

        start = time.perf_counter()
        try:
            resp = requests.post(
                f"{config.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=config.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise ProviderInvocationError(
                error_type=ErrorType.TIMEOUT,
                message=f"Groq request timed out after {config.timeout_seconds}s",
                retriable=True,
                provider_id=self.provider_id,
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderInvocationError(
                error_type=ErrorType.PROVIDER_UNAVAILABLE,
                message=f"could not reach Groq: {exc}",
                retriable=True,
                provider_id=self.provider_id,
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderInvocationError(
                error_type=ErrorType.UNKNOWN,
                message=str(exc),
                retriable=True,
                provider_id=self.provider_id,
            ) from exc
        latency_ms = (time.perf_counter() - start) * 1000

        if resp.status_code != 200:
            raise self._error_for_status(resp, latency_ms)

        return self._parse_success(resp, latency_ms)


    def _error_for_status(
        self, resp: "requests.Response", latency_ms: float
    ) -> ProviderInvocationError:
        """Map an HTTP error response to a normalized
        ProviderInvocationError. No raw HTTP/SDK exception ever
        crosses this boundary (PROVIDER_CONTRACT invariant 3)."""
        del latency_ms  # currently unused; kept for future observability hook
        try:
            body = resp.json()
            detail = body.get("error", {}).get("message", resp.text)
        except ValueError:
            detail = resp.text

        status = resp.status_code
        if status in (401, 403):
            return ProviderInvocationError(
                error_type=ErrorType.AUTHENTICATION,
                message=f"Groq authentication failed ({status}): {detail}",
                retriable=False,
                provider_id=self.provider_id,
            )
        if status == 404:
            return ProviderInvocationError(
                error_type=ErrorType.INVALID_REQUEST,
                message=f"Groq model or route not found ({status}): {detail}",
                retriable=False,
                provider_id=self.provider_id,
            )
        if status == 429:
            return ProviderInvocationError(
                error_type=ErrorType.RATE_LIMITED,
                message=f"Groq rate limit exceeded ({status}): {detail}",
                retriable=True,
                provider_id=self.provider_id,
            )
        if status == 400:
            return ProviderInvocationError(
                error_type=ErrorType.INVALID_REQUEST,
                message=f"Groq rejected the request ({status}): {detail}",
                retriable=False,
                provider_id=self.provider_id,
            )
        if 500 <= status < 600:
            return ProviderInvocationError(
                error_type=ErrorType.PROVIDER_UNAVAILABLE,
                message=f"Groq server error ({status}): {detail}",
                retriable=True,
                provider_id=self.provider_id,
            )
        return ProviderInvocationError(
            error_type=ErrorType.UNKNOWN,
            message=f"Groq returned unexpected status ({status}): {detail}",
            retriable=False,
            provider_id=self.provider_id,
        )

    def _parse_success(self, resp: "requests.Response", latency_ms: float) -> ProviderResult:
        body = resp.json()
        choice = body["choices"][0]
        message = choice.get("message", {})

        tool_intents: list[ToolIntent] = []
        for call in message.get("tool_calls") or []:
            function = call.get("function", {})
            raw_args = function.get("arguments") or "{}"
            try:
                import json

                arguments = json.loads(raw_args)
            except (ValueError, TypeError):
                arguments = {"_raw": raw_args}
            tool_intents.append(
                ToolIntent(
                    call_id=call.get("id", ""),
                    tool_name=function.get("name", ""),
                    arguments=arguments,
                )
            )

        usage_body = body.get("usage") or {}
        usage = ModelUsage(
            input_tokens=usage_body.get("prompt_tokens"),
            output_tokens=usage_body.get("completion_tokens"),
            total_tokens=usage_body.get("total_tokens"),
            cost_estimate_usd=0.0,  # Groq free tier: no per-call cost
        )

        return ProviderResult(
            output_text=message.get("content"),
            tool_intents=tool_intents,
            usage=usage,
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason"),
        )
