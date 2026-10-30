"""Generate the Needle catalogue from dodo.py.

``tools.json`` is a projection of the task file, not a second schema: this module
parses ``dodo.py`` with :mod:`ast`, reads the ``RESUME_TASKS`` table and the
``task_*`` functions, and refuses to emit a catalogue that names a task the file
does not define. A hand-written list would drift the moment a task is renamed,
and a router acting on a stale list routes to nothing.

The five public tasks are the catalogue. Everything else is internal: reachable
through ``task_dep`` and by hand, never offered to the router.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DODO_PATH = ROOT / "dodo.py"
TOOLS_PATH = ROOT / "tools.json"

REQUIRED_FIELDS = (
    "desc",
    "summary",
    "when_to_use",
    "when_not_to_use",
    "inputs",
    "outputs",
    "preconditions",
    "example",
)


class CatalogueError(Exception):
    """dodo.py and the catalogue disagree. Never paper over this."""


def _literal(node: ast.AST, label: str):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError) as error:  # pragma: no cover - malformed dodo.py
        raise CatalogueError(f"{label} is not a literal: {error}") from error


def parse_dodo(path: Path | None = None) -> tuple[dict, tuple[str, ...], set[str]]:
    """Return (spec, internal, task_function_names) from dodo.py."""
    source = Path(path or DODO_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)

    spec: dict = {}
    internal: tuple[str, ...] = ()
    functions: set[str] = set()

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
            if target == "RESUME_TASKS":
                spec = _literal(node.value, "RESUME_TASKS")
            elif target == "RESUME_INTERNAL":
                internal = tuple(_literal(node.value, "RESUME_INTERNAL"))
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("task_"):
            functions.add(node.name[len("task_"):])

    return spec, internal, functions


def validate(spec: dict, internal: tuple[str, ...], functions: set[str]) -> list[str]:
    """Every way dodo.py can disagree with the catalogue, all reported at once."""
    problems: list[str] = []

    if not spec:
        problems.append("RESUME_TASKS is missing or empty")

    overlap = sorted(set(spec) & set(internal))
    if overlap:
        problems.append(f"declared both public and internal: {', '.join(overlap)}")

    for name, meta in sorted(spec.items()):
        if name not in functions:
            problems.append(f"catalogue names {name!r} but dodo.py has no task_{name}")
        missing = [field for field in REQUIRED_FIELDS if field not in meta]
        if missing:
            problems.append(f"{name}: missing metadata {', '.join(missing)}")
        for field in ("inputs", "outputs", "preconditions"):
            if field in meta and not isinstance(meta[field], list):
                problems.append(f"{name}: {field} must be a list")
        if "example" in meta and not str(meta["example"]).strip():
            problems.append(f"{name}: example is empty")

    for name in internal:
        if name not in functions:
            problems.append(f"internal task {name!r} has no task_{name} in dodo.py")
    return problems


def build_catalogue(path: Path | None = None) -> dict:
    spec, internal, functions = parse_dodo(path)
    problems = validate(spec, internal, functions)
    if problems:
        raise CatalogueError("; ".join(problems))

    tools = []
    for name, meta in sorted(spec.items()):
        entry = {"name": name, "command": f"doit {name}"}
        entry.update({field: meta[field] for field in REQUIRED_FIELDS})
        tools.append(entry)

    return {
        "generated_from": "dodo.py",
        "generated_by": "app/services/resume/tooling.py",
        "count": len(tools),
        "tools": tools,
    }


def write_tools_json(path: Path | None = None) -> dict:
    catalogue = build_catalogue()
    target = Path(path or TOOLS_PATH)
    target.write_text(json.dumps(catalogue, indent=2) + "\n", encoding="utf-8")
    return catalogue


def load_tools(path: Path | None = None) -> dict:
    target = Path(path or TOOLS_PATH)
    if not target.is_file():
        raise CatalogueError(f"{target.name} is missing: run `doit tools_json`")
    return json.loads(target.read_text(encoding="utf-8"))
