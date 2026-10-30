"""Contratos de paciente."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


def _normalizar_dni(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("dni_anonimizado no puede estar vacío")
    if not all(char.isalnum() or char in {"-", "_"} for char in normalized):
        raise ValueError("dni_anonimizado solo admite letras, números, '-' y '_'")
    return normalized


class PacienteCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    apellido: str = Field(min_length=1, max_length=120)
    fecha_nacimiento: date | None = None
    dni_anonimizado: str = Field(min_length=6, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("dni_anonimizado")
    @classmethod
    def validar_dni(cls, value: str) -> str:
        return _normalizar_dni(value)

    @field_validator("nombre", "apellido")
    @classmethod
    def limpiar_nombre(cls, value: str) -> str:
        return " ".join(value.split())


class PacienteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellido: str | None = Field(default=None, min_length=1, max_length=120)
    fecha_nacimiento: date | None = None
    dni_anonimizado: str | None = Field(default=None, min_length=6, max_length=64)
    metadata: dict[str, Any] | None = None

    @field_validator("dni_anonimizado")
    @classmethod
    def validar_dni(cls, value: str | None) -> str | None:
        return _normalizar_dni(value) if value is not None else None

    @field_validator("nombre", "apellido")
    @classmethod
    def limpiar_nombre(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None


class PacienteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    nombre: str
    apellido: str
    fecha_nacimiento: date | None
    dni_anonimizado: str
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )
    created_at: datetime
    updated_at: datetime
