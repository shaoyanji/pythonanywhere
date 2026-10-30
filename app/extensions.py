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
        # Validate config before creating pool
        if not all([Config.MYSQL_HOST, Config.MYSQL_USER, Config.MYSQL_PASSWORD]):
            raise ValueError(
                "MySQL configuration incomplete. "
                "Ensure MYSQL_HOST, MYSQL_USER, and MYSQL_PASSWORD are set."
            )
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

        from app.services.auth import credentials_valid, unauthorized_response

        if request.method != "POST":
            return None

        # Auth first, then CSRF. The admin blueprints answer an unauthenticated
        # writer with 401 + the basic-auth challenge; CSRF is only meaningful to
        # a caller who has already identified itself, and a 403 before the
        # challenge told the wrong story (and made every unauthenticated POST
        # look like a token problem).
        #
        # The 401 is returned here rather than deferred to @admin_required so the
        # rule holds for the whole blueprint: a future POST route in admin/resume
        # that forgets the decorator still cannot be reached without credentials,
        # and the CSRF check below still covers every authenticated POST.
        if request.blueprint in {"admin", "resume"} and not credentials_valid():
            return unauthorized_response()

        token = request.form.get("csrf_token")
        if not token or token != app.config.get("CSRF_TOKEN"):
            abort(403)
        return None

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
