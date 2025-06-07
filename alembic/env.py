# alembic/env.py

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ------------------------------------------------------------------------------
# 0) Load .env so that os.getenv("DATABASE_URL") works
# ------------------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()

# ------------------------------------------------------------------------------
# 1) Make sure the project root is on PYTHONPATH, so that "import app.core.database"
#    and "import app.db.models" will succeed. We assume you're running "alembic" from
#    your project root directory.
# ------------------------------------------------------------------------------
sys.path.insert(0, os.getcwd())

# ------------------------------------------------------------------------------
# 2) Override the URL in alembic.ini with our real environment-variable
# ------------------------------------------------------------------------------
config = context.config
real_url = os.getenv("DATABASE_URL")
if real_url is None:
    raise RuntimeError("DATABASE_URL is not set in your environment.")
config.set_main_option("sqlalchemy.url", real_url)

# ------------------------------------------------------------------------------
# 3) Configure Python logging based on alembic.ini
# ------------------------------------------------------------------------------
if config.config_file_name:
    fileConfig(config.config_file_name)

# ------------------------------------------------------------------------------
# 4) Import Base and all model modules so that Base.metadata is populated
# ------------------------------------------------------------------------------
#
#    - Base should be the same declarative_base() you use in app/core/database.py.
#    - app.db.models (or whatever path you have) must import every model class so
#      that Base.metadata includes all tables.
#
from app.core.database import Base
import app.db.models
target_metadata = Base.metadata

# ------------------------------------------------------------------------------
# 5) Run migrations in “offline” mode: no DB connection, SQL scripts are emitted.
# ------------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ------------------------------------------------------------------------------
# 6) Run migrations in “online” mode: connect to the DB and apply directly.
# ------------------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


# ------------------------------------------------------------------------------
# 7) Decide which mode to run, then invoke it.
# ------------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
