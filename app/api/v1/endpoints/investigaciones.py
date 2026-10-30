"""Endpoints de investigación: agregados y datasets seudonimizados."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlmodel import col, select

from app.api.v1.deps import StaffUser
from app.db.session import SessionDep
from app.models.archivo import ArchivoAdjunto
from app.models.evaluacion import Evaluacion
from app.models.paciente import Paciente

router = APIRouter(prefix="/investigaciones", tags=["investigaciones"])

PII_KEYS = {
    "nombre",
    "apellido",
    "nombres",
    "apellidos",
    "dni",
    "documento",
    "email",
    "correo",
    "telefono",
    "teléfono",
    "direccion",
    "dirección",
    "fecha_nacimiento",
}


def _sanitizar(value: Any) -> Any:
    """Elimina recursivamente claves de identificación de los datos crudos."""
    if isinstance(value, dict):
        return {
            key: _sanitizar(nested)
            for key, nested in value.items()
            if str(key).strip().lower() not in PII_KEYS
        }
    if isinstance(value, list):
        return [_sanitizar(item) for item in value]
    return value


@router.get("/resumen", summary="Agregados para la mesa de I+D")
def resumen_investigacion(session: SessionDep, _: StaffUser) -> dict[str, Any]:
    total_pacientes = session.exec(select(func.count()).select_from(Paciente)).one()
    total_evaluaciones = session.exec(select(func.count()).select_from(Evaluacion)).one()
    total_archivos = session.exec(select(func.count()).select_from(ArchivoAdjunto)).one()
    bytes_almacenados = session.exec(
        select(func.coalesce(func.sum(ArchivoAdjunto.tamano_bytes), 0))
    ).one()
    ultima_fecha = session.exec(select(func.max(Evaluacion.fecha))).one()

    por_protocolo = session.exec(
        select(col(Evaluacion.tipo_protocolo), func.count(col(Evaluacion.id)))
        .group_by(col(Evaluacion.tipo_protocolo))
        .order_by(func.count(col(Evaluacion.id)).desc())
    ).all()
    por_dispositivo = session.exec(
        select(col(Evaluacion.dispositivo_origen), func.count(col(Evaluacion.id)))
        .group_by(col(Evaluacion.dispositivo_origen))
        .order_by(func.count(col(Evaluacion.id)).desc())
    ).all()

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "totales": {
            "pacientes": total_pacientes,
            "evaluaciones": total_evaluaciones,
            "archivos": total_archivos,
            "bytes_almacenados": int(bytes_almacenados or 0),
        },
        "ultima_evaluacion": ultima_fecha.isoformat() if ultima_fecha else None,
        "por_protocolo": [
            {"protocolo": protocolo, "total": total} for protocolo, total in por_protocolo
        ],
        "por_dispositivo": [
            {"dispositivo": dispositivo, "total": total} for dispositivo, total in por_dispositivo
        ],
    }


@router.get("/dataset", summary="Exportar dataset seudonimizado (JSON o CSV)")
def exportar_dataset(
    session: SessionDep,
    _: StaffUser,
    formato: Annotated[Literal["json", "csv"], Query()] = "json",
    tipo_protocolo: Annotated[str | None, Query(max_length=60)] = None,
    dispositivo: Annotated[str | None, Query(max_length=80)] = None,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
) -> Any:
    statement = (
        select(Evaluacion, Paciente)
        .join(Paciente, col(Evaluacion.paciente_id) == col(Paciente.id))
        .order_by(col(Evaluacion.fecha).desc())
    )
    if tipo_protocolo:
        statement = statement.where(Evaluacion.tipo_protocolo == tipo_protocolo)
    if dispositivo:
        statement = statement.where(Evaluacion.dispositivo_origen == dispositivo)
    if desde:
        statement = statement.where(Evaluacion.fecha >= desde)
    if hasta:
        statement = statement.where(Evaluacion.fecha <= hasta)

    rows = session.exec(statement).all()
    registros = [
        {
            "evaluacion_id": str(evaluacion.id),
            "paciente_seudonimo": paciente.dni_anonimizado,
            "tipo_protocolo": evaluacion.tipo_protocolo,
            "fecha": evaluacion.fecha.isoformat(),
            "dispositivo_origen": evaluacion.dispositivo_origen,
            "datos_raw": _sanitizar(evaluacion.datos_raw),
        }
        for evaluacion, paciente in rows
    ]

    if formato == "json":
        return {
            "dataset_version": "1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "total": len(registros),
            "filtros": {
                "tipo_protocolo": tipo_protocolo,
                "dispositivo": dispositivo,
                "desde": desde.isoformat() if desde else None,
                "hasta": hasta.isoformat() if hasta else None,
            },
            "items": registros,
        }

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "evaluacion_id",
            "paciente_seudonimo",
            "tipo_protocolo",
            "fecha",
            "dispositivo_origen",
            "datos_raw_json",
        ],
    )
    writer.writeheader()
    for registro in registros:
        writer.writerow(
            {
                **{key: registro[key] for key in registro if key != "datos_raw"},
                "datos_raw_json": json.dumps(
                    registro["datos_raw"], ensure_ascii=False, separators=(",", ":")
                ),
            }
        )

    filename = f"labos_dataset_{datetime.now(UTC):%Y%m%d_%H%M%S}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
