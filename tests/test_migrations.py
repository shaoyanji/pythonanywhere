import tempfile
import unittest
from pathlib import Path

from app.factory import create_app
from app.services.migrations import migrate_database


class FakeCursor:
    def __init__(self, state):
        self.state = state
        self.last_fetchone = None
        self.last_fetchall = []

    def execute(self, query, params=None, multi=False):
        normalized = " ".join(query.split())
        self.state["queries"].append(normalized)

        if multi:
            return []

        if normalized.startswith("CREATE TABLE IF NOT EXISTS schema_migrations"):
            return None

        if normalized.startswith("SELECT version FROM schema_migrations"):
            self.last_fetchall = [(version,) for version in sorted(self.state["applied_versions"])]
            return None

        if normalized.startswith("SHOW TABLES LIKE 'messages'"):
            self.last_fetchone = ("messages",) if self.state["messages_exists"] else None
            return None

        if normalized.startswith("INSERT INTO prompt_runs"):
            self.state["prompt_copy_runs"] += 1
            return None

        if normalized.startswith("INSERT INTO schema_migrations"):
            self.state["applied_versions"].add(params[0])
            return None

        return None

    def fetchone(self):
        return self.last_fetchone

    def fetchall(self):
        return self.last_fetchall

    def close(self):
        return None


class FakeConnection:
    def __init__(self, messages_exists):
        self.state = {
            "messages_exists": messages_exists,
            "applied_versions": set(),
            "prompt_copy_runs": 0,
            "queries": [],
            "commits": 0,
        }

    def cursor(self):
        return FakeCursor(self.state)

    def commit(self):
        self.state["commits"] += 1


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True})

    def _write_migrations(self, directory: Path):
        (directory / "0001_core.sql").write_text("CREATE TABLE pages (id INT);")
        (directory / "0002_copy.sql").write_text("CREATE TABLE prompt_runs (id INT);")

    def test_migrations_are_idempotent_and_copy_legacy_messages_once(self):
        with tempfile.TemporaryDirectory() as tempdir:
            sql_dir = Path(tempdir)
            self._write_migrations(sql_dir)
            connection = FakeConnection(messages_exists=True)

            with self.app.app_context():
                migrate_database(connection=connection, sql_dir=sql_dir)
                migrate_database(connection=connection, sql_dir=sql_dir)

            self.assertEqual(connection.state["prompt_copy_runs"], 0)
            self.assertEqual(connection.state["applied_versions"], {"0001_core.sql", "0002_copy.sql"})
            self.assertEqual(connection.state["commits"], 2)

    def test_legacy_copy_runs_once_for_real_migration_name(self):
        with tempfile.TemporaryDirectory() as tempdir:
            sql_dir = Path(tempdir)
            (sql_dir / "0001_core_schema.sql").write_text("CREATE TABLE pages (id INT);")
            (sql_dir / "0002_migrate_messages_to_prompt_runs.sql").write_text(
                "CREATE TABLE prompt_runs (id INT);"
            )
            connection = FakeConnection(messages_exists=True)

            with self.app.app_context():
                migrate_database(connection=connection, sql_dir=sql_dir)
                migrate_database(connection=connection, sql_dir=sql_dir)

            self.assertEqual(connection.state["prompt_copy_runs"], 1)
            self.assertEqual(connection.state["commits"], 2)

    def test_fresh_bootstrap_works_without_legacy_messages_table(self):
        with tempfile.TemporaryDirectory() as tempdir:
            sql_dir = Path(tempdir)
            (sql_dir / "0001_core_schema.sql").write_text("CREATE TABLE pages (id INT);")
            (sql_dir / "0002_migrate_messages_to_prompt_runs.sql").write_text(
                "CREATE TABLE prompt_runs (id INT);"
            )
            connection = FakeConnection(messages_exists=False)

            with self.app.app_context():
                migrate_database(connection=connection, sql_dir=sql_dir)

            self.assertEqual(connection.state["prompt_copy_runs"], 0)
            self.assertEqual(
                connection.state["applied_versions"],
                {"0001_core_schema.sql", "0002_migrate_messages_to_prompt_runs.sql"},
            )


if __name__ == "__main__":
    unittest.main()
