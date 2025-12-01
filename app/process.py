# Everything related to computing and plotting results
from flask import Blueprint, jsonify, request
from models.model_project import Project
from pipeline import Pipeline

bp = Blueprint("process", __name__)


@bp.route("/api/process/new/<int:project_id>")
def process_new(project_id: int):
    try:
        settings = Project.get_project(project_id)
    except LookupError as e:
        return jsonify({str(e): f"Project {project_id} not found"})

    try:
        plot_args = {}
        for wq_alg in settings.wq_algs:
            plot_args[wq_alg] = {"vmin": 10, "vmax": 12}
        pipeline = Pipeline(settings.to_dict())

        # Different stages of processing
        # pipeline.water_metadata()
        # pipeline.flight_plan()
        # pipeline.run()
        # pipeline.plot_essentials()
        # pipeline.point_samples()
        # pipeline.wq_run()
        # pipeline.plot_wq(plot_args)
        # TODO: add mosaic

        return jsonify({"success": True}), 200
    except Exception as e:
        print(e)
        raise e


@bp.route("/api/process/updated/<int:project_id>")
def process_updated(project_id: int):
    try:
        settings = Project.get_project(project_id)
        plot_args = {}
        for wq_alg in settings.wq_algs:
            plot_args[wq_alg] = {"vmin": 10, "vmax": 12}

        pipeline = Pipeline(settings.to_dict())
        pipeline.plot_essentials()
        pipeline.wq_run()
        pipeline.plot_wq(plot_args)
        # TODO: add mosaic
        return jsonify({"Success": True}), 200
    except LookupError as e:
        return jsonify({str(e): f"Project {project_id} not found"})


# @bp.route("/api/process/mosaic", methods=["POST"])
# def draw_mosaic():
#     args = request.get_json(silent=True) or request.args


@bp.route("/api/plot/wq", methods=["POST"])
def update_wq_plot():
    args = request.get_json(silent=True) or request.args
    project_id = args.get("projectId")
    plot_args = args.get("plotParams")
    try:
        settings = Project.get_project(project_id)
        pipeline = Pipeline(settings.to_dict())
        pipeline.plot_wq(plot_args)
        return jsonify({"Success": True}), 200
    except LookupError as e:
        return jsonify({str(e): f"Project {project_id} not found"})
