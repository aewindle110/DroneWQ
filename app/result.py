from pathlib import Path
from flask import jsonify, Blueprint
from flask import current_app as app
import sqlite3

bp = Blueprint("result", __name__)


@bp.route("/api/projects/<int:project_id>")
def results(project_id: int):
    try:
        with sqlite3.connect(app.config["DATABASE_PATH"]) as conn:
            cursor = conn.cursor()
            p = cursor.execute(
                """
                SELECT * 
                FROM projects
                WHERE id=?
                """,
                project_id,
            ).fetchall()

        project_folder = Path(p["folder_path"])
        result_folder = project_folder.joinpath("result")
        metadata = project_folder.joinpath("metadata.csv")
        ed_method = p["ed_method"]

        return jsonify(
            {
                "id": p["id"],
                "name": p["name"],
                "folder_path": p["folder_path"],
                "data_source": Path(p["folder_path"]).name,
                "lw_method": p["lw_method"],
                "created_at": p["created_at"],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)})
