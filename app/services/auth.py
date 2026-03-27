from __future__ import annotations

from functools import wraps

from flask import Response, current_app, request


def _unauthorized():
    return Response(
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="Admin"'},
    )


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth = request.authorization
        username = current_app.config["ADMIN_USERNAME"]
        password = current_app.config["ADMIN_PASSWORD"]
        if not auth or auth.username != username or auth.password != password:
            return _unauthorized()
        return view(*args, **kwargs)

    return wrapped

