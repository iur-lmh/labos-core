"""Modelo de paciente.

`metadata_` se mapea a la columna JSONB `metadata`; el guion bajo evita la colisión con
`DeclarativeBase.metadata` de SQLAlchemy.
"""

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, func, text
from sqlmodel import Field, Relationship, SQLModel

from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.evaluacion import Evaluacion


def utcnow() -> datetime:
    return datetime.now(UTC)


class PacienteBase(SQLModel):
    nombre: str = Field(max_length=120, index=True)
    apellido: str = Field(max_length=120, index=True)
    fecha_nacimiento: date | None = Field(default=None)
    dni_anonimizado: str = Field(max_length=64, unique=True, index=True)
    metadata_: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            "metadata",
            JSONType,
            nullable=False,
            server_default=text("'{}'"),
        ),
    )


class Paciente(PacienteBase, table=True):
    __tablename__ = "pacientes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    evaluaciones: list["Evaluacion"] = Relationship(
        back_populates="paciente",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"Paciente(id={self.id!r}, apellido={self.apellido!r})"
