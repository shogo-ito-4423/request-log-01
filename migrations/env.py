import os

from alembic import context

from app.database import make_engine
from app.models import Base

config = context.config
database_url = config.attributes.get("database_url") or os.getenv(
    "DATABASE_URL", "sqlite:////data/issues.db"
)


def run_migrations_offline():
    context.configure(
        url=database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = make_engine(database_url)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                compare_type=True,
                compare_server_default=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
