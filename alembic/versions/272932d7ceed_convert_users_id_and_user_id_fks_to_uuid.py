from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa

revision = "272932d7ceed_convert_ids_to_uuid"
down_revision = "23ab6521c9fe"
branch_labels = None
depends_on = None

CHILD_TABLES = [
    "user_profiles",
    "projects",
    "training_plans",
    "session_tracking",
    "daily_notes",
    "user_badges",
    "exercise_entries",
    "exercise_tracking",
    "pending_session_updates",
]

def upgrade():
    # 1) Alter the users PK
    op.alter_column(
        "users","id",
        existing_type=sa.INTEGER(),
        type_=sa.String(length=36),
        nullable=False,
        postgresql_using="id::text",
        # remove the old sequence default since we'll now set UUIDs in code
        server_default=None,
    )

    # 2) For each child table, drop FK, alter, re-create FK
    for tbl in CHILD_TABLES:
        fk_name = f"{tbl}_user_id_fkey"
        # a) drop the FK constraint
        op.drop_constraint(fk_name, tbl, type_="foreignkey")
        # b) alter column
        op.alter_column(
            tbl, "user_id",
            existing_type=sa.INTEGER(),
            type_=sa.String(length=36),
            nullable=False,
            postgresql_using="user_id::text",
        )
        # c) re-create the FK
        op.create_foreign_key(
            fk_name,                    # constraint name
            tbl, "users",               # source, target
            ["user_id"], ["id"],
            ondelete="CASCADE"
        )

def downgrade():
    # reverse: drop all those FKs, change back to INTEGER, recreate FKs, then users.id
    for tbl in CHILD_TABLES:
        fk_name = f"{tbl}_user_id_fkey"
        op.drop_constraint(fk_name, tbl, type_="foreignkey")
        op.alter_column(
            tbl, "user_id",
            existing_type=sa.String(length=36),
            type_=sa.INTEGER(),
            nullable=False,
            postgresql_using="user_id::integer",
        )
        op.create_foreign_key(
            fk_name,
            tbl, "users",
            ["user_id"], ["id"],
            ondelete="CASCADE"
        )

    op.alter_column(
        "users","id",
        existing_type=sa.String(length=36),
        type_=sa.INTEGER(),
        nullable=False,
        postgresql_using="id::integer",
        # if you want to restore your old sequence default you can,
        # but you probably can just leave it off
        server_default=sa.text("nextval('users_id_seq'::regclass)"),
    )
