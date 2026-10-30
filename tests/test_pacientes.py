"""Pruebas de pacientes y permisos."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.paciente import Paciente


def _payload(dni: str = "nuevo-paciente-001") -> dict[str, object]:
    return {
        "nombre": "Juan",
        "apellido": "Pérez",
        "fecha_nacimiento": "1990-05-17",
        "dni_anonimizado": dni,
        "metadata": {"deporte": "fútbol", "categoria": "amateur"},
    }


def test_crear_y_leer_paciente(client: TestClient, profesional_headers: dict[str, str]) -> None:
    response = client.post("/api/v1/pacientes", headers=profesional_headers, json=_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["metadata"] == {"deporte": "fútbol", "categoria": "amateur"}
    assert body["dni_anonimizado"] == "nuevo-paciente-001"

    detail = client.get(f"/api/v1/pacientes/{body['id']}", headers=profesional_headers)
    assert detail.status_code == 200
    assert detail.json()["apellido"] == "Pérez"


def test_dni_duplicado(
    client: TestClient, profesional_headers: dict[str, str], paciente: Paciente
) -> None:
    response = client.post(
        "/api/v1/pacientes",
        headers=profesional_headers,
        json=_payload(paciente.dni_anonimizado),
    )
    assert response.status_code == 409


def test_buscar_paciente(
    client: TestClient, profesional_headers: dict[str, str], paciente: Paciente
) -> None:
    response = client.get("/api/v1/pacientes", headers=profesional_headers, params={"q": "Góm"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(paciente.id)


def test_actualizar_paciente(
    client: TestClient, profesional_headers: dict[str, str], paciente: Paciente
) -> None:
    response = client.patch(
        f"/api/v1/pacientes/{paciente.id}",
        headers=profesional_headers,
        json={"nombre": "Ana María", "metadata": {"deporte": "trail"}},
    )
    assert response.status_code == 200
    assert response.json()["nombre"] == "Ana María"
    assert response.json()["metadata"] == {"deporte": "trail"}


def test_paciente_solo_ve_su_registro(
    client: TestClient,
    paciente_headers: dict[str, str],
    paciente: Paciente,
    session: Session,
) -> None:
    own = client.get(f"/api/v1/pacientes/{paciente.id}", headers=paciente_headers)
    assert own.status_code == 200

    otro = Paciente(nombre="Otro", apellido="Sujeto", dni_anonimizado="otro-001")
    session.add(otro)
    session.commit()
    session.refresh(otro)

    forbidden = client.get(f"/api/v1/pacientes/{otro.id}", headers=paciente_headers)
    assert forbidden.status_code == 403


def test_paciente_no_puede_listar(client: TestClient, paciente_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/pacientes", headers=paciente_headers)
    assert response.status_code == 403


def test_solo_admin_elimina(
    client: TestClient,
    profesional_headers: dict[str, str],
    admin_headers: dict[str, str],
    paciente: Paciente,
) -> None:
    forbidden = client.delete(f"/api/v1/pacientes/{paciente.id}", headers=profesional_headers)
    assert forbidden.status_code == 403

    deleted = client.delete(f"/api/v1/pacientes/{paciente.id}", headers=admin_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/pacientes/{paciente.id}", headers=admin_headers).status_code == 404


def test_sin_token(client: TestClient) -> None:
    assert client.get("/api/v1/pacientes").status_code == 401
