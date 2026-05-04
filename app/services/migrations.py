from __future__ import annotations

from pathlib import Path

from flask import current_app

from app.extensions import get_db
from app.config import Config


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


def _column_exists(cursor, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column)
    )
    return cursor.fetchone()[0] > 0


def _index_exists(cursor, table: str, index: str) -> bool:
    """Check if an index exists on a table."""
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (table, index)
    )
    return cursor.fetchone()[0] > 0


def _apply_sql_file(cursor, path: Path):
    """Execute SQL file with idempotent logic."""
    sql = path.read_text()
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
    for stmt in statements:
        try:
            cursor.execute(stmt)
            # Consume any result
            try:
                cursor.fetchall()
            except:
                pass
        except Exception as e:
            # Log and continue for idempotent migrations
            err_msg = str(e)
            if any(x in err_msg for x in ['Duplicate column', 'Duplicate key', 'already exists']):
                current_app.logger.warning("Skipping duplicate: %s", e)
                continue
            raise


def _migrate_messages_to_prompt_runs(cursor):
    """Extract legacy migration logic to dedicated function."""
    if _messages_table_exists(cursor):
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


def migrate_database(connection=None, sql_dir: Path | None = None) -> None:
    """Apply database migrations."""
    if connection is None:
        from app.extensions import _get_pool
        pool = _get_pool()
        connection = pool.get_connection()
    cursor = connection.cursor()
    applied = _migration_history(cursor)
    sql_dir = sql_dir or current_app.config["MIGRATIONS_DIR"]

    try:
        for path in sorted(sql_dir.glob("*.sql")):
            version = path.name
            if version in applied:
                current_app.logger.info("Migration %s already applied, skipping", version)
                continue

            current_app.logger.info("Applying migration: %s", version)
            _apply_sql_file(cursor, path)

            if version == "0002_migrate_messages_to_prompt_runs.sql":
                _migrate_messages_to_prompt_runs(cursor)

            cursor.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                (version,),
            )
            connection.commit()
            current_app.logger.info("Migration %s applied successfully", version)

        cursor.close()
    except Exception as e:
        current_app.logger.error("Migration failed: %s", e)
        raise
    finally:
        if cursor:
            cursor.close()
