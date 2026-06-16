"""Alembic environment, wired to the Flask app's SQLAlchemy metadata.

Standard Flask-Migrate setup: the target metadata and DB URL come from the live
Flask app, so `flask db migrate` autogenerates against the models in app/models.
"""
from __future__ import annotations

import logging
import os
from logging.config import fileConfig

from alembic import context
from flask import current_app

config = context.config
if config.config_file_name is not None and os.path.isfile(config.config_file_name):
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# Flask-Migrate provides an active app context when it calls this env.
# We read from current_app (not create a new one) to avoid double-context issues.
config.set_main_option(
    "sqlalchemy.url",
    current_app.config["SQLALCHEMY_DATABASE_URI"].replace("%", "%%"),
)
target_metadata = current_app.extensions["migrate"].db.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = current_app.extensions["migrate"].db.engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
