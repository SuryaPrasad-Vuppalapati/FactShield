"""Add source_type to semantic_cache

Revision ID: 7a8b9c0d1e2f
Revises: 322cf791b35b
Create Date: 2026-07-07 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7a8b9c0d1e2f"
down_revision: str | Sequence[str] | None = "322cf791b35b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "semantic_cache",
        sa.Column("source_type", sa.String(), server_default="document", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("semantic_cache", "source_type")
