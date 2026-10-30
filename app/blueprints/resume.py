"""The resume editor section.

Every route here is behind ``admin_required`` — this is a single-user tool on a
public host, so the pages, the writes and the PDF are all basic-auth protected
and the PDF is streamed by this module rather than mapped out of ``static/``.
Approval is enforced in :mod:`app.services.resume.store`, not here: a route can
forget a check, the store cannot.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from app.services.auth import admin_required
from app.services.resume import analysis, needle, pdf, store

resume_bp = Blueprint("resume", __name__, url_prefix="/admin/resume")


def _variant_or_404(name: str) -> str:
    try:
        store.variant_dir(name)
    except store.UnknownVariant:
        abort(404)
    return name


def _overview_context() -> dict:
    return {
        "variants": store.list_variants(),
        "base_path": current_app.config["RESUME_BASE_PATH"],
        "tools": needle.known_names(),
    }


@resume_bp.get("/")
@admin_required
def overview():
    return render_template("pages/admin/resume/overview.html", **_overview_context())


@resume_bp.post("/new")
@admin_required
def create_variant():
    name = (request.form.get("name") or "").strip().lower()
    try:
        store.variant_dir(name)
    except store.UnknownVariant as error:
        flash(str(error), "error")
        return redirect(url_for("resume.overview"))
    flash(f"variant {name} ready: analyze a job description to fill it", "success")
    return redirect(url_for("resume.jd", variant=name))


@resume_bp.get("/<variant>/edit")
@admin_required
def editor(variant: str):
    _variant_or_404(variant)
    resume = store.load_variant(variant) or store.load_base()
    skills = "\n".join(
        f"{skill.get('name', '')}: {skill.get('detail', '')}".strip(" :")
        for skill in (resume.get("sections", {}) or {}).get("skills", []) or []
    )
    return render_template(
        "pages/admin/resume/editor.html",
        variant=variant,
        resume=resume,
        skills_text=skills,
        has_approval=store.has_approval(variant),
        uses_base=store.load_variant(variant) is None,
    )


@resume_bp.post("/<variant>/edit")
@admin_required
def save_editor(variant: str):
    _variant_or_404(variant)
    fields = {
        "name": request.form.get("name"),
        "title": request.form.get("title"),
        "summary": request.form.get("summary"),
        "contact_email": request.form.get("contact_email"),
        "contact_site": request.form.get("contact_site"),
        "contact_location": request.form.get("contact_location"),
        "skills": request.form.get("skills"),
    }
    try:
        store.save_fields(variant, fields)
    except store.ApprovalRequired as error:
        flash(f"Refused: {error}", "error")
        return redirect(url_for("resume.editor", variant=variant)), 409
    flash("variant saved", "success")
    return redirect(url_for("resume.editor", variant=variant))


@resume_bp.get("/<variant>/jd")
@admin_required
def jd(variant: str):
    _variant_or_404(variant)
    proposals = store.load_proposals(variant)
    return render_template(
        "pages/admin/resume/jd.html",
        variant=variant,
        jd_text=(proposals or {}).get("jd", ""),
        threshold=analysis.THRESHOLD,
        proposals_count=len((proposals or {}).get("proposals", [])),
    )


@resume_bp.post("/<variant>/jd")
@admin_required
def analyze(variant: str):
    _variant_or_404(variant)
    jd_text = (request.form.get("jd") or "").strip()
    if not jd_text:
        flash("paste a job description first", "error")
        return redirect(url_for("resume.jd", variant=variant))
    resume = store.load_variant(variant) or store.load_base()
    result = analysis.analyze_job(jd_text, resume)
    store.save_proposals(variant, {"jd": jd_text, **result})
    flash(
        f"{len(result['proposals'])} proposals, {len(result['gaps'])} gaps "
        f"at threshold {result['threshold']}",
        "success",
    )
    return redirect(url_for("resume.review", variant=variant))


@resume_bp.get("/<variant>/review")
@admin_required
def review(variant: str):
    _variant_or_404(variant)
    proposals = store.load_proposals(variant)
    if not proposals:
        flash("no analysis yet: paste a job description first", "error")
        return redirect(url_for("resume.jd", variant=variant))
    return render_template(
        "pages/admin/resume/review.html",
        variant=variant,
        proposals=proposals,
        approved=store.load_approved(variant),
        has_resume=store.load_variant(variant) is not None,
    )


@resume_bp.post("/<variant>/approve")
@admin_required
def approve(variant: str):
    _variant_or_404(variant)
    proposals = store.load_proposals(variant) or {}
    items = []
    for index, proposal in enumerate(proposals.get("proposals", [])):
        if request.form.get(f"approve_{index}") != "on":
            continue
        items.append(
            {
                "resume_key": proposal["resume_key"],
                "concept": proposal["concept"],
                "requirement": proposal["requirement"],
                "evidence": proposal["evidence"],
                "score": proposal["score"],
                "suggested_change": (request.form.get(f"change_{index}") or "").strip() or None,
                "apply_to": request.form.get(f"apply_to_{index}") or "skills",
                "target_index": 0,
            }
        )
    if not items:
        flash("nothing selected: approve at least one proposal", "error")
        return redirect(url_for("resume.review", variant=variant))
    store.save_approved(variant, items, jd_text=proposals.get("jd", ""))
    flash(f"{len(items)} proposal(s) approved — now run apply", "success")
    return redirect(url_for("resume.review", variant=variant))


@resume_bp.post("/<variant>/apply")
@admin_required
def apply_changes(variant: str):
    _variant_or_404(variant)
    try:
        result = store.apply_approved(variant)
    except store.ApprovalRequired as error:
        flash(f"Refused: {error}", "error")
        return redirect(url_for("resume.review", variant=variant)), 409
    applied = sum(1 for item in result["results"] if item["status"] == "applied")
    flash(f"applied {applied} change(s) to variants/{variant}/resume.json", "success")
    return redirect(url_for("resume.editor", variant=variant))


@resume_bp.post("/<variant>/build")
@admin_required
def build(variant: str):
    _variant_or_404(variant)
    try:
        status = pdf.build_pdf(variant)
    except (pdf.PdfError, store.ResumeError) as error:
        flash(f"Build failed: {error}", "error")
        return redirect(url_for("resume.overview"))
    flash(
        f"built {status['size_bytes']} bytes, {status['pages']} page(s), validate {status['validate']}",
        "success",
    )
    return redirect(url_for("resume.overview"))


@resume_bp.get("/<variant>/pdf")
@admin_required
def download_pdf(variant: str):
    _variant_or_404(variant)
    path = store.pdf_path(variant)
    if not path.is_file():
        abort(404)
    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"{variant}-resume.pdf",
        max_age=0,
    )


@resume_bp.get("/<variant>/diff")
@admin_required
def diff(variant: str):
    _variant_or_404(variant)
    try:
        rows = store.diff_against_base(variant)
    except store.ResumeError as error:
        abort(404, str(error))
    return render_template(
        "pages/admin/resume/diff.html",
        variant=variant,
        rows=rows,
        status=store.read_status(variant),
        has_pdf=store.pdf_path(variant).is_file(),
    )


@resume_bp.get("/needle")
@admin_required
def needle_page():
    return render_template(
        "pages/admin/resume/needle.html",
        tools=needle.catalogue(),
        result=None,
    )


@resume_bp.post("/needle")
@admin_required
def needle_run():
    command = (request.form.get("command") or "").strip()
    result = needle.run(command, timeout=current_app.config.get("NEEDLE_TIMEOUT", 180))
    return render_template(
        "pages/admin/resume/needle.html",
        tools=needle.catalogue(),
        result=result,
        command=command,
    )
