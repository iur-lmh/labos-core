"""Registro de metadata de SQLModel.

Importar este módulo garantiza que todas las tablas estén registradas antes de que
Alembic o `create_all` las consulten.
"""

from __future__ import annotations

from app.models.archivo import ArchivoAdjunto
from app.models.evaluacion import Evaluacion
from app.models.paciente import Paciente
from app.models.usuario import Rol, Usuario

__all__ = ["ArchivoAdjunto", "Evaluacion", "Paciente", "Rol", "Usuario"]
