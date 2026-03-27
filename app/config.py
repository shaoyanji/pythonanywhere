import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    APP_NAME = os.getenv("APP_NAME", "Shaoyan Ji Lab")
    APP_TAGLINE = os.getenv(
        "APP_TAGLINE",
        "Personal notes, experiments, and operational tools in one restrained Flask site.",
    )
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB")
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_SSL_DISABLED = os.getenv("MYSQL_SSL_DISABLED", "1") == "1"
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    ADMIN_TOOLS_ENABLED = os.getenv("ADMIN_TOOLS_ENABLED", "0") == "1"
    ENABLE_ADMIN_DEPLOY = os.getenv("ENABLE_ADMIN_DEPLOY", "0") == "1"
    DEPLOY_RELOAD_COMMAND = os.getenv("DEPLOY_RELOAD_COMMAND", "pa webapp reload")
    GIT_PULL_COMMAND = os.getenv("GIT_PULL_COMMAND")
    CONTENT_HTML_TAGS = [
        "a",
        "blockquote",
        "code",
        "em",
        "h1",
        "h2",
        "h3",
        "hr",
        "li",
        "ol",
        "p",
        "pre",
        "strong",
        "ul",
    ]
    CONTENT_HTML_ATTRIBUTES = {
        "a": ["href", "title", "rel", "target"],
    }
    MIGRATIONS_DIR = BASE_DIR / "migrations" / "sql"

    @staticmethod
    def db_name() -> str | None:
        user = os.getenv("MYSQL_USER")
        explicit = os.getenv("MYSQL_DB")
        if explicit:
            return explicit
        if user:
            return f"{user}$default"
        return None

    @staticmethod
    def db_host() -> str | None:
        user = os.getenv("MYSQL_USER")
        explicit = os.getenv("MYSQL_HOST")
        if explicit:
            return explicit
        if user:
            return f"{user}.mysql.pythonanywhere-services.com"
        return None


Config.MYSQL_DB = Config.db_name()
Config.MYSQL_HOST = Config.db_host()

