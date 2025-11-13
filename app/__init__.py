from flask import Flask
from .process import bp as process_bp
from .manage import bp as manage_bp


def create_app():
    app = Flask(__name__)

    app.register_blueprint(manage_bp)

    app.register_blueprint(process_bp)

    return app
