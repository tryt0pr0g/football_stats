import asyncio
from logging.config import fileConfig
import sys
import os

# --- БЛОК 1: Добавляем путь к проекту ---
# Это нужно, чтобы Alembic видел папку 'app'
sys.path.append(os.getcwd())

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# --- БЛОК 2: Импортируем наши настройки ---
# Импортируем URL базы данных (уже исправленный для asyncpg)
from app.database.db import DATABASE_URL
# Импортируем Base (метаданные)
from app.database.db import Base
# ВАЖНО: Импортируем ВСЕ модели, чтобы они зарегистрировались в Base.metadata
# Если их не импортировать, Alembic подумает, что база пустая.
from app.ORMmodels.models import TeamModel, PlayerModel, MatchModel, LeagueModel, PlayerMatchStatModel

# Config object (читает alembic.ini)
config = context.config

# --- БЛОК 3: Подменяем URL на наш из Python ---
# В alembic.ini мы не храним пароль, берем его из .env через app.database.db
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные для генерации миграций
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())