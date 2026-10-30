"""Modelo de archivo adjunto a una evaluación."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Uuid, func
from sqlmodel import Field, Relationship, SQLModel

from app.models.evaluacion import Evaluacion


class TipoArchivo(StrEnum):
    PDF = "pdf"
    C3D = "c3d"
    MP4 = "mp4"
    CSV = "csv"
    JSON = "json"
    PNG = "png"
    OTRO = "otro"


class ArchivoAdjunto(SQLModel, table=True):
    __tablename__ = "archivos_adjuntos"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    evaluacion_id: uuid.UUID = Field(
        sa_column=Column(
            Uuid,
            ForeignKey("evaluaciones.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    url_storage: str = Field(max_length=2048)
    tipo_archivo: str = Field(max_length=16, index=True)
    hash_sha256: str = Field(max_length=64, index=True)
    nombre_original: str | None = Field(default=None, max_length=255)
    tamano_bytes: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    evaluacion: Optional[Evaluacion] = Relationship(  # noqa: UP007
        back_populates="archivos"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"ArchivoAdjunto(id={self.id!r}, tipo={self.tipo_archivo!r})"
