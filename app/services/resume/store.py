"""Variant storage with a hard approval gate.

Two invariants, both enforced here rather than in a view:

* the base resume is read-only, and
* nothing is written to ``variants/<name>/resume.json`` unless
  ``variants/<name>/approved.json`` exists — a human reviewed this variant.

Every write path funnels through this module so the gate cannot be forgotten by
a new route, and the base digest is recomputed on demand so a bug that mutates
it shows up in a test rather than a few weeks later.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

APPLY_TARGETS = ("skills", "bullets", "summary", "none")


class ResumeError(Exception):
    """Base class for user-facing resume failures."""


class UnknownVariant(ResumeError):
    pass


class ApprovalRequired(ResumeError):
    """A write was attempted without approved.json. Nothing was written."""


def _base_path() -> Path:
    return Path(current_app.config["RESUME_BASE_PATH"])


def _variants_dir() -> Path:
    return Path(current_app.config["RESUME_VARIANTS_DIR"])


def variant_dir(name: str) -> Path:
    """Resolve a variant directory, rejecting anything that is not a plain slug.

    The name arrives from a query string, so this is the path-traversal gate:
    ``../../etc`` must never reach the filesystem.
    """
    if not isinstance(name, str) or not NAME_PATTERN.match(name):
        raise UnknownVariant(f"invalid variant name: {name!r}")
    return _variants_dir() / name


def load_base() -> dict:
    path = _base_path()
    if not path.is_file():
        raise ResumeError(f"base resume not found at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ResumeError(f"base resume is not valid JSON: {error}") from error


def base_digest() -> str:
    return hashlib.sha256(_base_path().read_bytes()).hexdigest()


def load_variant(name: str) -> dict | None:
    path = variant_dir(name) / "resume.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def load_proposals(name: str) -> dict | None:
    path = variant_dir(name) / "proposals.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_proposals(name: str, payload: dict) -> None:
    """Proposals are analysis output, not resume data: no approval gate."""
    _write_json(variant_dir(name) / "proposals.json", payload)


def has_approval(name: str) -> bool:
    return (variant_dir(name) / "approved.json").is_file()


def load_approved(name: str) -> dict | None:
    path = variant_dir(name) / "approved.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_approved(name: str, items: list[dict], jd_text: str = "") -> dict:
    """Record a human decision. This is the gate, not the edit."""
    approved = {
        "variant": name,
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "jd_excerpt": jd_text[:500],
        "items": items,
    }
    _write_json(variant_dir(name) / "approved.json", approved)
    return approved


def _normalized_skills(resume: dict) -> list[dict]:
    return resume.setdefault("sections", {}).setdefault("skills", [])


def _apply_item(resume: dict, item: dict) -> dict:
    """Apply one approved change. Only human-supplied text is written: this
    function never composes a bullet, because inventing experience is the failure
    the whole editor exists to prevent."""
    change = (item.get("suggested_change") or "").strip()
    if not change:
        return {"resume_key": item.get("resume_key"), "status": "skipped", "reason": "no suggested_change"}
    target = item.get("apply_to") or "skills"
    if target not in APPLY_TARGETS:
        return {"resume_key": item.get("resume_key"), "status": "skipped", "reason": f"unknown apply_to {target!r}"}

    if target == "none":
        return {"resume_key": item.get("resume_key"), "status": "recorded"}

    if target == "summary":
        resume["summary"] = change
        return {"resume_key": item.get("resume_key"), "status": "applied", "to": "summary"}

    if target == "skills":
        skills = _normalized_skills(resume)
        key = item.get("resume_key") or ""
        name = key.split("/", 1)[1] if key.startswith("skills/") else ""
        for skill in skills:
            if str(skill.get("name", "")).strip().lower() == name.strip().lower() and name:
                skill["detail"] = change
                return {"resume_key": item.get("resume_key"), "status": "applied", "to": f"skills/{name}"}
        skills.append({"name": change, "detail": ""})
        return {"resume_key": item.get("resume_key"), "status": "applied", "to": "skills (new)"}

    # bullets
    experience = resume.setdefault("sections", {}).setdefault("experience", [])
    index = item.get("target_index", 0)
    if not isinstance(index, int) or not 0 <= index < len(experience):
        return {
            "resume_key": item.get("resume_key"),
            "status": "skipped",
            "reason": f"target_index {index!r} has no experience entry",
        }
    experience[index].setdefault("bullets", []).append(change)
    return {"resume_key": item.get("resume_key"), "status": "applied", "to": f"experience/{index}/bullets"}


def apply_approved(name: str) -> dict:
    """Fold the approved changes into ``variants/<name>/resume.json``.

    Raises :class:`ApprovalRequired` — before touching the filesystem — when the
    gate file is missing, which is what makes "no step may skip approval" true
    rather than aspirational.
    """
    approved = load_approved(name)
    if not approved:
        raise ApprovalRequired(
            f"variants/{name}/approved.json is missing: approve proposals before applying"
        )
    items = approved.get("items") or []
    if not items:
        raise ApprovalRequired(f"variants/{name}/approved.json has no approved items")

    existing = load_variant(name)
    resume = copy.deepcopy(existing) if existing else copy.deepcopy(load_base())
    base_before = base_digest()

    results = [_apply_item(resume, item) for item in items]

    _write_json(variant_dir(name) / "resume.json", resume)
    _write_json(
        variant_dir(name) / "applied.json",
        {
            "variant": name,
            "applied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "items": results,
        },
    )
    if base_digest() != base_before:  # pragma: no cover - defensive, asserted in tests
        raise ResumeError("base resume changed during apply_approved")
    return {"variant": name, "results": results}


def save_fields(name: str, fields: dict) -> dict:
    """Editor save. Also gated: an edit is a write to resume.json like any other."""
    if not has_approval(name):
        raise ApprovalRequired(
            f"variants/{name}/approved.json is missing: approve proposals before editing"
        )
    resume = load_variant(name) or copy.deepcopy(load_base())

    if fields.get("name"):
        resume["name"] = fields["name"].strip()
    if fields.get("title"):
        resume["title"] = fields["title"].strip()
    if fields.get("summary") is not None:
        resume["summary"] = fields["summary"].strip()
    contact = resume.setdefault("contact", {})
    for key in ("email", "site", "location"):
        if fields.get(f"contact_{key}") is not None:
            contact[key] = fields[f"contact_{key}"].strip()

    if fields.get("skills") is not None:
        skills: list[dict] = []
        for line in fields["skills"].splitlines():
            line = line.strip()
            if not line:
                continue
            head, _, detail = line.partition(":")
            skills.append({"name": head.strip(), "detail": detail.strip()})
        resume.setdefault("sections", {})["skills"] = skills

    _write_json(variant_dir(name) / "resume.json", resume)
    return resume


def list_variants() -> list[dict]:
    directory = _variants_dir()
    if not directory.is_dir():
        return []
    rows = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_dir() or not NAME_PATTERN.match(entry.name):
            continue
        status = read_status(entry.name)
        rows.append(
            {
                "name": entry.name,
                "has_resume": (entry / "resume.json").is_file(),
                "has_approved": (entry / "approved.json").is_file(),
                "has_proposals": (entry / "proposals.json").is_file(),
                "pdf_path": pdf_path(entry.name).is_file(),
                "last_build": status.get("built_at"),
                "last_validate": status.get("validate"),
            }
        )
    return rows


def pdf_path(name: str) -> Path:
    return variant_dir(name) / "build" / "resume.pdf"


def read_status(name: str) -> dict:
    path = variant_dir(name) / "build" / "status.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_status(name: str, payload: dict) -> None:
    _write_json(variant_dir(name) / "build" / "status.json", payload)


def clear_build(name: str) -> None:
    build = variant_dir(name) / "build"
    if build.is_dir():
        shutil.rmtree(build)


def diff_against_base(name: str) -> list[dict]:
    """Field-level differences between a variant and the base, for the variant
    list. Compares leaves only, so a changed bullet shows as one row."""
    base = load_base()
    variant = load_variant(name) or base
    rows: list[dict] = []

    def walk(left, right, path=""):
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                walk(left.get(key), right.get(key), f"{path}/{key}" if path else str(key))
            return
        if isinstance(left, list) and isinstance(right, list):
            for index in range(max(len(left), len(right))):
                walk(
                    left[index] if index < len(left) else None,
                    right[index] if index < len(right) else None,
                    f"{path}/{index}",
                )
            return
        if left != right:
            rows.append({"path": path, "base": left, "variant": right})

    walk(base, variant)
    return rows
