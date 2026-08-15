"""Live capability-registration probe (task item 4).

Fetches Groq's live model catalog and prints a diff-friendly summary
against config/registries/model_registry.yaml so a human can update
the registry with verified values. Deliberately does NOT auto-write
the registry -- registry entries are reviewed data, not
machine-overwritten state (same discipline as the rest of
06_REGISTRIES/*).

Usage:
    $env:GROQ_API_KEY = "..."
    python scripts/probe_groq_models.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from neptune.infrastructure.providers.groq_adapter import GroqAdapter  # noqa: E402


def main() -> int:
    adapter = GroqAdapter()
    health = adapter.health()
    print(f"health: {health.status.value} ({health.detail})")
    if health.status.value != "healthy":
        print("Aborting: provider not healthy, cannot probe capabilities.")
        return 1

    models = adapter.list_live_models()
    print(f"\nLive Groq models (verified {date.today().isoformat()}):\n")
    for m in models:
        print(f"  - id: {m.get('id')}")
        print(f"    context_window: {m.get('context_window')}")
        print(f"    owned_by: {m.get('owned_by')}")
        print(f"    active: {m.get('active')}")
    print(
        f"\n{len(models)} model(s) returned. Compare against "
        "config/registries/model_registry.yaml and update verified_at, "
        "context_limit, and availability by hand."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
