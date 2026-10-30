"""Pruebas de evaluaciones, adjuntos y datasets."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.evaluacion import Evaluacion
from app.models.paciente import Paciente


def _evaluacion_payload(paciente_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "paciente_id": paciente_id,
        "tipo_protocolo": "salto_vertical",
        "fecha": datetime.now(UTC).isoformat(),
        "dispositivo_origen": "Biobit",
        "datos_raw": {
            "schema_version": "1.0",
            "metricas": {"altura_salto_cm": 34.2, "tiempo_vuelo_ms": 512},
        },
    }
    payload.update(overrides)
    return payload


def test_crear_y_leer_evaluacion(
    client: TestClient,
    profesional_headers: dict[str, str],
    paciente: Paciente,
) -> None:
    response = client.post(
        "/api/v1/evaluaciones",
        headers=profesional_headers,
        json=_evaluacion_payload(str(paciente.id)),
    )
    assert response.status_code == 201, response.text
    evaluacion = response.json()
    assert evaluacion["tipo_protocolo"] == "salto_vertical"
    assert evaluacion["datos_raw"]["metricas"]["altura_salto_cm"] == 34.2

    detail = client.get(f"/api/v1/evaluaciones/{evaluacion['id']}", headers=profesional_headers)
    assert detail.status_code == 200
    assert detail.json()["paciente_id"] == str(paciente.id)


def test_rechaza_pii_en_datos_raw(
    client: TestClient,
    profesional_headers: dict[str, str],
    paciente: Paciente,
) -> None:
    response = client.post(
        "/api/v1/evaluaciones",
        headers=profesional_headers,
        json=_evaluacion_payload(
            str(paciente.id), datos_raw={"metricas": {"altura": 30}, "nombre": "Ana"}
        ),
    )
    assert response.status_code == 422
    assert "identificación personal" in response.text


def test_filtros_listado(
    client: TestClient,
    profesional_headers: dict[str, str],
    paciente: Paciente,
    session: Session,
) -> None:
    session.add(
        Evaluacion(
            paciente_id=paciente.id,
            tipo_protocolo="marcha",
            dispositivo_origen="mDurance",
            datos_raw={},
        )
    )
    session.add(
        Evaluacion(
            paciente_id=paciente.id,
            tipo_protocolo="salto_vertical",
            dispositivo_origen="Biobit",
            fecha=datetime.now(UTC) - timedelta(days=2),
            datos_raw={},
        )
    )
    session.commit()

    response = client.get(
        "/api/v1/evaluaciones",
        headers=profesional_headers,
        params={"tipo_protocolo": "salto_vertical"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["dispositivo_origen"] == "Biobit"


def test_archivos_adjuntos(
    client: TestClient,
    profesional_headers: dict[str, str],
    paciente: Paciente,
) -> None:
    created = client.post(
        "/api/v1/evaluaciones",
        headers=profesional_headers,
        json=_evaluacion_payload(str(paciente.id)),
    )
    evaluacion_id = created.json()["id"]
    digest = hashlib.sha256(b"contenido-sintetico").hexdigest()

    attachment = client.post(
        f"/api/v1/evaluaciones/{evaluacion_id}/archivos",
        headers=profesional_headers,
        json={
            "url_storage": f"s3://labos-archivos/evaluaciones/{evaluacion_id}/salto.c3d",
            "tipo_archivo": "c3d",
            "hash_sha256": digest,
            "nombre_original": "salto.c3d",
            "tamano_bytes": 2048,
        },
    )
    assert attachment.status_code == 201, attachment.text
    assert attachment.json()["hash_sha256"] == digest

    duplicate = client.post(
        f"/api/v1/evaluaciones/{evaluacion_id}/archivos",
        headers=profesional_headers,
        json={
            "url_storage": f"s3://labos-archivos/evaluaciones/{evaluacion_id}/otro.c3d",
            "tipo_archivo": "c3d",
            "hash_sha256": digest,
        },
    )
    assert duplicate.status_code == 409

    listed = client.get(
        f"/api/v1/evaluaciones/{evaluacion_id}/archivos",
        headers=profesional_headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_hash_invalido(
    client: TestClient,
    profesional_headers: dict[str, str],
    paciente: Paciente,
) -> None:
    created = client.post(
        "/api/v1/evaluaciones",
        headers=profesional_headers,
        json=_evaluacion_payload(str(paciente.id)),
    )
    response = client.post(
        f"/api/v1/evaluaciones/{created.json()['id']}/archivos",
        headers=profesional_headers,
        json={
            "url_storage": "https://example.com/a.pdf",
            "tipo_archivo": "pdf",
            "hash_sha256": "no-es-un-hash",
        },
    )
    assert response.status_code == 422


def test_paciente_ve_solo_sus_evaluaciones(
    client: TestClient,
    paciente: Paciente,
    paciente_headers: dict[str, str],
    session: Session,
) -> None:
    own = Evaluacion(
        paciente_id=paciente.id,
        tipo_protocolo="salto_vertical",
        dispositivo_origen="Biobit",
        datos_raw={},
    )
    otro_paciente = Paciente(nombre="Otro", apellido="Sujeto", dni_anonimizado="otro-002")
    session.add(otro_paciente)
    session.commit()
    session.refresh(otro_paciente)
    ajeno = Evaluacion(
        paciente_id=otro_paciente.id,
        tipo_protocolo="marcha",
        dispositivo_origen="mDurance",
        datos_raw={},
    )
    session.add(own)
    session.add(ajeno)
    session.commit()
    session.refresh(own)
    session.refresh(ajeno)

    listed = client.get("/api/v1/evaluaciones", headers=paciente_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == str(own.id)

    forbidden = client.get(f"/api/v1/evaluaciones/{ajeno.id}", headers=paciente_headers)
    assert forbidden.status_code == 403


def test_resumen_y_dataset(
    client: TestClient,
    profesional_headers: dict[str, str],
    paciente: Paciente,
) -> None:
    created = client.post(
        "/api/v1/evaluaciones",
        headers=profesional_headers,
        json=_evaluacion_payload(str(paciente.id)),
    )
    assert created.status_code == 201

    resumen = client.get("/api/v1/investigaciones/resumen", headers=profesional_headers)
    assert resumen.status_code == 200
    assert resumen.json()["totales"]["evaluaciones"] == 1
    assert resumen.json()["por_protocolo"][0]["protocolo"] == "salto_vertical"

    dataset = client.get("/api/v1/investigaciones/dataset", headers=profesional_headers)
    assert dataset.status_code == 200
    body = dataset.json()
    assert body["total"] == 1
    assert body["items"][0]["paciente_seudonimo"] == paciente.dni_anonimizado
    assert "nombre" not in body["items"][0]
    assert body["items"][0]["datos_raw"]["metricas"]["altura_salto_cm"] == 34.2

    csv_response = client.get(
        "/api/v1/investigaciones/dataset",
        headers=profesional_headers,
        params={"formato": "csv"},
    )
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(csv_response.text)))
    assert rows[0]["paciente_seudonimo"] == paciente.dni_anonimizado
    assert json.loads(rows[0]["datos_raw_json"])["metricas"]["altura_salto_cm"] == 34.2
