"""Utilidades de storage compatibles con S3 (R2 / MinIO).

La firma de URLs se habilitará en la fase 1 con `boto3`; por ahora se centralizan las
convenciones de nombres y la verificación de integridad.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def build_object_key(evaluacion_id: uuid.UUID, filename: str) -> str:
    """Genera una clave estable y sin PII para un adjunto."""
    clean = SAFE_NAME.sub("_", Path(filename).name).strip("._") or "archivo"
    return f"evaluaciones/{evaluacion_id}/{uuid.uuid4().hex[:12]}-{clean}"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calcula SHA-256 de un archivo sin cargarlo completo en memoria."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[a-fA-F0-9]{64}", value))
