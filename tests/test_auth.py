"""Pruebas de autenticación y RBAC de usuarios."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token
from app.models.usuario import Rol, Usuario
from tests.conftest import PASSWORD, login_headers


def test_login_y_perfil(client: TestClient, admin_user: Usuario) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == admin_user.email
    assert me.json()["rol"] == "admin"


def test_login_incorrecto(client: TestClient, admin_user: Usuario) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": "incorrecta"},
    )
    assert response.status_code == 401


def test_token_expirado(client: TestClient, admin_user: Usuario) -> None:
    token = create_access_token(
        subject=str(admin_user.id),
        rol=admin_user.rol.value,
        expires_delta=timedelta(seconds=-30),
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_crear_usuario_admin(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/auth/usuarios",
        headers=admin_headers,
        json={
            "email": "nuevo@labos.ar",
            "password": "OtraPassword123!",
            "nombre_completo": "Nuevo Profesional",
            "rol": "profesional",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "nuevo@labos.ar"
    assert response.json()["rol"] == "profesional"


def test_crear_usuario_prohibido(client: TestClient, profesional_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/auth/usuarios",
        headers=profesional_headers,
        json={
            "email": "otro@labos.ar",
            "password": "OtraPassword123!",
            "nombre_completo": "Otro",
            "rol": "admin",
        },
    )
    assert response.status_code == 403


def test_paciente_requiere_vinculo(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/auth/usuarios",
        headers=admin_headers,
        json={
            "email": "sinvinculo@labos.ar",
            "password": "OtraPassword123!",
            "nombre_completo": "Sin Vínculo",
            "rol": "paciente",
        },
    )
    assert response.status_code == 400


def test_usuario_inactivo_no_puede_login(client: TestClient, session: Session) -> None:
    from tests.conftest import create_user

    user = create_user(session, "inactivo@labos.ar", Rol.PROFESIONAL, activo=False)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": PASSWORD},
    )
    assert response.status_code == 403


def test_admin_no_puede_desactivarse(
    client: TestClient, admin_user: Usuario, admin_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"/api/v1/auth/usuarios/{admin_user.id}",
        headers=admin_headers,
        json={"activo": False},
    )
    assert response.status_code == 400


def test_login_headers_fixture(client: TestClient, profesional_user: Usuario) -> None:
    assert login_headers(client, profesional_user.email)["Authorization"].startswith("Bearer ")
