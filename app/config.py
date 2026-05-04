import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _strip_quotes(value: str | None) -> str | None:
    """Strip surrounding quotes from env var values."""
    if value is None:
        return None
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _compute_db_name() -> str | None:
    user = _strip_quotes(os.getenv("MYSQL_USER"))
    explicit = _strip_quotes(os.getenv("MYSQL_DB"))
    if explicit:
        return explicit
    if user:
        return f"{user}$default"
    return None


def _compute_db_host() -> str | None:
    user = _strip_quotes(os.getenv("MYSQL_USER"))
    explicit = _strip_quotes(os.getenv("MYSQL_HOST"))
    if explicit:
        return explicit
    if user:
        return f"{user}.mysql.pythonanywhere-services.com"
    return None


class Config:
    SECRET_KEY = _strip_quotes(os.getenv("SECRET_KEY", "dev-secret-key-change-me"))
    APP_NAME = _strip_quotes(os.getenv("APP_NAME", "Shaoyan Ji Lab"))
    APP_TAGLINE = _strip_quotes(
        os.getenv(
            "APP_TAGLINE",
            "Personal notes, experiments, and operational tools in one restrained Flask site.",
        )
    )
    MYSQL_USER = _strip_quotes(os.getenv("MYSQL_USER"))
    MYSQL_PASSWORD = _strip_quotes(os.getenv("MYSQL_PASSWORD"))
    MYSQL_DB = _compute_db_name()
    MYSQL_HOST = _compute_db_host()
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_SSL_DISABLED = os.getenv("MYSQL_SSL_DISABLED", "1") == "1"
    ADMIN_USERNAME = _strip_quotes(os.getenv("ADMIN_USERNAME", "admin"))
    ADMIN_PASSWORD_HASH = _strip_quotes(os.getenv("ADMIN_PASSWORD_HASH"))
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
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    @classmethod
    def validate_production(cls):
        """Validate required config for production."""
        errors = []
        if not cls.SECRET_KEY or cls.SECRET_KEY == "dev-secret-key-change-me":
            errors.append("SECRET_KEY must be set to a secure value in production")
        if not cls.ADMIN_PASSWORD_HASH:
            errors.append("ADMIN_PASSWORD_HASH must be set (hash of ADMIN_PASSWORD)")
        if not cls.MYSQL_PASSWORD:
            errors.append("MYSQL_PASSWORD must be set")
        if errors:
            raise ValueError("Configuration errors: " + "; ".join(errors))


class DevelopmentConfig(Config):
    FLASK_DEBUG = True


class ProductionConfig(Config):
    FLASK_DEBUG = False

    @classmethod
    def init_app(cls, app):
        cls.validate_production()


def get_config():
    """Return appropriate config based on environment."""
    env = os.getenv("FLASK_ENV", "development")
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig

