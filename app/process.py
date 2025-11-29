import json
import sqlite3
from pathlib import Path

# from description_generator import generate_plot_descriptions
from flask import Blueprint, jsonify, request
from flask import current_app as app
from pipeline import Pipeline

bp = Blueprint("process", __name__)


def __get_project(project_id: int):
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
    return {
        "id": project["id"],
        "name": project["name"],
        "main_dir": project["folder_path"],
        "data_source": Path(project["folder_path"]).name,
        "lw_method": project["lw_method"],
        "ed_method": project["ed_method"],
        "mask_method": project["mask_method"],
        "wq_algs": json.loads(project["wq_algs"]) if project["wq_algs"] else [],
        "created_at": project["created_at"],
    }


@bp.route("/api/process_new", methods=["POST"])
def process_new():
    data = request.get_json(silent=True) or request.args
    project_id = data.get("projectId")

    settings = __get_project(project_id)

    try:
        pipeline = Pipeline(settings)

        # pipeline.water_metadata()
        # pipeline.flight_plan()
        # pipeline.run()
        # pipeline.plot_essentials()
        # pipeline.point_samples()
        # pipeline.wq_run()

        # After all plots are generated, generate descriptions
        # result_folder = os.path.join(folder_path, "result")
        try:
            print("Generating accessibility descriptions...")
            # generate_plot_descriptions(result_folder, Config.GEMINI_API_KEY)
        except Exception as e:
            print(f"Failed to generate accessibility descriptions: {e}")
            # Don't fail the whole process if descriptions fail

        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
