"""Created by Temuulen"""

from flask import Blueprint, jsonify
from models.model_project import Project

bp = Blueprint("result", __name__)


@bp.route("/api/projects/<int:project_id>")
def get_project(project_id: int):
    try:
        project = Project.get_project(project_id)
        return jsonify(project.to_dict())
    except LookupError as e:
        return jsonify({str(e): f"Project {project_id} not found"})
