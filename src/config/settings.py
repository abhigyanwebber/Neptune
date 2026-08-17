"""Configuration.

Free/cheap-first per the Bible's production objective: default points at a
local Docker Postgres (docker-compose.yml at repo root) so there is no
mandatory paid dependency to run Stage 0/1. DATABASE_URL can be overridden
to point at any Postgres-compatible instance (e.g. a free-tier managed DB)
without code changes.
"""
from __future__ import annotations

import os

DEFAULT_DATABASE_URL = "postgresql+psycopg2://neptune:neptune@localhost:5433/neptune"


def get_database_url() -> str:
    return os.environ.get("NEPTUNE_DATABASE_URL", DEFAULT_DATABASE_URL)
