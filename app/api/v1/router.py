"""Router agregado de la API v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, evaluaciones, investigaciones, pacientes

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(pacientes.router)
api_router.include_router(evaluaciones.router)
api_router.include_router(investigaciones.router)
