# Everything about managing Projects
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask import current_app as app

bp = Blueprint("projects", __name__)


@bp.route("/api/projects")
def get_all_projects():
    with sqlite3.connect(
        app.config["DATABASE_PATH"],
    ) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        projects = c.execute(
            """
            SELECT id, name, folder_path, lw_method, ed_method, mask_method, mask_args, wq_algs, created_at
            FROM projects
            """,
        ).fetchall()

    # Convert rows → JSON
    result = []
    for p in projects:
        result.append(
            {
                "id": p["id"],
                "name": p["name"],
                "folder_path": p["folder_path"],
                "data_source": Path(p["folder_path"]).name,
                "lw_method": p["lw_method"],
                "ed_method": p["ed_method"],
                "mask_method": p["mask_method"],
                "masking_params": json.loads(p["mask_args"]) if p["mask_args"] else {},
                "wq_algs": json.loads(p["wq_algs"]) if p["wq_algs"] else [],
                "created_at": p["created_at"],
            },
        )

    return jsonify(result)


@bp.route("/api/projects/<int:project_id>/delete", methods=["DELETE"])
def delete_project(project_id: int):
    try:
        with sqlite3.connect(
            app.config["DATABASE_PATH"],
        ) as conn:
            c = conn.cursor()

            c.execute(
                """
                DELETE FROM projects
                WHERE id=?
                """,
                (project_id,),
            )

        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def is_writable_dir(path: str, create_if_missing: bool = False) -> bool:
    """
    Return True if current process can write inside `path`.

    If path doesn't exist and create_if_missing is True, an attempt to create
    the directory will be made. The function then attempts to create + remove
    a temporary file inside `path` to confirm writability.

    This approach is preferred over os.access(path, os.W_OK) because it
    actually exercises the filesystem and handles ACLs/network mounts more
    reliably.
    """
    try:
        if not os.path.exists(path):
            if create_if_missing:
                os.makedirs(path, exist_ok=True)
            else:
                # If the folder doesn't exist, check if parent is writable
                parent = os.path.dirname(path) or "."
                return os.access(parent, os.W_OK)

        # Attempt to create a temporary file inside the directory
        fd, tmp = tempfile.mkstemp(dir=path)
        os.close(fd)
        os.remove(tmp)
        return True
    except Exception:
        return False


def check_folder_structure(folder_path: str) -> bool:
    dirs = os.listdir(folder_path)
    # TODO: Should account for uppercase beginning chars
    needed_dirs = ["panel", "raw_water_imgs", "raw_sky_imgs", "align_img"]

    count = 0

    for dir in needed_dirs:
        if dir in dirs:
            count += 1

    if count >= 3:
        return True
    return False


# TODO: Automatic sorting
@bp.route("/api/projects/check_folder", methods=["POST"])
def check_folder():
    # Accept folderPath from JSON body (preferred)
    # or query params for flexibility
    data = request.get_json(silent=True) or request.args
    folder_path = data.get("folderPath")

    if folder_path is None:
        return jsonify({"error": "folderPath is not specified."}), 400

    # if not is_writable_dir(folder_path, create_if_missing=True):
    #     return jsonify({"error": "folderPath is not writable or cannot be created", "path": folder_path}), 400

    if not check_folder_structure(folder_path):
        return jsonify({"error": "Directory structure is incorrect."}), 400

    return jsonify({"success": True}), 200


@bp.route("/api/projects/new", methods=["POST"])
def new_project():
    """Create new project"""
    # receive payload from frontend
    args = request.get_json(silent=True) or request.args
    project_name = args.get("project_name")
    folder_path = args.get("folderPath")
    rrs_count = args.get("rrs_count")
    lw_method = str(args.get("lwMethod"))
    ed_method = str(args.get("edMethod"))
    mask_method = str(args.get("maskMethod"))
    mask_args = args.get("maskingParams")
    wq_algs = args.get("wqAlgs")
    mosaic = args.get("mosaic")

    if folder_path is None:
        return jsonify({"error": "folderPath is not specified."}), 400
    if not Path(folder_path).exists():
        return jsonify({"error": f"{folder_path} does not exist."}), 400

    lw_method = lw_method.lower().strip().replace(" ", "_")
    ed_method = ed_method.lower().strip().replace(" ", "_")

    if mask_method is not None:
        mask_method = mask_method.lower().strip().replace(" ", "_")

    created_at = datetime.now().isoformat()

    try:
        # Insert project into DB
        with sqlite3.connect(app.config["DATABASE_PATH"]) as conn:
            c = conn.cursor()

            c.execute(
                """
                INSERT INTO projects 
                    (name, folder_path, created_at, rrs_count, lw_method, ed_method, mask_method, mask_args, wq_algs, mosaic)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    project_name,
                    folder_path,
                    created_at,
                    rrs_count,
                    lw_method,
                    ed_method,
                    mask_method,
                    json.dumps(mask_args) if mask_args else None,
                    json.dumps(wq_algs) if wq_algs else None,
                    mosaic,
                ),
            )

            project_id = c.lastrowid
            conn.commit()

        return (
            jsonify(
                {
                    "id": project_id,
                    "name": project_name,
                    "folder_path": folder_path,
                    "data_source": Path(folder_path).name,
                    "created_at": created_at,
                    "lw_method": lw_method,
                    "ed_method": ed_method,
                    "mask_method": mask_method,
                    "masking_params": mask_args,
                    "wq_algs": wq_algs,
                    "mosaic": mosaic,
                },
            ),
            200,
        )
    except Exception as e:
        return jsonify({"Error while saving settings.": str(e)}), 500


@bp.route("/api/projects/update", methods=["POST"])
def update_project():
    args = request.get_json(silent=True) or request.args
    project_id = args.get("projectId")
    project_name = args.get("name")
    rrs_count = args.get("rrs_count")
    wq_algs = args.get("wq_algs")

    try:
        # update project into DB
        with sqlite3.connect(app.config["DATABASE_PATH"]) as conn:
            c = conn.cursor()

            c.execute(
                """
                UPDATE projects 
                SET name = ?, rrs_count = ?, wq_algs = ?
                WHERE id = ?
            """,
                (
                    project_name,
                    rrs_count,
                    json.dumps(wq_algs) if wq_algs else None,
                    project_id,
                ),
            )
            conn.commit()

        return jsonify({"Success": True}), 200

    except Exception as e:
        return jsonify({"Error while saving settings.": str(e)}), 500
