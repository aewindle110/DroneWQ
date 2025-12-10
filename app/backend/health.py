"""Created by Temuulen"""

from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)


@bp.route("/health")
def check_health():
    return jsonify({"success": True}), 200
