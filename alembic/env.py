# alembic/env.py
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 0) Load .env so os.getenv("DATABASE_URL") works
from dotenv import load_dotenv
load_dotenv()

config = context.config

# 1) Override the URL in alembic.ini with our real environment‐variable
real_url = os.getenv("DATABASE_URL")
if real_url is None:
    raise RuntimeError("DATABASE_URL is not set")
config.set_main_option("sqlalchemy.url", real_url)

# 2) Configure Python logging based on alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 3) Import Base and all model modules so that Base.metadata is populated
from app.core.database import Base
import app.db.models

target_metadata = Base.metadata

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

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
