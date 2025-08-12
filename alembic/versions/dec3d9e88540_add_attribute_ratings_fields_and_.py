"""Add attribute ratings fields and history table

Revision ID: dec3d9e88540
Revises: 0ddf04ffdc81
Create Date: 2025-08-12 15:43:33.249066
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "dec3d9e88540"
down_revision: Union[str, None] = "0ddf04ffdc81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- New time-series table for ability snapshots ---
    op.create_table(
        "user_attribute_ratings_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False, index=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ratings", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_attr_hist_user_id",
        "user_attribute_ratings_history",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_user_attr_hist_recorded_at",
        "user_attribute_ratings_history",
        ["recorded_at"],
        unique=False,
    )

    # --- Snapshot columns on users ---
    op.add_column(
        "users",
        sa.Column("attribute_ratings_initial", sa.JSON(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("attribute_ratings_current", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    # Drop snapshot columns
    op.drop_column("users", "attribute_ratings_current")
    op.drop_column("users", "attribute_ratings_initial")

    # Drop history table + indexes
    op.drop_index("idx_user_attr_hist_recorded_at", table_name="user_attribute_ratings_history")
    op.drop_index("idx_user_attr_hist_user_id", table_name="user_attribute_ratings_history")
    op.drop_table("user_attribute_ratings_history")
