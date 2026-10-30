"""Endpoints de evaluaciones y archivos adjuntos."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlmodel import col, select

from app.api.v1.deps import AdminUser, CurrentUser, StaffUser
from app.db.session import SessionDep
from app.models.archivo import ArchivoAdjunto
from app.models.evaluacion import Evaluacion
from app.models.paciente import Paciente
from app.models.usuario import Rol
from app.schemas.common import Paginated
from app.schemas.evaluacion import (
    ArchivoCreate,
    ArchivoRead,
    EvaluacionCreate,
    EvaluacionRead,
)

router = APIRouter(prefix="/evaluaciones", tags=["evaluaciones"])


def _get_evaluacion_or_404(session: SessionDep, evaluacion_id: uuid.UUID) -> Evaluacion:
    evaluacion = session.get(Evaluacion, evaluacion_id)
    if evaluacion is None:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    return evaluacion


def _assert_puede_ver(current_user: CurrentUser, evaluacion: Evaluacion) -> None:
    if current_user.rol == Rol.PACIENTE and current_user.paciente_id != evaluacion.paciente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a esta evaluación",
        )


@router.get("", response_model=Paginated[EvaluacionRead], summary="Listar evaluaciones")
def list_evaluaciones(
    session: SessionDep,
    current_user: CurrentUser,
    paciente_id: Annotated[uuid.UUID | None, Query()] = None,
    tipo_protocolo: Annotated[str | None, Query(max_length=60)] = None,
    dispositivo: Annotated[str | None, Query(max_length=80)] = None,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Paginated[EvaluacionRead]:
    if current_user.rol == Rol.PACIENTE:
        if current_user.paciente_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta no está vinculada a un paciente",
            )
        paciente_id = current_user.paciente_id

    statement = select(Evaluacion)
    if paciente_id is not None:
        statement = statement.where(Evaluacion.paciente_id == paciente_id)
    if tipo_protocolo:
        statement = statement.where(Evaluacion.tipo_protocolo == tipo_protocolo)
    if dispositivo:
        statement = statement.where(Evaluacion.dispositivo_origen == dispositivo)
    if desde:
        statement = statement.where(Evaluacion.fecha >= desde)
    if hasta:
        statement = statement.where(Evaluacion.fecha <= hasta)

    total = session.exec(select(func.count()).select_from(statement.subquery())).one()
    evaluaciones = session.exec(
        statement.order_by(col(Evaluacion.fecha).desc()).offset(skip).limit(limit)
    ).all()
    return Paginated[EvaluacionRead](
        items=[EvaluacionRead.model_validate(item) for item in evaluaciones],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=EvaluacionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar evaluación",
)
def create_evaluacion(
    payload: EvaluacionCreate,
    session: SessionDep,
    _: StaffUser,
) -> Evaluacion:
    paciente = session.get(Paciente, payload.paciente_id)
    if paciente is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    evaluacion = Evaluacion(
        paciente_id=payload.paciente_id,
        tipo_protocolo=payload.tipo_protocolo.value,
        fecha=payload.fecha,
        dispositivo_origen=payload.dispositivo_origen.strip(),
        datos_raw=payload.datos_raw,
    )
    session.add(evaluacion)
    session.commit()
    session.refresh(evaluacion)
    return evaluacion


@router.get("/{evaluacion_id}", response_model=EvaluacionRead, summary="Detalle de evaluación")
def get_evaluacion(
    evaluacion_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Evaluacion:
    evaluacion = _get_evaluacion_or_404(session, evaluacion_id)
    _assert_puede_ver(current_user, evaluacion)
    return evaluacion


@router.delete(
    "/{evaluacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Eliminar evaluación (solo admin)",
)
def delete_evaluacion(
    evaluacion_id: uuid.UUID,
    session: SessionDep,
    _: AdminUser,
) -> Response:
    evaluacion = _get_evaluacion_or_404(session, evaluacion_id)
    session.delete(evaluacion)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{evaluacion_id}/archivos",
    response_model=list[ArchivoRead],
    summary="Listar archivos de una evaluación",
)
def list_archivos(
    evaluacion_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[ArchivoAdjunto]:
    evaluacion = _get_evaluacion_or_404(session, evaluacion_id)
    _assert_puede_ver(current_user, evaluacion)
    return list(
        session.exec(
            select(ArchivoAdjunto)
            .where(ArchivoAdjunto.evaluacion_id == evaluacion_id)
            .order_by(col(ArchivoAdjunto.created_at))
        ).all()
    )


@router.post(
    "/{evaluacion_id}/archivos",
    response_model=ArchivoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar metadatos de un archivo subido a storage",
)
def create_archivo(
    evaluacion_id: uuid.UUID,
    payload: ArchivoCreate,
    session: SessionDep,
    _: StaffUser,
) -> ArchivoAdjunto:
    evaluacion = _get_evaluacion_or_404(session, evaluacion_id)
    duplicate = session.exec(
        select(ArchivoAdjunto).where(
            ArchivoAdjunto.evaluacion_id == evaluacion.id,
            ArchivoAdjunto.hash_sha256 == payload.hash_sha256,
        )
    ).first()
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese archivo ya está registrado para la evaluación",
        )

    archivo = ArchivoAdjunto(
        evaluacion_id=evaluacion.id,
        url_storage=payload.url_storage,
        tipo_archivo=payload.tipo_archivo.value,
        hash_sha256=payload.hash_sha256,
        nombre_original=payload.nombre_original,
        tamano_bytes=payload.tamano_bytes,
    )
    session.add(archivo)
    session.commit()
    session.refresh(archivo)
    return archivo
