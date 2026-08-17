"""Engine / session-factory wiring.

This is the one place that turns a connection string into a live SQLAlchemy
engine. Everything else (repositories) depends only on a sessionmaker,
which keeps repository code testable against any Postgres-compatible URL.
"""
from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from .models.base import Base


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, future=True)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def create_all_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)
