"""Fixtures compartidas de la suite backend."""

from __future__ import annotations

import os
from collections.abc import Generator

os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-32-characters"
os.environ["ADMIN_EMAIL"] = ""
os.environ["ADMIN_PASSWORD"] = ""
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AUTO_CREATE_TABLES"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import hash_password
from app.db import base  # noqa: F401 - registra modelos
from app.db.session import get_session
from app.main import app
from app.models.paciente import Paciente
from app.models.usuario import Rol, Usuario

PASSWORD = "TestPassword123!"


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(session: Session) -> Generator[TestClient, None, None]:
    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(
    session: Session,
    email: str,
    rol: Rol,
    *,
    paciente_id=None,
    activo: bool = True,
) -> Usuario:
    user = Usuario(
        email=email,
        hashed_password=hash_password(PASSWORD),
        nombre_completo=f"Usuario {rol.value}",
        rol=rol,
        paciente_id=paciente_id,
        activo=activo,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def login_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def admin_user(session: Session) -> Usuario:
    return create_user(session, "admin@labos.ar", Rol.ADMIN)


@pytest.fixture()
def profesional_user(session: Session) -> Usuario:
    return create_user(session, "pro@labos.ar", Rol.PROFESIONAL)


@pytest.fixture()
def paciente(session: Session) -> Paciente:
    patient = Paciente(
        nombre="Ana",
        apellido="Gómez",
        dni_anonimizado="ana-gomez-001",
        metadata_={"deporte": "running"},
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@pytest.fixture()
def paciente_user(session: Session, paciente: Paciente) -> Usuario:
    return create_user(
        session,
        "paciente@labos.ar",
        Rol.PACIENTE,
        paciente_id=paciente.id,
    )


@pytest.fixture()
def admin_headers(client: TestClient, admin_user: Usuario) -> dict[str, str]:
    return login_headers(client, admin_user.email)


@pytest.fixture()
def profesional_headers(client: TestClient, profesional_user: Usuario) -> dict[str, str]:
    return login_headers(client, profesional_user.email)


@pytest.fixture()
def paciente_headers(client: TestClient, paciente_user: Usuario) -> dict[str, str]:
    return login_headers(client, paciente_user.email)
