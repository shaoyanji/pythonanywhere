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


def credentials_valid() -> bool:
    """True when the request carries the admin credentials.

    Called by the CSRF hook as well as by the decorator, so the ordering is
    "who are you" before "prove this came from your browser". A missing
    ADMIN_PASSWORD_HASH is a configuration state, not a crash: it answers False
    and the caller gets the 401 challenge.
    """
    auth = request.authorization
    username = current_app.config["ADMIN_USERNAME"]
    password_hash = current_app.config.get("ADMIN_PASSWORD_HASH")
    if not auth or not password_hash or auth.username != username:
        return False
    return check_password_hash(password_hash, auth.password)


def unauthorized_response():
    """The 401 the admin gate returns, with the basic-auth challenge."""
    return _unauthorized()


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not credentials_valid():
            return _unauthorized()
        return view(*args, **kwargs)

    return wrapped

