"""Dependencias compartidas: sesión, usuario actual y RBAC."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import SessionDep
from app.models.usuario import Rol, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> Usuario:
    """Decodifica el JWT y devuelve el usuario activo asociado."""
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if not subject:
            raise CREDENTIALS_EXCEPTION
        user_id = uuid.UUID(subject)
    except (InvalidTokenError, ValueError):
        raise CREDENTIALS_EXCEPTION from None

    user = session.get(Usuario, user_id)
    if user is None or not user.activo:
        raise CREDENTIALS_EXCEPTION
    return user


def require_roles(*roles: Rol) -> Callable[..., Usuario]:
    """Fábrica de dependencias que exige al menos uno de los roles indicados."""
    allowed = set(roles)

    def checker(current_user: Annotated[Usuario, Depends(get_current_user)]) -> Usuario:
        if current_user.rol not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El rol actual no tiene permiso para esta operación",
            )
        return current_user

    return checker


CurrentUser = Annotated[Usuario, Depends(get_current_user)]
AdminUser = Annotated[Usuario, Depends(require_roles(Rol.ADMIN))]
StaffUser = Annotated[Usuario, Depends(require_roles(Rol.ADMIN, Rol.PROFESIONAL))]
