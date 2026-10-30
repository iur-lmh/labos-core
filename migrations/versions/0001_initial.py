"""Esquema inicial LabOS: pacientes, evaluaciones, archivos y usuarios.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pacientes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("apellido", sa.String(length=120), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("dni_anonimizado", sa.String(length=64), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pacientes"),
    )
    op.create_index("ix_pacientes_nombre", "pacientes", ["nombre"])
    op.create_index("ix_pacientes_apellido", "pacientes", ["apellido"])
    op.create_index(
        "ix_pacientes_dni_anonimizado",
        "pacientes",
        ["dni_anonimizado"],
        unique=True,
    )

    op.create_table(
        "evaluaciones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("paciente_id", sa.Uuid(), nullable=False),
        sa.Column("tipo_protocolo", sa.String(length=60), nullable=False),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dispositivo_origen", sa.String(length=80), nullable=False),
        sa.Column(
            "datos_raw",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["paciente_id"],
            ["pacientes.id"],
            name="fk_evaluaciones_paciente_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluaciones"),
    )
    op.create_index("ix_evaluaciones_paciente_id", "evaluaciones", ["paciente_id"])
    op.create_index("ix_evaluaciones_tipo_protocolo", "evaluaciones", ["tipo_protocolo"])
    op.create_index("ix_evaluaciones_fecha", "evaluaciones", ["fecha"])
    op.create_index(
        "ix_evaluaciones_dispositivo_origen", "evaluaciones", ["dispositivo_origen"]
    )
    op.create_index(
        "ix_evaluaciones_paciente_fecha",
        "evaluaciones",
        ["paciente_id", "fecha"],
    )

    op.create_table(
        "archivos_adjuntos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluacion_id", sa.Uuid(), nullable=False),
        sa.Column("url_storage", sa.String(length=2048), nullable=False),
        sa.Column("tipo_archivo", sa.String(length=16), nullable=False),
        sa.Column("hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("nombre_original", sa.String(length=255), nullable=True),
        sa.Column("tamano_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["evaluacion_id"],
            ["evaluaciones.id"],
            name="fk_archivos_evaluacion_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_archivos_adjuntos"),
    )
    op.create_index(
        "ix_archivos_adjuntos_evaluacion_id", "archivos_adjuntos", ["evaluacion_id"]
    )
    op.create_index("ix_archivos_adjuntos_tipo_archivo", "archivos_adjuntos", ["tipo_archivo"])
    op.create_index("ix_archivos_adjuntos_hash_sha256", "archivos_adjuntos", ["hash_sha256"])

    rol_enum = sa.Enum("admin", "profesional", "paciente", name="rol_usuario")
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("nombre_completo", sa.String(length=160), nullable=False),
        sa.Column("rol", rol_enum, server_default="profesional", nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("paciente_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["paciente_id"],
            ["pacientes.id"],
            name="fk_usuarios_paciente_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_usuarios"),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)
    op.create_index("ix_usuarios_rol", "usuarios", ["rol"])
    op.create_index("ix_usuarios_paciente_id", "usuarios", ["paciente_id"])


def downgrade() -> None:
    op.drop_index("ix_usuarios_paciente_id", table_name="usuarios")
    op.drop_index("ix_usuarios_rol", table_name="usuarios")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
    sa.Enum(name="rol_usuario").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_archivos_adjuntos_hash_sha256", table_name="archivos_adjuntos")
    op.drop_index("ix_archivos_adjuntos_tipo_archivo", table_name="archivos_adjuntos")
    op.drop_index("ix_archivos_adjuntos_evaluacion_id", table_name="archivos_adjuntos")
    op.drop_table("archivos_adjuntos")

    op.drop_index("ix_evaluaciones_paciente_fecha", table_name="evaluaciones")
    op.drop_index("ix_evaluaciones_dispositivo_origen", table_name="evaluaciones")
    op.drop_index("ix_evaluaciones_fecha", table_name="evaluaciones")
    op.drop_index("ix_evaluaciones_tipo_protocolo", table_name="evaluaciones")
    op.drop_index("ix_evaluaciones_paciente_id", table_name="evaluaciones")
    op.drop_table("evaluaciones")

    op.drop_index("ix_pacientes_dni_anonimizado", table_name="pacientes")
    op.drop_index("ix_pacientes_apellido", table_name="pacientes")
    op.drop_index("ix_pacientes_nombre", table_name="pacientes")
    op.drop_table("pacientes")
