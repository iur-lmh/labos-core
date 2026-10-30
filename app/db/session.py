"""Engine y sesión de base de datos."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    connect_args=connect_args,
)


def get_session() -> Generator[Session, None, None]:
    """Dependencia FastAPI que entrega una sesión y la cierra al finalizar."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def create_db_and_tables() -> None:
    """Crea tablas sin migraciones. Solo para desarrollo/pruebas, nunca producción."""
    SQLModel.metadata.create_all(engine)
