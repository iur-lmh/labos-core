"""Modelo de evaluación biomecánica y catálogo de protocolos."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Uuid, func, text
from sqlmodel import Field, Relationship, SQLModel

from app.db.types import JSONType
from app.models.paciente import Paciente

if TYPE_CHECKING:
    from app.models.archivo import ArchivoAdjunto


class TipoProtocolo(StrEnum):
    SALTO_VERTICAL = "salto_vertical"
    SALTO_HORIZONTAL = "salto_horizontal"
    MARCHA = "marcha"
    EMG = "emg"
    FUERZA = "fuerza"
    EQUILIBRIO = "equilibrio"
    MOVILIDAD = "movilidad"
    OTRO = "otro"


class EvaluacionBase(SQLModel):
    tipo_protocolo: str = Field(max_length=60, index=True)
    fecha: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            index=True,
            nullable=False,
            server_default=func.now(),
        ),
    )
    dispositivo_origen: str = Field(max_length=80, index=True)
    datos_raw: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONType, nullable=False, server_default=text("'{}'")),
    )


class Evaluacion(EvaluacionBase, table=True):
    __tablename__ = "evaluaciones"
    __table_args__ = (Index("ix_evaluaciones_paciente_fecha", "paciente_id", "fecha"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    paciente_id: uuid.UUID = Field(
        sa_column=Column(
            Uuid,
            ForeignKey("pacientes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    paciente: Optional[Paciente] = Relationship(  # noqa: UP007
        back_populates="evaluaciones"
    )
    archivos: list["ArchivoAdjunto"] = Relationship(
        back_populates="evaluacion",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"Evaluacion(id={self.id!r}, protocolo={self.tipo_protocolo!r})"
