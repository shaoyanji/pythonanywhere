from __future__ import annotations

from functools import wraps
from pathlib import Path

import click
import mysql.connector
from dotenv import load_dotenv
from flask import current_app, g


load_dotenv()


def init_app(app):
    @app.context_processor
    def inject_globals():
        return {
            "app_name": app.config["APP_NAME"],
            "app_tagline": app.config["APP_TAGLINE"],
        }

    @app.cli.command("db-upgrade")
    def db_upgrade_command():
        from app.services.migrations import migrate_database

        migrate_database()
        click.echo("Database migrations applied.")


def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(
            host=current_app.config["MYSQL_HOST"],
            port=current_app.config["MYSQL_PORT"],
            user=current_app.config["MYSQL_USER"],
            password=current_app.config["MYSQL_PASSWORD"],
            database=current_app.config["MYSQL_DB"],
            autocommit=False,
            use_pure=True,
        )
    else:
        g.db.ping(reconnect=True, attempts=1, delay=0)
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None and connection.is_connected():
        connection.close()


def dict_cursor():
    return get_db().cursor(dictionary=True)


def migrations_dir() -> Path:
    return current_app.config["MIGRATIONS_DIR"]
