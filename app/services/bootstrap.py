"""Bootstrap de datos iniciales (idempotente)."""

from __future__ import annotations

import logging

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import engine
from app.models.usuario import Rol, Usuario

logger = logging.getLogger("labos.bootstrap")


def seed_admin() -> None:
    """Crea el administrador inicial si la tabla está vacía y hay credenciales."""
    email = settings.admin_email.strip().lower()
    password = settings.admin_password.get_secret_value()
    if not email or not password:
        return

    try:
        with Session(engine) as session:
            total = session.exec(select(func.count()).select_from(Usuario)).one()
            if total > 0:
                return
            admin = Usuario(
                email=email,
                hashed_password=hash_password(password),
                nombre_completo=settings.admin_nombre.strip() or "Administrador LabOS",
                rol=Rol.ADMIN,
                activo=True,
            )
            session.add(admin)
            session.commit()
            logger.info("Administrador inicial creado: %s", email)
    except SQLAlchemyError as exc:
        logger.warning(
            "No se pudo crear el administrador inicial (¿migraciones pendientes?): %s",
            exc,
        )
