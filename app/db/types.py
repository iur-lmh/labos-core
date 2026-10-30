"""Tipos de columna compartidos."""

from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.sqltypes import TypeEngine

# JSON portable: JSONB en PostgreSQL, JSON en SQLite (tests).
JSONType: TypeEngine = JSON().with_variant(JSONB(), "postgresql")

__all__ = ["JSONType"]
