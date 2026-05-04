from __future__ import annotations

from functools import wraps
from pathlib import Path

import click
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv
from flask import current_app, g

from app.config import Config

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="flask_app_pool",
            pool_size=5,
            pool_reset_session=True,
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            autocommit=False,
            use_pure=True,
        )
    return _pool


def init_app(app):
    @app.context_processor
    def inject_globals():
        return {
            "app_name": app.config["APP_NAME"],
            "app_tagline": app.config["APP_TAGLINE"],
        }

    @app.before_request
    def csrf_protect():
        from flask import request, abort
        if request.method == "POST":
            token = request.form.get("csrf_token")
            if not token or token != app.config.get("CSRF_TOKEN"):
                abort(403)

    @app.context_processor
    def inject_csrf():
        import secrets
        if "CSRF_TOKEN" not in app.config:
            app.config["CSRF_TOKEN"] = secrets.token_hex(32)
        return {"csrf_token": app.config["CSRF_TOKEN"]}

    @app.cli.command("db-upgrade")
    def db_upgrade_command():
        from app.services.migrations import migrate_database

        migrate_database()
        click.echo("Database migrations applied.")

    @app.cli.command("generate-password-hash")
    def generate_password_hash_command():
        from app.services.auth import init_admin_password
        init_admin_password()


def get_db():
    if "db" not in g:
        pool = _get_pool()
        g.db = pool.get_connection()
    else:
        try:
            g.db.ping(reconnect=True, attempts=1, delay=0)
        except Exception:
            pool = _get_pool()
            g.db = pool.get_connection()
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None and connection.is_connected():
        connection.close()


def dict_cursor():
    return get_db().cursor(dictionary=True)


def migrations_dir() -> Path:
    return current_app.config["MIGRATIONS_DIR"]
