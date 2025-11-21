import sqlite3

from flask import Flask
from .config import Config
from .process import bp as process_bp
from .projects import bp as projects_bp


def init_db(DB_PATH):
    print(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        folder_path TEXT NOT NULL,
        created_at TEXT NOT NULL,
        lw_method TEXT NOT NULL,
        ed_method TEXT NOT NULL,
        mask_method TEXT,
        wq_algs TEXT,
        mosaic TEXT
    );
    """
    )

    conn.commit()
    conn.close()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app.config["DATABASE_PATH"])

    app.register_blueprint(projects_bp)

    app.register_blueprint(process_bp)

    return app
