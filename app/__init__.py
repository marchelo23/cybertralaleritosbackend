import os
from flask import Flask


def create_app(config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["DEBUG"] = os.environ.get("DEBUG", "0") == "1"

    from app.routes import bp
    app.register_blueprint(bp)

    return app
