"""Needle: a router, not an analyst.

Short commands only. The namespace is closed — the five names in ``tools.json``
and nothing else — so a hallucinated name fails before any process starts, and a
caller with a small context window can be told exactly what does exist.

Parameters travel as ``KEY=VALUE`` tokens and are validated against an allowlist.
Nothing is passed through a shell: the command line is split into a task name and
an argv list, `subprocess` runs it without ``shell=True``, and the only strings
that reach the child come from that allowlist.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from app.services.resume import tooling

#: The only environment the router will set on a child. An unlisted KEY=value is
#: refused rather than forwarded: the child imports the Flask app, and PYTHONPATH
#: or PYTHONSTARTUP from a chat box would be an execution primitive.
ALLOWED_PARAMS = ("PYANY_VARIANT", "PYANY_JD", "PYANY_JD_FILE", "PYANY_PORT")

DEFAULT_TIMEOUT = 180


class NeedleError(Exception):
    pass


def interpreter() -> str:
    """The Python that runs ``doit``, never the server that is hosting us.

    Inside a PythonAnywhere web worker ``sys.executable`` is the uWSGI binary,
    so spawning ``[sys.executable, "-m", "doit", ...]`` runs ``uwsgi -m doit``
    — and uWSGI parses ``doit`` as a config file and exits with
    ``unable to load configuration from doit``. That is the live failure the
    tester saw; the task never started. Set ``PYANY_PYTHON`` to override, or
    this falls back to a real interpreter.
    """
    override = os.environ.get("PYANY_PYTHON")
    if override:
        return override

    candidates = [sys.executable, sys.exec_prefix + "/bin/python3", shutil.which("python3"), shutil.which("python")]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and Path(candidate).name.lower().startswith("python"):
            return candidate
    raise NeedleError(
        "no Python interpreter found to run doit: set PYANY_PYTHON to one "
        f"(sys.executable is {sys.executable!r})"
    )


def catalogue() -> list[dict]:
    return tooling.load_tools()["tools"]


def known_names() -> list[str]:
    return [tool["name"] for tool in catalogue()]


def parse(command: str) -> tuple[str, dict]:
    """Split a command line into (task name, parameters). No shell syntax."""
    tokens = shlex.split(command)
    if not tokens:
        raise NeedleError("empty command")
    name, rest = tokens[0], tokens[1:]

    params: dict[str, str] = {}
    for token in rest:
        key, separator, value = token.partition("=")
        if not separator:
            raise NeedleError(f"unexpected argument {token!r}: parameters are KEY=value")
        if key not in ALLOWED_PARAMS:
            raise NeedleError(f"{key!r} is not an allowed parameter ({', '.join(ALLOWED_PARAMS)})")
        params[key] = value
    return name, params


def run(command: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Execute one catalogue command. Unknown names never reach a subprocess."""
    names = known_names()
    try:
        name, params = parse(command)
    except (NeedleError, ValueError) as error:
        return {"ok": False, "executed": False, "name": None, "output": "", "error": str(error), "known": names}

    if name not in names:
        return {
            "ok": False,
            "executed": False,
            "name": name,
            "output": "",
            "error": f"unknown task {name!r}: the catalogue is closed ({', '.join(names)})",
            "known": names,
        }

    try:
        python = interpreter()
    except NeedleError as error:
        return {"ok": False, "executed": False, "name": name, "output": "", "error": str(error), "known": names}

    environment = os.environ.copy()
    environment.update(params)

    argv = [python, "-m", "doit", name]
    try:
        completed = subprocess.run(
            argv,
            cwd=str(tooling.ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "executed": True,
            "name": name,
            "output": "",
            "error": f"{name} timed out after {timeout}s",
            "known": names,
        }
    except OSError as error:
        return {"ok": False, "executed": False, "name": name, "output": "", "error": str(error), "known": names}

    return {
        "ok": completed.returncode == 0,
        "executed": True,
        "name": name,
        "returncode": completed.returncode,
        "output": (completed.stdout or "").strip(),
        "error": (completed.stderr or "").strip(),
        "known": names,
    }


def explain(name: str) -> dict | None:
    """The catalogue entry for one name, for the UI to show before running."""
    for tool in catalogue():
        if tool["name"] == name:
            return tool
    return None


def root() -> Path:
    return tooling.ROOT
