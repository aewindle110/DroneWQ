from flask import Blueprint, jsonify, request
import os

from pipeline import Pipeline
from description_generator import generate_plot_descriptions
from config import Config

bp = Blueprint("process", __name__)


@bp.route("/api/process", methods=["POST"])
def process():
    data = request.get_json(silent=True) or {}
    folder_path = data.get("folderPath")

    if folder_path is None:
        return jsonify({"error": "folderPath is not specified."}), 400

    try:
        # pipeline = Pipeline(folder_path)

        # pipeline.water_metadata()
        # pipeline.flight_plan()
        # pipeline.run()
        # pipeline.plot_essentials()
        # pipeline.point_samples()
        # pipeline.wq_run()
        
        # After all plots are generated, generate descriptions
        result_folder = os.path.join(folder_path, 'result')
        try:
            print("Generating accessibility descriptions...")
            generate_plot_descriptions(result_folder, Config.GEMINI_API_KEY)
        except Exception as e:
            print(f"Failed to generate accessibility descriptions: {e}")
            # Don't fail the whole process if descriptions fail
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500