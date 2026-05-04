from flask import Flask

from app.blueprints.admin import admin_bp
from app.blueprints.api import api_bp
from app.blueprints.experiments import experiments_bp
from app.blueprints.public import public_bp
from app.config import Config, get_config
from app.extensions import close_db, init_app as init_extensions
from dotenv import load_dotenv


def create_app(config_object=None) -> Flask:
    load_dotenv()

    if config_object is None:
        config_object = get_config()

    # Reload config from environment
    Config.reload()

    app = Flask(__name__)
    if isinstance(config_object, dict):
        app.config.from_object(Config)
        app.config.from_mapping(config_object)
    else:
        app.config.from_object(config_object)

    init_extensions(app)
    app.register_blueprint(public_bp)
    app.register_blueprint(experiments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.teardown_appcontext(close_db)

    if hasattr(config_object, 'init_app'):
        config_object.init_app(app)

    return app
