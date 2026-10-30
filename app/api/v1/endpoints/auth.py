"""Endpoints de autenticación y gestión de usuarios."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlmodel import select

from app.api.v1.deps import AdminUser, CurrentUser
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import SessionDep
from app.models.paciente import Paciente
from app.models.usuario import Rol, Usuario
from app.schemas.common import Paginated
from app.schemas.usuario import Token, UsuarioCreate, UsuarioRead, UsuarioUpdate

router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.post("/login", response_model=Token, summary="Iniciar sesión (OAuth2 password flow)")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> Token:
    email = form_data.username.strip().lower()
    user = session.exec(select(Usuario).where(func.lower(Usuario.email) == email)).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está desactivada",
        )

    token = create_access_token(subject=str(user.id), rol=user.rol.value)
    return Token(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UsuarioRead, summary="Perfil del usuario autenticado")
def read_me(current_user: CurrentUser) -> Usuario:
    return current_user


@router.get(
    "/usuarios",
    response_model=Paginated[UsuarioRead],
    summary="Listar usuarios (solo administradores)",
)
def list_usuarios(
    session: SessionDep,
    _: AdminUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Paginated[UsuarioRead]:
    total = session.exec(select(func.count()).select_from(Usuario)).one()
    usuarios = session.exec(
        select(Usuario).order_by(Usuario.nombre_completo).offset(skip).limit(limit)
    ).all()
    return Paginated[UsuarioRead](
        items=[UsuarioRead.model_validate(user) for user in usuarios],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/usuarios",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario (solo administradores)",
)
def create_usuario(payload: UsuarioCreate, session: SessionDep, _: AdminUser) -> Usuario:
    email = payload.email.strip().lower()
    existing = session.exec(select(Usuario).where(func.lower(Usuario.email) == email)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )

    if payload.rol == Rol.PACIENTE:
        if payload.paciente_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un usuario con rol paciente requiere paciente_id",
            )
        paciente = session.get(Paciente, payload.paciente_id)
        if paciente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente no encontrado",
            )

    user = Usuario(
        email=email,
        hashed_password=hash_password(payload.password),
        nombre_completo=payload.nombre_completo.strip(),
        rol=payload.rol,
        paciente_id=payload.paciente_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.patch(
    "/usuarios/{usuario_id}",
    response_model=UsuarioRead,
    summary="Actualizar o desactivar usuario (solo administradores)",
)
def update_usuario(
    usuario_id: uuid.UUID,
    payload: UsuarioUpdate,
    session: SessionDep,
    current_user: AdminUser,
) -> Usuario:
    user = session.get(Usuario, usuario_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    changes = payload.model_dump(exclude_unset=True)
    if user.id == current_user.id and changes.get("activo") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No es posible desactivar la propia cuenta",
        )

    if changes.get("nombre_completo"):
        user.nombre_completo = str(changes["nombre_completo"]).strip()
    if "activo" in changes:
        user.activo = bool(changes["activo"])
    if changes.get("password"):
        user.hashed_password = hash_password(str(changes["password"]))

    session.add(user)
    session.commit()
    session.refresh(user)
    return user
