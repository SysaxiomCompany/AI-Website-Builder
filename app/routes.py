"""Flask API and pages."""
import json
import os
import re

from flask import Blueprint, Response, current_app, jsonify, render_template, request

from ml.predictor import MANDATORY_SECTIONS, SECTIONS, SITE_TYPES
from .assembler import add_section, content_bank
from .preprocess import MAX_PROMPT_CHARS, normalize_prompt
from .renderer import RenderError, build_zip, render_preview
from .sitemodel import ModelError, summarize_edit, validate_model
from .store import NotFound
from .theme import FONTS, PALETTES

bp = Blueprint("main", __name__)

EXAMPLES = [
    "A modern website for my bakery called Sweet Crumbs with a menu, gallery and contact form",
    "Portfolio for a freelance photographer named Maya Lin with a photo gallery and pricing, in dark colors",
    "A friendly site for a coding bootcamp with course listings, FAQ and student reviews",
    "Simple blog about hiking and travel, email hello@trailnotes.example",
    "Website for an animal shelter called Happy Paws in Austin with volunteer stories and ways to donate",
    "Professional site for a plumbing company in Denver with services, pricing and customer reviews",
]


def _ctx():
    return current_app.extensions["aiwb"]


def api_error(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


@bp.after_app_request
def _headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.app_errorhandler(404)
def _not_found(_e):
    if request.path.startswith("/api/"):
        return api_error("not_found", "That endpoint does not exist.", 404)
    return render_template("error.html", title="Page not found",
                           message="That page does not exist."), 404


@bp.app_errorhandler(405)
def _bad_method(_e):
    return api_error("method_not_allowed", "That method is not allowed here.", 405)


@bp.app_errorhandler(413)
def _too_large(_e):
    return api_error("too_large", "The request is too large.", 413)


@bp.app_errorhandler(500)
def _server_error(_e):
    return api_error("server_error", "Something went wrong on the server.", 500)


# ---------------------------------------------------------------- pages
@bp.route("/")
def builder_page():
    return render_template("builder.html", page="builder", examples=EXAMPLES, max_chars=MAX_PROMPT_CHARS)


@bp.route("/editor/<int:pid>")
def editor_page(pid):
    try:
        _ctx()["store"].get(pid)
    except NotFound:
        return render_template("error.html", title="Project not found",
                               message=f"There is no project with id {pid}. It may have been deleted."), 404
    return render_template("editor.html", page="editor", pid=pid, max_chars=MAX_PROMPT_CHARS)


@bp.route("/projects")
def projects_page():
    return render_template("projects.html", page="projects")


@bp.route("/about")
def about_page():
    return render_template("about.html", page="about")


@bp.route("/preview/<int:pid>")
def preview_saved(pid):
    try:
        project = _ctx()["store"].get(pid)
    except NotFound:
        return api_error("not_found", f"No project with id {pid}.", 404)
    return Response(render_preview(project["model"]), mimetype="text/html")


# ---------------------------------------------------------------- helpers
def _check_prompt(data):
    prompt = data.get("prompt") if data else None
    if not isinstance(prompt, str):
        return None, api_error("empty_prompt", "Please type a description of the website you want.", 400)
    text = normalize_prompt(prompt)
    if not text:
        return None, api_error("empty_prompt", "Please type a description of the website you want.", 400)
    if len(text) > MAX_PROMPT_CHARS:
        return None, api_error("prompt_too_long",
                               f"The description is too long ({len(text)} characters; the limit is "
                               f"{MAX_PROMPT_CHARS}). Please shorten it.", 400)
    return text, None


def _generation_payload(project, result):
    return {"project": project, "requirements": result["requirements"],
            "timing_ms": round(result["timing_ms"], 2)}


# ---------------------------------------------------------------- generation
@bp.route("/api/generate", methods=["POST"])
def api_generate():
    data = _json_body()
    if data is None:
        return api_error("invalid_json", "The request body must be a JSON object.", 400)
    text, err = _check_prompt(data)
    if err:
        return err
    result = _ctx()["engine"].generate(text, data.get("overrides"))
    model = result["model"]
    project = _ctx()["store"].create(model["slots"]["name"], text, model)
    return jsonify(_generation_payload(project, result)), 201


@bp.route("/api/projects/<int:pid>/regenerate", methods=["POST"])
def api_regenerate(pid):
    data = _json_body()
    if data is None:
        return api_error("invalid_json", "The request body must be a JSON object.", 400)
    store = _ctx()["store"]
    try:
        store.get(pid)
    except NotFound:
        return api_error("not_found", f"No project with id {pid}.", 404)
    text, err = _check_prompt(data)
    if err:
        return err
    result = _ctx()["engine"].generate(text, data.get("overrides"))
    model = result["model"]
    project = store.update(pid, model["slots"]["name"], text, model, "regenerated from prompt")
    return jsonify(_generation_payload(project, result))


@bp.route("/api/preview", methods=["POST"])
def api_preview():
    data = _json_body()
    if data is None:
        return api_error("invalid_json", "The request body must be a JSON object.", 400)
    try:
        html = render_preview(data.get("model"))
    except ModelError as exc:
        return api_error("invalid_model", str(exc), 400)
    return Response(html, mimetype="text/html")


@bp.route("/api/model/add-section", methods=["POST"])
def api_add_section():
    """Add a section that was not generated (its sample copy comes from the content bank)."""
    data = _json_body()
    if data is None:
        return api_error("invalid_json", "The request body must be a JSON object.", 400)
    section = data.get("section")
    if section not in SECTIONS or section in MANDATORY_SECTIONS:
        return api_error("invalid_section", "Unknown section.", 400)
    try:
        model = add_section(validate_model(data.get("model")), section)
        model = validate_model(model)
    except ModelError as exc:
        return api_error("invalid_model", str(exc), 400)
    return jsonify({"model": model})


# ---------------------------------------------------------------- projects
@bp.route("/api/projects", methods=["GET"])
def api_projects():
    return jsonify({"projects": _ctx()["store"].list()})


@bp.route("/api/projects/<int:pid>", methods=["GET"])
def api_project(pid):
    store = _ctx()["store"]
    try:
        project = store.get(pid)
    except NotFound:
        return api_error("not_found", f"No project with id {pid}.", 404)
    return jsonify({"project": project, "feedback": store.get_feedback(pid), "edits": store.edits(pid)[:20]})


@bp.route("/api/projects/<int:pid>", methods=["PUT"])
def api_update(pid):
    data = _json_body()
    if data is None:
        return api_error("invalid_json", "The request body must be a JSON object.", 400)
    store = _ctx()["store"]
    try:
        old = store.get(pid)
    except NotFound:
        return api_error("not_found", f"No project with id {pid}.", 404)
    try:
        model = validate_model(data.get("model"))
    except ModelError as exc:
        return api_error("invalid_model", str(exc), 400)
    name = data.get("name", old["name"])
    if not isinstance(name, str) or not name.strip():
        return api_error("invalid_name", "The project name cannot be empty.", 400)
    name = name.strip()[:80]
    summary = summarize_edit(validate_model(old["model"]), model)
    project = store.update(pid, name, model.get("prompt") or old["prompt"], model, summary)
    return jsonify({"project": project})


@bp.route("/api/projects/<int:pid>", methods=["DELETE"])
def api_delete(pid):
    try:
        _ctx()["store"].delete(pid)
    except NotFound:
        return api_error("not_found", f"No project with id {pid}.", 404)
    return jsonify({"deleted": pid})


@bp.route("/api/projects/<int:pid>/duplicate", methods=["POST"])
def api_duplicate(pid):
    try:
        project = _ctx()["store"].duplicate(pid)
    except NotFound:
        return api_error("not_found", f"No project with id {pid}.", 404)
    return jsonify({"project": project}), 201


@bp.route("/api/projects/<int:pid>/export", methods=["GET"])
def api_export(pid):
    try:
        project = _ctx()["store"].get(pid)
    except NotFound:
        return api_error("not_found", f"No project with id {pid}.", 404)
    try:
        payload = build_zip(project["model"])
    except (ModelError, RenderError) as exc:
        return api_error("export_failed", f"The site could not be exported: {exc}", 500)
    slug = re.sub(r"[^a-z0-9]+", "-", project["name"].lower()).strip("-") or "website"
    return Response(payload, mimetype="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{slug}.zip"'})


@bp.route("/api/projects/<int:pid>/feedback", methods=["POST"])
def api_feedback(pid):
    data = _json_body()
    if data is None:
        return api_error("invalid_json", "The request body must be a JSON object.", 400)
    rating = data.get("rating")
    if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
        return api_error("invalid_rating", "The rating must be a whole number from 1 to 5.", 400)
    comment = data.get("comment", "")
    if comment is None:
        comment = ""
    if not isinstance(comment, str) or len(comment) > 500:
        return api_error("invalid_comment", "The comment must be text of at most 500 characters.", 400)
    try:
        fb = _ctx()["store"].set_feedback(pid, rating, comment.strip())
    except NotFound:
        return api_error("not_found", f"No project with id {pid}.", 404)
    return jsonify({"feedback": fb, "summary": _ctx()["store"].feedback_summary()}), 201


@bp.route("/api/feedback/summary", methods=["GET"])
def api_feedback_summary():
    return jsonify(_ctx()["store"].feedback_summary())


# ---------------------------------------------------------------- meta / ML info
@bp.route("/api/meta", methods=["GET"])
def api_meta():
    models = _ctx()["models"]
    return jsonify({
        "site_types": [{"id": t, "label": content_bank(t)["label"]} for t in SITE_TYPES],
        "sections": SECTIONS, "mandatory_sections": MANDATORY_SECTIONS,
        "palettes": [{"id": k, "label": v["label"], "swatch": v["swatch"]} for k, v in PALETTES.items()],
        "fonts": [{"id": k, "label": v} for k, v in FONTS.items()],
        "max_prompt_chars": MAX_PROMPT_CHARS,
        "confidence_threshold": models.confidence_threshold,
        "nav_labels": {t: content_bank(t)["nav_labels"] for t in SITE_TYPES},
    })


@bp.route("/api/ml/info", methods=["GET"])
def api_ml_info():
    models = _ctx()["models"]
    info = dict(models.metrics)
    return jsonify({"metrics": info, "model_card": models.model_card, "site_types": SITE_TYPES,
                    "sections": SECTIONS, "mandatory_sections": MANDATORY_SECTIONS,
                    "confidence_threshold": models.confidence_threshold})


@bp.route("/api/eval", methods=["GET"])
def api_eval():
    path = os.path.join(current_app.config["ARTIFACT_DIR"], "eval_results.json")
    if not os.path.isfile(path):
        return api_error("no_eval", "eval_results.json has not been created yet. Run train.sh "
                                    "(macOS/Linux) or train.bat (Windows).", 404)
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))
