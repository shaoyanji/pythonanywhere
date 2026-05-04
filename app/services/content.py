from __future__ import annotations

import os
from typing import Any

import bleach
import markdown2
from flask import current_app
from mysql.connector import Error as MySQLError

from app.extensions import dict_cursor, get_db

_is_production = os.getenv("FLASK_ENV") == "production"


def render_markdown(markdown_text: str | None) -> str:
    source = markdown_text or ""
    html = markdown2.markdown(
        source,
        extras=["fenced-code-blocks", "tables", "strike", "target-blank-links"],
    )
    cleaned = bleach.clean(
        html,
        tags=current_app.config["CONTENT_HTML_TAGS"],
        attributes=current_app.config["CONTENT_HTML_ATTRIBUTES"],
        strip=True,
    )
    return bleach.linkify(cleaned)


def get_cached_html(row: dict, markdown_key: str = "body_markdown") -> str:
    """Return cached HTML if available, otherwise render and return."""
    if row and row.get("body_html"):
        return row["body_html"]
    return render_markdown(row.get(markdown_key)) if row else ""


def _safe_query(default, fn):
    try:
        return fn()
    except MySQLError as error:
        if _is_production:
            current_app.logger.error("Database query failed: %s", error)
            return default
        else:
            current_app.logger.warning("Content query fallback triggered: %s", error)
            raise


def fetch_navigation():
    def _run():
        cursor = dict_cursor()
        cursor.execute(
            """
            SELECT label, href, kind
            FROM nav_items
            WHERE is_enabled = 1
            ORDER BY sort_order ASC, id ASC
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows

    return _safe_query([], _run)


def fetch_site_settings() -> dict[str, str]:
    def _run():
        cursor = dict_cursor()
        cursor.execute("SELECT `key`, value_text FROM site_settings")
        rows = cursor.fetchall()
        cursor.close()
        return {row["key"]: row["value_text"] for row in rows}

    return _safe_query({}, _run)


def fetch_page(slug: str) -> dict[str, Any] | None:
    def _run():
        cursor = dict_cursor()
        cursor.execute(
            """
            SELECT id, slug, title, body_markdown, body_html, status, sort_order, created_at, updated_at
            FROM pages
            WHERE slug = %s AND status = 'published'
            LIMIT 1
            """,
            (slug,),
        )
        row = cursor.fetchone()
        cursor.close()
        if row:
            row["body_html"] = get_cached_html(row, "body_markdown")
        return row

    return _safe_query(None, _run)


def fetch_posts(limit: int | None = None):
    def _run():
        cursor = dict_cursor()
        query = """
            SELECT id, slug, title, excerpt, body_markdown, status, published_at, created_at, updated_at
            FROM posts
            WHERE status = 'published'
            ORDER BY COALESCE(published_at, created_at) DESC, id DESC
        """
        if limit is not None:
            query += " LIMIT %s"
            cursor.execute(query, (limit,))
        else:
            cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    return _safe_query([], _run)


def fetch_post(slug: str):
    def _run():
        cursor = dict_cursor()
        cursor.execute(
            """
            SELECT id, slug, title, excerpt, body_markdown, body_html, status, published_at, created_at, updated_at
            FROM posts
            WHERE slug = %s AND status = 'published'
            LIMIT 1
            """,
            (slug,),
        )
        row = cursor.fetchone()
        cursor.close()
        if row:
            row["body_html"] = get_cached_html(row, "body_markdown")
        return row

    return _safe_query(None, _run)


def fetch_experiments(featured_only: bool = False):
    def _run():
        cursor = dict_cursor()
        query = """
            SELECT id, slug, title, summary, body_markdown, demo_path, source_path, status, featured, created_at, updated_at
            FROM experiments
            WHERE status = 'published'
        """
        if featured_only:
            query += " AND featured = 1"
        query += " ORDER BY featured DESC, updated_at DESC, id DESC"
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    return _safe_query([], _run)


def fetch_experiment(slug: str):
    def _run():
        cursor = dict_cursor()
        cursor.execute(
            """
            SELECT id, slug, title, summary, body_markdown, body_html, demo_path, source_path, status, featured, created_at, updated_at
            FROM experiments
            WHERE slug = %s AND status = 'published'
            LIMIT 1
            """,
            (slug,),
        )
        row = cursor.fetchone()
        cursor.close()
        if row:
            row["body_html"] = get_cached_html(row, "body_markdown")
        return row

    return _safe_query(None, _run)


def fetch_prompt_runs(limit: int = 50):
    def _run():
        cursor = dict_cursor()
        cursor.execute(
            """
            SELECT id, title, input_text, output_text, summary, kind, created_at
            FROM prompt_runs
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows

    return _safe_query([], _run)


def fetch_content_summary():
    def _run():
        cursor = dict_cursor()
        summary = {}
        for table_name in ("pages", "posts", "experiments", "prompt_runs"):
            cursor.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
            summary[table_name] = cursor.fetchone()["count"]
        cursor.close()
        return summary

    return _safe_query(
        {"pages": 0, "posts": 0, "experiments": 0, "prompt_runs": 0},
        _run,
    )


def fetch_admin_content(content_type: str):
    if content_type not in {"page", "post", "experiment"}:
        raise ValueError(f"Unsupported content type: {content_type}")

    table_map = {
        "page": "pages",
        "post": "posts",
        "experiment": "experiments",
    }
    table = table_map[content_type]

    allowed_tables = {"pages", "posts", "experiments"}
    if table not in allowed_tables:
        raise ValueError(f"Invalid table: {table}")

    def _run():
        cursor = dict_cursor()
        cursor.execute("SELECT * FROM `%s` ORDER BY updated_at DESC, id DESC" % table)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    return _safe_query([], _run)


def upsert_content(content_type: str, payload: dict[str, Any]) -> None:
    body_html = render_markdown(payload.get("body_markdown", ""))

    if content_type == "page":
        columns = ["slug", "title", "body_markdown", "body_html", "status", "sort_order"]
        table = "pages"
        update_clause = """
            title = VALUES(title),
            body_markdown = VALUES(body_markdown),
            body_html = VALUES(body_html),
            status = VALUES(status),
            sort_order = VALUES(sort_order),
            updated_at = CURRENT_TIMESTAMP
        """
        values_dict = {col: payload.get(col) for col in ["slug", "title", "body_markdown", "status", "sort_order"]}
        values_dict["body_html"] = body_html
    elif content_type == "post":
        columns = [
            "slug",
            "title",
            "excerpt",
            "body_markdown",
            "body_html",
            "status",
            "published_at",
        ]
        table = "posts"
        update_clause = """
            title = VALUES(title),
            excerpt = VALUES(excerpt),
            body_markdown = VALUES(body_markdown),
            body_html = VALUES(body_html),
            status = VALUES(status),
            published_at = VALUES(published_at),
            updated_at = CURRENT_TIMESTAMP
        """
        values_dict = {col: payload.get(col) for col in ["slug", "title", "excerpt", "body_markdown", "status", "published_at"]}
        values_dict["body_html"] = body_html
    elif content_type == "experiment":
        columns = [
            "slug",
            "title",
            "summary",
            "body_markdown",
            "body_html",
            "demo_path",
            "source_path",
            "status",
            "featured",
        ]
        table = "experiments"
        update_clause = """
            title = VALUES(title),
            summary = VALUES(summary),
            body_markdown = VALUES(body_markdown),
            body_html = VALUES(body_html),
            demo_path = VALUES(demo_path),
            source_path = VALUES(source_path),
            status = VALUES(status),
            featured = VALUES(featured),
            updated_at = CURRENT_TIMESTAMP
        """
        values_dict = {col: payload.get(col) for col in ["slug", "title", "summary", "body_markdown", "demo_path", "source_path", "status", "featured"]}
        values_dict["body_html"] = body_html
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

    placeholders = ", ".join(["%s"] * len(columns))
    column_list = ", ".join(columns)
    values = [values_dict.get(column) for column in columns]

    cursor = get_db().cursor()
    cursor.execute(
        f"""
        INSERT INTO {table} ({column_list})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
        {update_clause}
        """,
        values,
    )
    get_db().commit()
    cursor.close()
