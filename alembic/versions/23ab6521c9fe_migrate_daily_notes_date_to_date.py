"""migrate daily_notes.date to DATE"""

# revision identifiers, used by Alembic.
revision = '23ab6521c9fe'
down_revision = '940f952b1a36'   # keep whatever your previous head is
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Date


def upgrade() -> None:
    # 1) Add a temporary column `date_tmp` of type DATE (nullable for now)
    op.add_column(
        'daily_notes',
        sa.Column('date_tmp', Date(), nullable=True)
    )

    # 2) Copy-and-cast existing string dates into date_tmp
    daily_notes = table(
        'daily_notes',
        column('id', String),
        column('date', String),
        column('date_tmp', Date),
    )
    # On most backends sa.cast will work; SQLite will do an implicit cast
    op.execute(
        daily_notes.update().values(
            date_tmp=sa.cast(daily_notes.c.date, Date)
        )
    )

    # 3) Drop the old `date` column, and rename `date_tmp` → `date`
    op.drop_column('daily_notes', 'date')
    op.alter_column(
        'daily_notes',
        'date_tmp',
        new_column_name='date',
        nullable=False
    )


def downgrade() -> None:
    # reverse: re-add old string column and cast back
    op.add_column(
        'daily_notes',
        sa.Column('date_txt', String(length=10), nullable=True)
    )

    daily_notes = table(
        'daily_notes',
        column('id', String),
        column('date', Date),
        column('date_txt', String),
    )
    op.execute(
        daily_notes.update().values(
            date_txt=sa.cast(daily_notes.c.date, String(length=10))
        )
    )

    op.drop_column('daily_notes', 'date')
    op.alter_column(
        'daily_notes',
        'date_txt',
        new_column_name='date',
        nullable=False
    )