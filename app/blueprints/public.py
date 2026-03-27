from flask import Blueprint, abort, render_template

from app.services.content import (
    fetch_experiment,
    fetch_experiments,
    fetch_navigation,
    fetch_page,
    fetch_posts,
    fetch_post,
    fetch_site_settings,
)


public_bp = Blueprint("public", __name__)


@public_bp.app_context_processor
def inject_site_data():
    settings = fetch_site_settings()
    return {
        "nav_items": fetch_navigation(),
        "site_settings": settings,
    }


@public_bp.route("/")
def home():
    settings = fetch_site_settings()
    home_page = fetch_page("home")
    about_page = fetch_page("about")
    featured_posts = fetch_posts(limit=3)
    featured_experiments = fetch_experiments(featured_only=True)
    return render_template(
        "pages/home.html",
        home_page=home_page,
        about_page=about_page,
        featured_posts=featured_posts,
        featured_experiments=featured_experiments,
        hero_title=settings.get("hero_title", "A personal lab for notes and experiments"),
        hero_intro=settings.get(
            "hero_intro",
            "A thin Flask site for publishing writing, collecting prototypes, and keeping internal tools out of the public surface area.",
        ),
    )


@public_bp.route("/notes")
def notes_index():
    return render_template("pages/notes_index.html", posts=fetch_posts())


@public_bp.route("/notes/<slug>")
def note_detail(slug: str):
    post = fetch_post(slug)
    if not post:
        abort(404)
    return render_template("pages/note_detail.html", post=post)


@public_bp.route("/experiments")
def experiments_index():
    return render_template("pages/experiments_index.html", experiments=fetch_experiments())


@public_bp.route("/experiments/<slug>")
def experiment_detail(slug: str):
    experiment = fetch_experiment(slug)
    if not experiment:
        abort(404)
    return render_template("pages/experiment_detail.html", experiment=experiment)


@public_bp.route("/about")
def about():
    page = fetch_page("about")
    if not page:
        abort(404)
    return render_template("pages/about.html", page=page)

