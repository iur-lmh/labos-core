"""Plantilla de migración Alembic."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "${up_revision}"
down_revision: str | None = "${down_revision}"
branch_labels: str | Sequence[str] | None = "${branch_labels}"
depends_on: str | Sequence[str] | None = "${depends_on}"


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
