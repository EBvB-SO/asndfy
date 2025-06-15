"""migrate daily_notes.date to DATE"""

# revision identifiers, used by Alembic.
revision = '23ab6521c9fe'
down_revision = '940f952b1a36'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


def upgrade() -> None:
    # 1) Add a temporary column `date_tmp` of type DATE (nullable for now)
    op.add_column(
        'daily_notes',
        sa.Column('date_tmp', sa.Date(), nullable=True)
    )

    # 2) Copy-and-cast existing string dates into date_tmp
    daily_notes = table(
        'daily_notes',
        column('id', sa.String(36)),        # instantiate String
        column('date', sa.String(10)),      # instantiate String
        column('date_tmp', sa.Date()),      # instantiate Date
    )

    op.execute(
        daily_notes.update().values(
            date_tmp=sa.cast(daily_notes.c.date, sa.Date())  # instantiate Date here too
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
        sa.Column('date_txt', sa.String(length=10), nullable=True)
    )

    daily_notes = table(
        'daily_notes',
        column('id', sa.String(36)),
        column('date', sa.Date()),
        column('date_txt', sa.String(10)),
    )
    op.execute(
        daily_notes.update().values(
            date_txt=sa.cast(daily_notes.c.date, sa.String(length=10))
        )
    )

    op.drop_column('daily_notes', 'date')
    op.alter_column(
        'daily_notes',
        'date_txt',
        new_column_name='date',
        nullable=False
    )
