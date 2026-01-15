from logging.config import fileConfig
import os
import sys
import asyncio
import pkgutil
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# 1. ADD PROJECT ROOT TO SYS.PATH
# This allows 'import apps' to work when running from inside the container
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# 2. LOAD ENVIRONMENT VARIABLES
load_dotenv(dotenv_path=BASE_DIR / ".env")

# 3. IMPORT BASE AND DYNAMICALLY LOAD MODELS
# Import the specific Base from your models file
from apps.users.models import Base 
import apps


# This loop finds all models in all subdirectories of /apps
for loader, module_name, is_pkg in pkgutil.walk_packages(apps.__path__, apps.__name__ + "."):
    __import__(module_name)
    print(f"  -> Loaded: {module_name}")

# Set the metadata for Alembic
target_metadata = Base.metadata

# 4. ALEMBIC CONFIGURATION
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
    
db_url = os.getenv('DATABASE_URL')
if db_url:
    config.set_main_option('sqlalchemy.url', db_url)


def do_run_migrations(connection):
    """
    This helper function runs migrations in a synchronous context 
    provided by the async connection's 'run_sync' method.
    """
    context.configure(connection=connection, target_metadata=target_metadata, compare_server_default=True)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an AsyncEngine."""
    
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Use run_sync to execute the synchronous Alembic code
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Use asyncio.run to execute the async function
    asyncio.run(run_migrations_online())