# LabOS Core — API biomecánica

API REST del Laboratorio de Movimiento Humano (IUR — UCASAL): ingestión de datos
biomecánicos, autenticación JWT, RBAC y exportación de datasets seudonimizados.

- **Stack**: Python 3.11+, FastAPI, Pydantic v2, SQLModel, PostgreSQL 16, Alembic.
- **Docs**: `http://localhost:8000/docs`
- **Contrato**: [`../docs/API.md`](../docs/API.md)

## Inicio rápido

### Docker (recomendado)

Desde la raíz del monorepo:

```bash
cp .env.example .env
docker compose up --build
```

### Local

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env
# Ajustar DATABASE_URL a una PostgreSQL local
alembic upgrade head
uvicorn app.main:app --reload
```

Variables clave: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `ADMIN_*` y `S3_*`.
Ver `.env.example`.

## Estructura

```text
app/
├── api/v1/
│   ├── deps.py              # JWT actual + RBAC
│   ├── endpoints/           # auth, pacientes, evaluaciones, investigaciones
│   └── router.py
├── core/                    # config, security
├── db/                      # session, metadata, tipos JSONB
├── models/                  # SQLModel: paciente, evaluación, archivo, usuario
├── schemas/                 # Pydantic v2
├── services/                # bootstrap, storage
└── main.py
migrations/                  # Alembic
tests/                       # pytest + SQLite
```

## Roles

| Rol | Acceso |
|---|---|
| `admin` | Todo, incluyendo usuarios y borrados |
| `profesional` | Pacientes, evaluaciones, datasets |
| `paciente` | Solo sus propios datos |

El administrador inicial se crea una sola vez si `ADMIN_EMAIL`/`ADMIN_PASSWORD` están
definidos y la tabla de usuarios está vacía. **Cambiar la contraseña tras el primer
acceso.**

## Endpoints principales

| Método | Ruta |
|---|---|
| POST | `/api/v1/auth/login` (form: `username`, `password`) |
| GET | `/api/v1/auth/me` |
| GET/POST | `/api/v1/pacientes` |
| GET/PATCH/DELETE | `/api/v1/pacientes/{id}` |
| GET/POST | `/api/v1/evaluaciones` |
| GET/DELETE | `/api/v1/evaluaciones/{id}` |
| GET/POST | `/api/v1/evaluaciones/{id}/archivos` |
| GET | `/api/v1/investigaciones/resumen` |
| GET | `/api/v1/investigaciones/dataset?formato=csv` |

## Calidad

```bash
ruff check .
ruff format --check .
mypy app
pytest --cov=app
```

## Migraciones

```bash
alembic upgrade head
alembic revision --autogenerate -m "descripcion"
alembic downgrade -1
```

En producción, ejecutar `alembic upgrade head` antes de arrancar la API. El Dockerfile
lo hace automáticamente.

## Seguridad

- Argon2id para contraseñas; JWT HS256 con expiración.
- `datos_raw` rechaza claves de PII conocidas y limita a 1 MB.
- Las exportaciones eliminan PII y conservan solo el seudónimo.
- No almacenar binarios en PostgreSQL: usar R2/S3 y registrar URL + SHA-256.
- Reportar vulnerabilidades según
  [`SECURITY.md`](https://github.com/iur-lmh/.github/blob/main/SECURITY.md).

## Licencia

MIT.
