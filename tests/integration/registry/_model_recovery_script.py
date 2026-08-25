"""Standalone script invoked as a SEPARATE OS process by
test_model_recovery.py.

    python _model_recovery_script.py write
        -> registers a Model (and its Provider) plus verification
           metadata, then this process exits (dies).
    python _model_recovery_script.py read
        -> a brand-new process reconnects and reads the model back,
           confirms verification metadata, provider relationship, and
           dependency resolution against its provider all survived.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from config.settings import get_database_url  # noqa: E402
from core.registry.dependency_resolution import resolve_dependencies  # noqa: E402
from core.registry.model_registry import Model, ModelRegistry  # noqa: E402
from core.registry.provider_registry import Provider, ProviderRegistry  # noqa: E402
from infrastructure.persistence.database import (  # noqa: E402
    create_all_tables,
    make_engine,
    make_session_factory,
)
from infrastructure.persistence.repositories import (  # noqa: E402
    SqlAlchemyModelRepository,
    SqlAlchemyProviderRepository,
)


def _registries():
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return ProviderRegistry(SqlAlchemyProviderRepository(sf)), ModelRegistry(SqlAlchemyModelRepository(sf))


def do_write() -> None:
    providers, models = _registries()

    # Idempotency: fixed ids, Postgres data persists across repeated test
    # runs (docker volume) -- same pattern as the A-003 registry recovery
    # script.
    models.delete("groq-llama-3.3-70b-versatile")
    providers.delete("groq")

    providers.register(Provider(provider_id="groq", name="Groq", endpoints=["https://api.groq.com/openai/v1"]))
    models.register(
        Model(
            model_id="groq-llama-3.3-70b-versatile",
            provider_id="groq",
            provider_model_name="llama-3.3-70b-versatile",
            capabilities=["coding", "tool_use"],
            status="available",
            depends_on=["groq"],
            verification_date="2026-08-13",
            verification_source="B-003 live validation",
            verification_status="verified",
        )
    )
    print(json.dumps({"status": "written"}))


def do_read() -> None:
    providers, models = _registries()

    model = models.get("groq-llama-3.3-70b-versatile")
    provider = providers.get("groq")

    dependency_map = {"groq": [], "groq-llama-3.3-70b-versatile": ["groq"]}
    resolution_order = resolve_dependencies("groq-llama-3.3-70b-versatile", dependency_map)

    result = {
        "model_found": model is not None,
        "provider_id": model.provider_id if model else None,
        "provider_model_name": model.provider_model_name if model else None,
        "capabilities": model.capabilities if model else None,
        "status": model.status if model else None,
        "verification_status": model.verification_status if model else None,
        "verification_source": model.verification_source if model else None,
        "provider_found": provider is not None,
        "provider_endpoints": provider.endpoints if provider else None,
        "dependency_resolution_order": resolution_order,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "write":
        do_write()
    elif mode == "read":
        do_read()
    else:
        raise SystemExit(f"Unknown mode: {mode}")
