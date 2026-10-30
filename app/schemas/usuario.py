"""Contratos de usuario y autenticación."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.usuario import Rol


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str | None = None
    rol: str | None = None


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    nombre_completo: str = Field(min_length=1, max_length=160)
    rol: Rol = Rol.PROFESIONAL
    paciente_id: uuid.UUID | None = None


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    nombre_completo: str
    rol: Rol
    activo: bool
    paciente_id: uuid.UUID | None
    created_at: datetime


class UsuarioUpdate(BaseModel):
    nombre_completo: str | None = Field(default=None, min_length=1, max_length=160)
    activo: bool | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)
