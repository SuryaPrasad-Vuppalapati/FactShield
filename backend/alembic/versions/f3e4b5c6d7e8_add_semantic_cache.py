"""add_semantic_cache

Revision ID: f3e4b5c6d7e8
Revises: c1f2aa82c512
Create Date: 2026-07-05 15:30:00.000000

"""

from collections.abc import Sequence

import pgvector
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3e4b5c6d7e8"
down_revision: str | Sequence[str] | None = "c1f2aa82c512"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "semantic_cache",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column(
            "query_embedding", pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=False
        ),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("generation_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generation_id"], ["generations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("semantic_cache")
