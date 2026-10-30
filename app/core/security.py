"""Primitivas de seguridad: hashing de contraseñas y tokens JWT.

La autorización (consulta de usuario y RBAC) vive en `app/api/v1/deps.py` para evitar
dependencias circulares con la capa de base de datos.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Devuelve un hash Argon2 de la contraseña."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash, sin propagar errores de formato."""
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:  # hash corrupto o algoritmo desconocido
        return False


def create_access_token(
    subject: str,
    rol: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Firma un JWT con `sub` (id de usuario) y `rol`."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "rol": rol,
        "iat": datetime.now(UTC),
        "exp": expire,
        "iss": "labos-core",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un JWT. Lanza `jwt.InvalidTokenError` si no es válido."""
    return jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=[settings.algorithm],
        issuer="labos-core",
    )
