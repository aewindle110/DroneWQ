from flask import Blueprint, jsonify, request

from .pipeline import Pipeline

bp = Blueprint("process", __name__)


@bp.route("/api/process", methods=["POST"])
def process():
    data = request.get_json(silent=True) or {}
    folder_path = data.get("folderPath")

    if folder_path is None:
        return jsonify({"error": "folderPath is not specified."}), 400

    try:
        pipeline = Pipeline(folder_path)

        # pipeline.water_metadata()
        # pipeline.flight_plan()
        # pipeline.run()
        # pipeline.plot_essentials()
        # pipeline.point_samples()
        # pipeline.wq_run()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
