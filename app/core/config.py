"""Configuración central tipada.

Toda variable de entorno se declara aquí. Nunca leer `os.environ` directamente en el
resto del código: facilita tests y despliegues.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicación ---------------------------------------------------------
    project_name: str = "LabOS API"
    project_description: str = (
        "API de gestión biomecánica e investigación del Laboratorio de Movimiento Humano"
    )
    version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    auto_create_tables: bool = False

    # --- Seguridad ----------------------------------------------------------
    secret_key: SecretStr = SecretStr("dev-only-change-me-with-a-random-48-byte-string-please")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Base de datos ------------------------------------------------------
    database_url: str = "postgresql+psycopg://labos:labos_dev_password@localhost:5432/labos"
    database_echo: bool = False

    # --- Bootstrap ----------------------------------------------------------
    admin_email: str = "admin@labos.ar"
    admin_password: SecretStr = SecretStr("LabosAdmin123!")
    admin_nombre: str = "Administrador LabOS"

    # --- Object storage (S3 compatible: R2 / MinIO) -------------------------
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: SecretStr = SecretStr("")
    s3_bucket: str = "labos-archivos"
    s3_region: str = "auto"

    # --- Límites de dominio -------------------------------------------------
    max_datos_raw_bytes: int = 1_000_000
    max_archivo_bytes: int = 500 * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        """Orígenes CORS como lista, ignorando entradas vacías."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def storage_configured(self) -> bool:
        return bool(self.s3_endpoint_url and self.s3_access_key_id and self.s3_bucket)

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> Settings:
        if self.environment == "production":
            secret = self.secret_key.get_secret_value()
            if len(secret) < 32 or "change-me" in secret:
                raise ValueError(
                    "SECRET_KEY debe tener al menos 32 caracteres y no ser el valor de "
                    "desarrollo en producción."
                )
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS no puede contener '*' en producción.")
        return self

    database_pool_size: int = Field(default=5, ge=1, le=50)


@lru_cache
def get_settings() -> Settings:
    """Instancia única de configuración (cacheada)."""
    return Settings()


settings = get_settings()
