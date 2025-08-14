"""add test_definitions & test_results

Revision ID: 5366d3563e34
Revises: dec3d9e88540
Create Date: 2025-08-13 17:56:41.435775
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "5366d3563e34"
down_revision: Union[str, None] = "dec3d9e88540"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- test_definitions ----
    op.create_table(
        "test_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # exercises.id is INTEGER
        sa.Column("exercise_id", sa.Integer(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_test_definitions_id"), "test_definitions", ["id"], unique=False)

    # ---- test_results ----
    op.create_table(
        "test_results",
        sa.Column("id", sa.Integer(), nullable=False),
        # users.id is VARCHAR(36)
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["test_definitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_results_id"), "test_results", ["id"], unique=False)
    op.create_index(op.f("ix_test_results_user_id"), "test_results", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_test_results_user_id"), table_name="test_results")
    op.drop_index(op.f("ix_test_results_id"), table_name="test_results")
    op.drop_table("test_results")

    op.drop_index(op.f("ix_test_definitions_id"), table_name="test_definitions")
    op.drop_table("test_definitions")
