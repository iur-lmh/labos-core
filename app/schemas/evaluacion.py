"""Contratos de evaluación y archivos adjuntos."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.models.archivo import TipoArchivo
from app.models.evaluacion import TipoProtocolo

PII_KEYS = {
    "nombre",
    "apellido",
    "nombres",
    "apellidos",
    "dni",
    "documento",
    "email",
    "correo",
    "telefono",
    "teléfono",
    "direccion",
    "dirección",
    "fecha_nacimiento",
}


def _contiene_pii(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).strip().lower() in PII_KEYS:
                return True
            if _contiene_pii(nested):
                return True
    elif isinstance(value, list):
        return any(_contiene_pii(item) for item in value)
    return False


class EvaluacionCreate(BaseModel):
    paciente_id: uuid.UUID
    tipo_protocolo: TipoProtocolo
    fecha: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dispositivo_origen: str = Field(min_length=1, max_length=80)
    datos_raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("fecha")
    @classmethod
    def normalizar_fecha(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @field_validator("datos_raw")
    @classmethod
    def validar_datos_raw(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _contiene_pii(value):
            raise ValueError(
                "datos_raw contiene claves de identificación personal; "
                "usar solo métricas seudonimizadas"
            )
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as exc:
            raise ValueError("datos_raw debe ser serializable a JSON") from exc
        if len(serialized.encode("utf-8")) > settings.max_datos_raw_bytes:
            raise ValueError(f"datos_raw supera el límite de {settings.max_datos_raw_bytes} bytes")
        return value


class EvaluacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paciente_id: uuid.UUID
    tipo_protocolo: str
    fecha: datetime
    dispositivo_origen: str
    datos_raw: dict[str, Any]
    created_at: datetime


class ArchivoCreate(BaseModel):
    url_storage: str = Field(min_length=1, max_length=2048)
    tipo_archivo: TipoArchivo
    hash_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    nombre_original: str | None = Field(default=None, max_length=255)
    tamano_bytes: int | None = Field(default=None, ge=0, le=settings.max_archivo_bytes)

    @field_validator("hash_sha256")
    @classmethod
    def normalizar_hash(cls, value: str) -> str:
        return value.lower()

    @field_validator("url_storage")
    @classmethod
    def validar_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://", "s3://", "/")):
            raise ValueError("url_storage debe ser http(s), s3 o una ruta relativa")
        return value


class ArchivoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evaluacion_id: uuid.UUID
    url_storage: str
    tipo_archivo: str
    hash_sha256: str
    nombre_original: str | None
    tamano_bytes: int | None
    created_at: datetime
