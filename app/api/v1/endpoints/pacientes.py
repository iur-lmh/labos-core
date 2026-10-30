"""Endpoints de pacientes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, or_
from sqlmodel import col, select

from app.api.v1.deps import AdminUser, CurrentUser, StaffUser
from app.db.session import SessionDep
from app.models.paciente import Paciente
from app.models.usuario import Rol
from app.schemas.common import Paginated
from app.schemas.paciente import PacienteCreate, PacienteRead, PacienteUpdate

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


def _get_or_404(session: SessionDep, paciente_id: uuid.UUID) -> Paciente:
    paciente = session.get(Paciente, paciente_id)
    if paciente is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return paciente


def _assert_puede_ver(current_user: CurrentUser, paciente: Paciente) -> None:
    if current_user.rol == Rol.PACIENTE and current_user.paciente_id != paciente.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a este paciente",
        )


@router.get("", response_model=Paginated[PacienteRead], summary="Listar/buscar pacientes")
def list_pacientes(
    session: SessionDep,
    _: StaffUser,
    q: Annotated[str | None, Query(max_length=120)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Paginated[PacienteRead]:
    statement = select(Paciente)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                col(Paciente.nombre).ilike(pattern),
                col(Paciente.apellido).ilike(pattern),
                col(Paciente.dni_anonimizado).ilike(pattern),
            )
        )

    total = session.exec(select(func.count()).select_from(statement.subquery())).one()
    pacientes = session.exec(
        statement.order_by(col(Paciente.apellido), col(Paciente.nombre)).offset(skip).limit(limit)
    ).all()
    return Paginated[PacienteRead](
        items=[PacienteRead.model_validate(p) for p in pacientes],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=PacienteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear paciente",
)
def create_paciente(
    payload: PacienteCreate,
    session: SessionDep,
    _: StaffUser,
) -> Paciente:
    existing = session.exec(
        select(Paciente).where(Paciente.dni_anonimizado == payload.dni_anonimizado)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un paciente con ese identificador seudonimizado",
        )

    data = payload.model_dump()
    metadata = data.pop("metadata")
    paciente = Paciente(**data, metadata_=metadata)
    session.add(paciente)
    session.commit()
    session.refresh(paciente)
    return paciente


@router.get("/{paciente_id}", response_model=PacienteRead, summary="Detalle de paciente")
def get_paciente(
    paciente_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Paciente:
    paciente = _get_or_404(session, paciente_id)
    _assert_puede_ver(current_user, paciente)
    return paciente


@router.patch("/{paciente_id}", response_model=PacienteRead, summary="Editar paciente")
def update_paciente(
    paciente_id: uuid.UUID,
    payload: PacienteUpdate,
    session: SessionDep,
    _: StaffUser,
) -> Paciente:
    paciente = _get_or_404(session, paciente_id)
    changes = payload.model_dump(exclude_unset=True)

    if "dni_anonimizado" in changes and changes["dni_anonimizado"] != paciente.dni_anonimizado:
        duplicate = session.exec(
            select(Paciente).where(Paciente.dni_anonimizado == changes["dni_anonimizado"])
        ).first()
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un paciente con ese identificador seudonimizado",
            )

    if "metadata" in changes:
        paciente.metadata_ = changes.pop("metadata") or {}
    for field, value in changes.items():
        setattr(paciente, field, value)
    paciente.updated_at = datetime.now(UTC)

    session.add(paciente)
    session.commit()
    session.refresh(paciente)
    return paciente


@router.delete(
    "/{paciente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Eliminar paciente y sus evaluaciones (solo admin)",
)
def delete_paciente(
    paciente_id: uuid.UUID,
    session: SessionDep,
    _: AdminUser,
) -> Response:
    paciente = _get_or_404(session, paciente_id)
    session.delete(paciente)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
