from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services.auth import admin_required
from app.services.content import (
    fetch_admin_content,
    fetch_content_summary,
    fetch_prompt_runs,
    upsert_content,
)
from app.services.deploy import run_deploy_tasks


def log_admin_action(action: str, details: str = ""):
    """Simple admin audit log - writes to app logger."""
    from flask import current_app
    current_app.logger.info("ADMIN ACTION: %s %s", action, details)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def admin_index():
    return render_template("pages/admin/index.html", summary=fetch_content_summary())


@admin_bp.route("/content", methods=["GET", "POST"])
@admin_required
def admin_content():
    content_type = request.values.get("type", "post")
    if request.method == "POST":
        published_at = request.form.get("published_at", "").strip() or None
        if published_at:
            published_at = published_at.replace("T", " ")
        payload = {
            "slug": request.form.get("slug", "").strip(),
            "title": request.form.get("title", "").strip(),
            "body_markdown": request.form.get("body_markdown", "").strip(),
            "status": request.form.get("status", "draft").strip(),
            "sort_order": int(request.form.get("sort_order", "0") or 0),
            "excerpt": request.form.get("excerpt", "").strip() or None,
            "published_at": published_at,
            "summary": request.form.get("summary", "").strip() or None,
            "demo_path": request.form.get("demo_path", "").strip() or None,
            "source_path": request.form.get("source_path", "").strip() or None,
            "featured": 1 if request.form.get("featured") == "on" else 0,
        }
        upsert_content(content_type, payload)
        log_admin_action("content_upsert", f"type={content_type}, slug={payload['slug']}")
        flash(f"{content_type.title()} saved.", "success")
        return redirect(url_for("admin.admin_content", type=content_type))

    return render_template(
        "pages/admin/content.html",
        content_type=content_type,
        rows=fetch_admin_content(content_type),
    )


@admin_bp.route("/prompts")
@admin_required
def admin_prompts():
    return render_template("pages/admin/prompts.html", prompt_runs=fetch_prompt_runs(limit=100))


@admin_bp.route("/deploy", methods=["GET", "POST"])
@admin_required
def admin_deploy():
    results = None
    if request.method == "POST":
        log_admin_action("deploy", "Triggered deployment")
        results = run_deploy_tasks()
    return render_template("pages/admin/deploy.html", results=results)
