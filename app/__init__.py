from flask import Flask

def create_app():
    app = Flask(__name__)

    from .manage import bp as manage_bp
    app.register_blueprint(manage_bp)

    from .process import bp as process_bp
    app.register_blueprint(process_bp)

    return app
