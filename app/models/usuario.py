"""Usuario de la plataforma y roles RBAC."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Uuid, func, text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class Rol(StrEnum):
    ADMIN = "admin"
    PROFESIONAL = "profesional"
    PACIENTE = "paciente"


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    email: str = Field(max_length=320, unique=True, index=True)
    hashed_password: str = Field(max_length=255)
    nombre_completo: str = Field(max_length=160)
    rol: Rol = Field(
        sa_column=Column(
            SAEnum(
                Rol,
                name="rol_usuario",
                values_callable=lambda enum: [item.value for item in enum],
            ),
            nullable=False,
            index=True,
            default=Rol.PROFESIONAL,
            server_default=Rol.PROFESIONAL.value,
        )
    )
    activo: bool = Field(
        default=True,
        sa_column_kwargs={"server_default": text("true")},
    )
    paciente_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid,
            ForeignKey("pacientes.id", ondelete="SET NULL"),
            nullable=True,
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

    def __repr__(self) -> str:  # pragma: no cover
        return f"Usuario(id={self.id!r}, email={self.email!r}, rol={self.rol.value!r})"
