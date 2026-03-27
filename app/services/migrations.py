from __future__ import annotations

from pathlib import Path

from flask import current_app

from app.extensions import get_db


def _messages_table_exists(cursor) -> bool:
    cursor.execute("SHOW TABLES LIKE 'messages'")
    return cursor.fetchone() is not None


def _migration_history(cursor) -> set[str]:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC")
    return {row[0] for row in cursor.fetchall()}


def _apply_sql_file(cursor, path: Path):
    sql = path.read_text()
    for _ in cursor.execute(sql, multi=True):
        pass


def migrate_database(connection=None, sql_dir: Path | None = None) -> None:
    connection = connection or get_db()
    cursor = connection.cursor()
    applied = _migration_history(cursor)
    sql_dir = sql_dir or current_app.config["MIGRATIONS_DIR"]

    for path in sorted(sql_dir.glob("*.sql")):
        version = path.name
        if version in applied:
            continue
        _apply_sql_file(cursor, path)

        if version == "0002_migrate_messages_to_prompt_runs.sql" and _messages_table_exists(cursor):
            cursor.execute(
                """
                INSERT INTO prompt_runs (title, input_text, output_text, summary, kind, created_at)
                SELECT
                    COALESCE(NULLIF(title, ''), CONCAT('message-', id)),
                    content,
                    aicontent,
                    summary,
                    'legacy-message',
                    COALESCE(created_at, CURRENT_TIMESTAMP)
                FROM messages
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM prompt_runs
                    WHERE prompt_runs.title = COALESCE(NULLIF(messages.title, ''), CONCAT('message-', messages.id))
                      AND prompt_runs.input_text <=> messages.content
                      AND prompt_runs.output_text <=> messages.aicontent
                )
                """
            )

        cursor.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s)",
            (version,),
        )
        connection.commit()

    cursor.close()
