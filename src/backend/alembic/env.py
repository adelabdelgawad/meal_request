import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from alembic import context

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import the project's models (both legacy and new domain models)
from db.models import Base

# Load environment variables from .env
load_dotenv()

# Import new domain models to register them with SQLModel.metadata
# Domain models will be imported here as they are created
# Example (uncomment as domains are implemented):
# from domain.auth.models import User, Role, RolePermission, RevokedToken
# from domain.meal_request.models import MealRequest, MealRequestLine, MealType
# from domain.organization.models import Employee, Department
# from domain.attendance.models import Attendance, AttendanceDevice
# from domain.config.models import Page, Email

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback to MARIA_URL
    DATABASE_URL = os.getenv("MARIA_URL")

if not DATABASE_URL:
    # Fallback to individual environment variables
    DB_USER = os.getenv("DB_USER", "meal_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "meal_password")
    DB_SERVER = os.getenv("DB_SERVER", "localhost")
    DB_NAME = os.getenv("DB_NAME", "meal_request_db")

    # Use PyMySQL for sync operations in Alembic (aiomysql is async-only)
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}?charset=utf8mb4"
else:
    # Convert async URL to sync URL for Alembic
    DATABASE_URL = DATABASE_URL.replace("mysql+aiomysql", "mysql+pymysql")

# Set the database URL in the Alembic config
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create sync engine for Alembic
    connectable = create_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
