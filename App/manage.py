# Everything about managing Projects
from flask import Blueprint, request, jsonify
from dronewq.utils.settings import Settings
import os
import tempfile

bp = Blueprint("manage", __name__)


# Simple CORS support for the blueprint: allow requests from the frontend (Electron)
# and respond to preflight OPTIONS requests. This avoids adding a dependency while
# supporting cross-origin fetches from file:// or other origins during dev.
@bp.after_request
def _add_cors_headers(response):
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault(
        "Access-Control-Allow-Methods", "GET, POST, OPTIONS"
    )
    response.headers.setdefault(
        "Access-Control-Allow-Headers", "Content-Type, Authorization"
    )
    return response


@bp.route('/manage/make_project', methods=["OPTIONS"])
def make_project_options():
    # Preflight response for CORS
    return ("", 204)

#TODO: Figure out how to manage projects folder

def is_writable_dir(path: str, create_if_missing: bool = False) -> bool:
    """
    Return True if current process can write inside `path`.

    If path doesn't exist and create_if_missing is True, an attempt to create
    the directory will be made. The function then attempts to create + remove
    a temporary file inside `path` to confirm writability.

    This approach is preferred over os.access(path, os.W_OK) because it
    actually exercises the filesystem and handles ACLs/network mounts more reliably.
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
    #TODO: Should account for uppercase beginning chars
    needed_dirs = ["panel", "raw_water_imgs", "raw_sky_imgs", "align_img"]

    for dir in needed_dirs:
        if dir not in dirs:
            return False
    return True

#TODO: Automatic sorting
@bp.route('/manage/make_project', methods=["POST"])
def make_project():
    # Accept folderPath from JSON body (preferred) or query params for flexibility
    data = request.get_json(silent=True) or {}
    folder_path = data.get("folderPath") or request.args.get("folderPath")

    if folder_path is None:
        return jsonify({"error": "folderPath is not specified."}), 400

    # if not is_writable_dir(folder_path, create_if_missing=True):
    #     return jsonify({"error": "folderPath is not writable or cannot be created", "path": folder_path}), 400
    
    # if not check_folder_structure(folder_path):
    #     return jsonify({"error": "Directory structure is incorrect."}), 400

    settings = Settings()
    # Assuming the project sub-folders are sorted
    settings.configure(main_dir=folder_path)

    try: 
        settings.save(folder_path)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"Error while saving settings.": str(e)}), 500

@bp.route('/manage/save_settings', methods=["POST"])
def save_settings():
    args = request.args
    project_id = args.get("project_id")
    project_name = args.get("project_name")
    folder_path = args.get("folderPath")
    lw_method = args.get("lwMethod")
    ed_method = args.get("edMethod")
    mask_method = args.get("maskMethod")
    outputs = args.get("outputs")

    settings = Settings()

    if folder_path is None:
        return jsonify({"error": "folderPath is not specified."}), 400
    
    if os.path.exists(os.path.join(folder_path, "settings.pkl")):
        settings = settings.load(folder_path)
    else:
        settings.configure(main_dir=folder_path)
    
    settings.configure(
        project_id=project_id,
        project_name=project_name,
        lw_method=lw_method,
        ed_method=ed_method,
        mask_method=mask_method,
        outputs=outputs.split(",") if outputs else [],
    )

    try:
        settings.save(folder_path)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"Error while saving settings.": str(e)}), 500