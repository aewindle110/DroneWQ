import json
import sqlite3
from pathlib import Path

from flask import Blueprint, jsonify
from flask import current_app as app

bp = Blueprint("result", __name__)


@bp.route("/api/projects/<int:project_id>")
def get_project(project_id: int):
    with sqlite3.connect(
        app.config["DATABASE_PATH"],
    ) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        project = c.execute(
            """
            SELECT id, name, folder_path, lw_method, ed_method, mask_method, wq_algs, created_at
            FROM projects
            WHERE id=?
            """,
            (project_id,),
        ).fetchone()

    if project is None:
        return jsonify({"error": "Project not found"}), 404

    # Convert rows → JSON
    result = {
        "id": project["id"],
        "name": project["name"],
        "folder_path": project["folder_path"],
        "data_source": Path(project["folder_path"]).name,
        "lw_method": project["lw_method"],
        "ed_method": project["ed_method"],
        "mask_method": project["mask_method"],
        "wq_algs": json.loads(project["wq_algs"]) if project["wq_algs"] else [],
        "created_at": project["created_at"],
    }

    return jsonify(result)
