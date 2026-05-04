#!/usr/bin/env python
import os
import tempfile
import subprocess
from pathlib import Path

import typer
import click
from dotenv import load_dotenv

from app.factory import create_app
from app.services.migrations import migrate_database
from app.services.content import fetch_admin_content, upsert_content

load_dotenv()

cli = typer.Typer()


@cli.command()
def serve(host: str = "127.0.0.1", port: int = 5000, debug: bool = None):
    app = create_app()
    if debug is None:
        debug = app.config.get("FLASK_DEBUG", False)
    app.run(host=host, port=port, debug=debug)


@cli.command("db-upgrade")
def db_upgrade():
    """Apply database migrations (auto-decrypts .env.age if needed)."""
    import os
    import subprocess
    from dotenv import load_dotenv

    # Auto-decrypt .env.age if .env doesn't exist
    if not os.path.exists(".env") and os.path.exists(".env.age"):
        subprocess.run(
            ["age", "-d", "-i", os.path.expanduser("~/.ssh/id_ed25519"), ".env.age"],
            stdout=open(".env", "w"),
            check=True
        )
        print("Decrypted .env.age to .env")

    load_dotenv()
    app = create_app()
    with app.app_context():
        migrate_database()
    print("Database migrations applied.")


@cli.command("generate-password-hash")
def generate_password_hash():
    """Generate a password hash for ADMIN_PASSWORD_HASH."""
    from app.services.auth import init_admin_password
    init_admin_password()


def _get_app_context():
    """Create app and return app context."""
    app = create_app()
    ctx = app.app_context()
    ctx.push()
    return app, ctx


def _edit_in_editor(initial_content: str = "") -> str:
    """Open editor for content authoring."""
    editor = os.getenv("EDITOR", "nano")

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.md', delete=False) as f:
        f.write(initial_content)
        temp_path = f.name

    try:
        subprocess.run([editor, temp_path])
        with open(temp_path, 'r') as f:
            return f.read()
    finally:
        os.unlink(temp_path)


@cli.command("create-page")
def create_page():
    """Create a new page interactively."""
    app, ctx = _get_app_context()
    try:
        slug = typer.prompt("Slug (URL-friendly identifier)")
        title = typer.prompt("Title")
        status = typer.prompt(
            "Status",
            default="draft",
            type=click.Choice(["draft", "published", "archived"])
        )
        sort_order = typer.prompt("Sort order", default=0, type=int)

        typer.echo("Enter body markdown (opens editor):")
        body_markdown = _edit_in_editor(f"# {title}\n\n")

        payload = {
            "slug": slug,
            "title": title,
            "body_markdown": body_markdown,
            "status": status,
            "sort_order": sort_order,
        }
        upsert_content("page", payload)
        typer.echo(f"Page '{title}' created successfully!")
    finally:
        ctx.pop()


@cli.command("create-post")
def create_post():
    """Create a new post interactively."""
    app, ctx = _get_app_context()
    try:
        slug = typer.prompt("Slug (URL-friendly identifier)")
        title = typer.prompt("Title")
        excerpt = typer.prompt("Excerpt (short summary)", default="")
        status = typer.prompt(
            "Status",
            default="draft",
            type=click.Choice(["draft", "published", "archived"])
        )

        from datetime import datetime
        publish_now = typer.confirm("Publish now?", default=True)
        published_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if publish_now else None

        typer.echo("Enter body markdown (opens editor):")
        body_markdown = _edit_in_editor(f"# {title}\n\n")

        payload = {
            "slug": slug,
            "title": title,
            "excerpt": excerpt,
            "body_markdown": body_markdown,
            "status": status,
            "published_at": published_at,
        }
        upsert_content("post", payload)
        typer.echo(f"Post '{title}' created successfully!")
    finally:
        ctx.pop()


@cli.command("create-experiment")
def create_experiment():
    """Create a new experiment interactively."""
    app, ctx = _get_app_context()
    try:
        slug = typer.prompt("Slug (URL-friendly identifier)")
        title = typer.prompt("Title")
        summary = typer.prompt("Summary", default="")
        status = typer.prompt(
            "Status",
            default="draft",
            type=click.Choice(["draft", "published", "archived"])
        )
        featured = typer.confirm("Featured on homepage?", default=False)
        demo_path = typer.prompt("Demo path (optional)", default="")
        source_path = typer.prompt("Source path (optional)", default="")

        typer.echo("Enter body markdown (opens editor):")
        body_markdown = _edit_in_editor(f"# {title}\n\n")

        payload = {
            "slug": slug,
            "title": title,
            "summary": summary,
            "body_markdown": body_markdown,
            "status": status,
            "featured": 1 if featured else 0,
            "demo_path": demo_path or None,
            "source_path": source_path or None,
        }
        upsert_content("experiment", payload)
        typer.echo(f"Experiment '{title}' created successfully!")
    finally:
        ctx.pop()


@cli.command("list-content")
def list_content(
    content_type: str = typer.Argument(..., help="Content type: page, post, or experiment")
):
    """List existing content."""
    app, ctx = _get_app_context()
    try:
        if content_type not in ["page", "post", "experiment"]:
            typer.secho(f"Invalid content type: {content_type}", fg="red")
            raise typer.Exit(1)

        rows = fetch_admin_content(content_type)
        if not rows:
            typer.echo(f"No {content_type}s found.")
            return

        for row in rows:
            status_color = "green" if row['status'] == 'published' else "yellow"
            typer.echo(f"• {row['slug']} - {row['title']} ", nl=False)
            typer.secho(f"[{row['status']}]", fg=status_color)
    finally:
        ctx.pop()


@cli.command("edit-content")
def edit_content(
    content_type: str = typer.Argument(..., help="Content type: page, post, or experiment"),
    slug: str = typer.Argument(...)
):
    """Edit existing content by slug."""
    app, ctx = _get_app_context()
    try:
        from app.services.content import fetch_page, fetch_post, fetch_experiment

        fetch_map = {
            "page": fetch_page,
            "post": fetch_post,
            "experiment": fetch_experiment,
        }

        if content_type not in fetch_map:
            typer.secho(f"Invalid content type: {content_type}", fg="red")
            raise typer.Exit(1)

        item = fetch_map[content_type](slug)
        if not item:
            typer.secho(f"{content_type} with slug '{slug}' not found.", fg="red")
            raise typer.Exit(1)

        typer.echo(f"Editing: {item['title']}")
        typer.echo(f"Current status: {item['status']}")

        new_status = typer.prompt(
            "Status",
            default=item['status'],
            type=click.Choice(["draft", "published", "archived"])
        )

        typer.echo("Edit body markdown (opens editor):")
        body_markdown = _edit_in_editor(item.get('body_markdown', ''))

        payload = {
            "slug": slug,
            "title": item['title'],
            "body_markdown": body_markdown,
            "status": new_status,
        }

        if content_type == "page":
            payload["sort_order"] = item.get('sort_order', 0)
        elif content_type == "post":
            payload["excerpt"] = item.get('excerpt', '')
            payload["published_at"] = item.get('published_at')
        elif content_type == "experiment":
            payload["summary"] = item.get('summary', '')
            payload["featured"] = item.get('featured', 0)
            payload["demo_path"] = item.get('demo_path')
            payload["source_path"] = item.get('source_path')

        upsert_content(content_type, payload)
        typer.echo(f"{content_type.title()} '{item['title']}' updated successfully!")
    finally:
        ctx.pop()


@cli.command("import-markdown")
def import_markdown(
    file_path: Path = typer.Argument(..., exists=True, readable=True),
    content_type: str = typer.Option(..., help="Content type: page, post, or experiment"),
    slug: str = typer.Option(..., help="URL slug for the content"),
    title: str = typer.Option(..., help="Title of the content"),
):
    """Import content from a markdown file."""
    app, ctx = _get_app_context()
    try:
        body_markdown = file_path.read_text()

        payload = {
            "slug": slug,
            "title": title,
            "body_markdown": body_markdown,
            "status": "draft",
        }

        if content_type == "page":
            payload["sort_order"] = 0
        elif content_type == "post":
            payload["excerpt"] = ""
            payload["published_at"] = None
        elif content_type == "experiment":
            payload["summary"] = ""
            payload["featured"] = 0
            payload["demo_path"] = None
            payload["source_path"] = None
        else:
            typer.secho(f"Invalid content type: {content_type}", fg="red")
            raise typer.Exit(1)

        upsert_content(content_type, payload)
        typer.echo(f"{content_type.title()} imported from {file_path} successfully!")
    finally:
        ctx.pop()


if __name__ == "__main__":
    cli()
