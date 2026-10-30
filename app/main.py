"""Arranque de la API LabOS."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import SessionDep, create_db_and_tables
from app.services.bootstrap import seed_admin

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("labos.core")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_tables:
        logger.warning("AUTO_CREATE_TABLES activo: creando tablas sin migraciones")
        create_db_and_tables()

    if settings.environment != "test":
        seed_admin()

    logger.info("LabOS API iniciada en entorno %s", settings.environment)
    yield
    logger.info("LabOS API detenida")


app = FastAPI(
    title=settings.project_name,
    description=settings.project_description,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, __: IntegrityError) -> JSONResponse:
    logger.warning("Conflicto de integridad en base de datos")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "La operación entra en conflicto con datos existentes"},
    )


@app.get("/", tags=["salud"], summary="Metadatos de la API")
def root() -> dict[str, str]:
    return {
        "service": settings.project_name,
        "version": settings.version,
        "docs": "/docs",
        "api": settings.api_v1_prefix,
    }


@app.get("/health", tags=["salud"], summary="Liveness")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "labos-core", "version": settings.version}


@app.get("/health/ready", tags=["salud"], summary="Readiness (incluye base de datos)")
def readiness(session: SessionDep) -> dict[str, str]:
    session.exec(select(1)).one()
    return {"status": "ready", "database": "ok"}
