from flask import Blueprint, request, jsonify
from .pipeline import Pipeline

bp = Blueprint("process", __name__)


@bp.route("/process", methods=["POST"])
def process():
    data = request.get_json(silent=True) or {}
    folder_path = data.get("folderPath")

    if folder_path is None:
        return jsonify({"error": "folderPath is not specified."}), 400

    pipeline = Pipeline(folder_path)

    pipeline.water_metadata()
    pipeline.flight_plan()
    pipeline.run()
    pipeline.plot_essentials()

    return jsonify({"success": True}), 200
