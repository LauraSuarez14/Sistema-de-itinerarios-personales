"""Configuracion de Alembic. Lee la URL de la base de datos de las mismas
variables de entorno que usa la app (`ITINERARY_DB_*`, ver `app/config.py`),
para no duplicar la logica de construccion de la connection string."""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Permite `from app.infrastructure.db.models import Base` al correr
# `alembic` desde services/itinerary-service/ (donde vive este archivo).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.db.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    user = os.getenv("ITINERARY_DB_USER", "itinerary")
    password = os.getenv("ITINERARY_DB_PASSWORD", "itinerary-db-pass")
    host = os.getenv("ITINERARY_DB_HOST", "itinerary-db")
    port = os.getenv("ITINERARY_DB_PORT", "5432")
    name = os.getenv("ITINERARY_DB_NAME", "itinerary")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
