from __future__ import annotations

from functools import wraps

import click
from flask import Response, current_app, request
from werkzeug.security import check_password_hash, generate_password_hash


def _unauthorized():
    return Response(
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="Admin"'},
    )


def init_admin_password():
    """Generate and display password hash for Admin_PASSWORD."""
    password = click.prompt("Enter admin password", hide_input=True, confirmation_prompt=True)
    hash_value = generate_password_hash(password)
    click.echo(f"Set ADMIN_PASSWORD_HASH in your environment to:\n{hash_value}")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth = request.authorization
        username = current_app.config["ADMIN_USERNAME"]
        password_hash = current_app.config.get("ADMIN_PASSWORD_HASH")
        if not auth or auth.username != username or not check_password_hash(password_hash, auth.password):
            return _unauthorized()
        return view(*args, **kwargs)

    return wrapped

