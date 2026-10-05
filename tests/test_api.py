import io
import re
import time
import zipfile

import pytest

from app.preprocess import MAX_PROMPT_CHARS
from app.renderer import check_output


def err_code(resp):
    return resp.get_json()["error"]["code"]


# ---------------------------------------------------------------- generate
def test_generate_returns_requirements_and_project(client):
    r = client.post("/api/generate", json={"prompt": "Portfolio for a freelance photographer named Maya Lin with a "
                                                     "photo gallery and pricing, in dark colors. maya@example.com"})
    assert r.status_code == 201
    d = r.get_json()
    req = d["requirements"]
    assert req["site_type"] == "portfolio"
    assert {"gallery", "pricing"} <= set(req["sections"]) and {"navbar", "hero", "footer"} <= set(req["sections"])
    assert req["slots"]["name"] == "Maya Lin" and req["slots"]["email"] == "maya@example.com"
    assert d["project"]["model"]["theme"]["palette"] == "midnight"
    assert d["timing_ms"] > 0 and d["project"]["id"] >= 1
    assert "low_confidence" in req and "confidence" in req


@pytest.mark.parametrize("body", [{}, {"prompt": ""}, {"prompt": "   \n\t "}, {"prompt": None}, {"prompt": 123},
                                  {"prompt": ["a"]}])
def test_generate_empty_or_invalid_prompt(client, body):
    r = client.post("/api/generate", json=body)
    assert r.status_code == 400 and err_code(r) == "empty_prompt"


def test_generate_overlong_prompt(client):
    r = client.post("/api/generate", json={"prompt": "bakery " * 300})
    assert r.status_code == 400 and err_code(r) == "prompt_too_long"
    ok = client.post("/api/generate", json={"prompt": ("bakery " * 200)[:MAX_PROMPT_CHARS]})
    assert ok.status_code == 201


def test_generate_invalid_json_and_wrong_type(client):
    r = client.post("/api/generate", data="not json", content_type="application/json")
    assert r.status_code == 400 and err_code(r) == "invalid_json"
    assert client.post("/api/generate", json=["x"]).status_code == 400


def test_generate_with_overrides(client):
    r = client.post("/api/generate", json={"prompt": "something for my business",
                                           "overrides": {"site_type": "blog", "sections": ["faq"],
                                                         "slots": {"name": "Notes"}}})
    req = r.get_json()["requirements"]
    assert req["site_type"] == "blog" and "faq" in req["sections"] and "gallery" not in req["sections"]
    assert req["slots"]["name"] == "Notes"
    assert set(req["overridden"]) >= {"site_type", "sections", "slot:name"} or "sections" in req["overridden"]


def test_low_confidence_prompts_are_flagged_not_silent(client):
    for text in ("asdf qwerty", "what is the capital of France", "hi", "quiero una pagina para mi escuela de musica"):
        req = client.post("/api/generate", json={"prompt": text}).get_json()["requirements"]
        assert req["low_confidence"] is True and req["low_confidence_reasons"], text
    good = client.post("/api/generate", json={"prompt": "A modern website for my bakery called Sweet Crumbs with a "
                                                         "menu, gallery and contact form"}).get_json()
    assert good["requirements"]["low_confidence"] is False


def test_regenerate(client, project):
    r = client.post(f"/api/projects/{project['id']}/regenerate",
                    json={"prompt": "A friendly site for a coding bootcamp with course listings and FAQ"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["project"]["id"] == project["id"] and d["project"]["model"]["site_type"] == "education"
    assert client.post(f"/api/projects/{project['id']}/regenerate", json={"prompt": ""}).status_code == 400
    assert client.post("/api/projects/9999/regenerate", json={"prompt": "bakery"}).status_code == 404


# ---------------------------------------------------------------- projects CRUD
def test_projects_list_get_update_delete(client, project):
    pid = project["id"]
    assert [p["id"] for p in client.get("/api/projects").get_json()["projects"]] == [pid]
    d = client.get(f"/api/projects/{pid}").get_json()
    assert d["project"]["name"] == project["name"] and d["feedback"] is None and d["edits"][0]["summary"]
    model = d["project"]["model"]
    model["sections"][1]["content"]["headline"] = "My new headline"
    model["sections"] = [s for s in model["sections"]]
    r = client.put(f"/api/projects/{pid}", json={"name": "Renamed", "model": model})
    assert r.status_code == 200 and r.get_json()["project"]["name"] == "Renamed"
    again = client.get(f"/api/projects/{pid}").get_json()
    assert again["project"]["model"]["sections"][1]["content"]["headline"] == "My new headline"
    assert "edited hero text" in again["edits"][0]["summary"]
    assert client.get(f"/preview/{pid}").data.decode().count("My new headline") >= 1
    assert client.delete(f"/api/projects/{pid}").get_json() == {"deleted": pid}
    assert client.get(f"/api/projects/{pid}").status_code == 404
    assert client.get("/api/projects").get_json()["projects"] == []


def test_update_validation_errors(client, project):
    pid = project["id"]
    assert client.put(f"/api/projects/{pid}", data="x", content_type="application/json").status_code == 400
    r = client.put(f"/api/projects/{pid}", json={"model": {"site_type": "nope"}})
    assert r.status_code == 400 and err_code(r) == "invalid_model"
    r = client.put(f"/api/projects/{pid}", json={"name": "  ", "model": project["model"]})
    assert r.status_code == 400 and err_code(r) == "invalid_name"
    assert client.put(f"/api/projects/{pid}", json={"model": None}).status_code == 400


def test_duplicate(client, project):
    r = client.post(f"/api/projects/{project['id']}/duplicate")
    assert r.status_code == 201
    dup = r.get_json()["project"]
    assert dup["id"] != project["id"] and dup["name"].endswith("(copy)") and dup["model"] == project["model"]
    assert len(client.get("/api/projects").get_json()["projects"]) == 2


@pytest.mark.parametrize("method,url", [("get", "/api/projects/999"), ("put", "/api/projects/999"),
                                        ("delete", "/api/projects/999"), ("post", "/api/projects/999/duplicate"),
                                        ("get", "/api/projects/999/export"), ("post", "/api/projects/999/feedback"),
                                        ("get", "/preview/999"), ("post", "/api/projects/999/regenerate")])
def test_unknown_project_id_returns_404_json(client, method, url):
    kwargs = {"json": {"rating": 4, "prompt": "bakery", "model": {}}} if method in ("put", "post") else {}
    r = getattr(client, method)(url, **kwargs)
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "not_found"


def test_editor_page_for_unknown_project_is_a_friendly_404(client):
    r = client.get("/editor/999")
    assert r.status_code == 404 and b"no project with id 999" in r.data


# ---------------------------------------------------------------- export and preview
def test_export_zip_contents_and_offline_rendering(client, project):
    r = client.get(f"/api/projects/{project['id']}/export")
    assert r.status_code == 200 and r.mimetype == "application/zip"
    assert "attachment" in r.headers["Content-Disposition"] and r.headers["Content-Disposition"].endswith('.zip"')
    z = zipfile.ZipFile(io.BytesIO(r.data))
    assert sorted(z.namelist()) == ["index.html", "script.js", "style.css"]
    files = {n: z.read(n).decode() for n in z.namelist()}
    assert check_output(files) == []
    html = files["index.html"]
    assert 'href="style.css"' in html and 'src="script.js"' in html            # relative: works from file://
    assert not re.search(r"https?://", "".join(files.values()))
    assert zipfile.ZipFile(io.BytesIO(client.get(f"/api/projects/{project['id']}/export").data)).read("index.html") \
        == z.read("index.html")                                                  # reproducible


def test_preview_post_and_get(client, project):
    r = client.post("/api/preview", json={"model": project["model"]})
    assert r.status_code == 200 and r.mimetype == "text/html" and b"<!DOCTYPE html>" in r.data
    assert r.data == client.get(f"/preview/{project['id']}").data
    bad = client.post("/api/preview", json={"model": {"nope": 1}})
    assert bad.status_code == 400 and err_code(bad) == "invalid_model"
    assert client.post("/api/preview", data="x", content_type="application/json").status_code == 400


def test_add_section_endpoint(client):
    r = client.post("/api/generate", json={"prompt": "bakery website with a menu", "overrides": {"sections": ["about"]}})
    model = r.get_json()["project"]["model"]
    assert "pricing" not in [s["type"] for s in model["sections"]]
    r2 = client.post("/api/model/add-section", json={"model": model, "section": "pricing"})
    assert r2.status_code == 200
    new = r2.get_json()["model"]
    assert "pricing" in [s["type"] for s in new["sections"]] and new["sections"][-1]["type"] == "footer"
    assert client.post("/api/model/add-section", json={"model": model, "section": "navbar"}).status_code == 400
    assert client.post("/api/model/add-section", json={"model": model, "section": "zzz"}).status_code == 400
    assert client.post("/api/model/add-section", json={"model": {}, "section": "faq"}).status_code == 400


# ---------------------------------------------------------------- feedback
def test_feedback_flow(client, project):
    pid = project["id"]
    assert client.get("/api/feedback/summary").get_json()["count"] == 0
    r = client.post(f"/api/projects/{pid}/feedback", json={"rating": 4, "comment": "nice"})
    assert r.status_code == 201 and r.get_json()["feedback"]["rating"] == 4
    client.post(f"/api/projects/{pid}/feedback", json={"rating": 5})
    s = client.get("/api/feedback/summary").get_json()
    assert s["count"] == 1 and s["average"] == 5.0
    assert client.get(f"/api/projects/{pid}").get_json()["feedback"]["rating"] == 5
    assert client.get("/api/projects").get_json()["projects"][0]["rating"] == 5


@pytest.mark.parametrize("body", [{"rating": 0}, {"rating": 6}, {"rating": "5"}, {"rating": 4.5}, {"rating": True},
                                  {}, {"rating": 3, "comment": "x" * 501}, {"rating": 3, "comment": 5}])
def test_feedback_validation(client, project, body):
    r = client.post(f"/api/projects/{project['id']}/feedback", json=body)
    assert r.status_code == 400 and err_code(r).startswith("invalid_")


# ---------------------------------------------------------------- meta / ml / eval / errors
def test_meta_ml_info_and_eval(client):
    meta = client.get("/api/meta").get_json()
    assert len(meta["site_types"]) >= 5 and meta["max_prompt_chars"] == MAX_PROMPT_CHARS
    assert {"navbar", "hero", "footer"} == set(meta["mandatory_sections"])
    info = client.get("/api/ml/info").get_json()
    assert info["metrics"]["test"]["site_type"]["accuracy"] > 0 and "Model card" in info["model_card"]
    assert info["confidence_threshold"] == info["metrics"]["confidence"]["threshold"]
    ev = client.get("/api/eval").get_json()
    assert ev["n"] >= 80 and ev["generation_time"]["mean_ms"] > 0 and ev["generation_time"]["p95_ms"] > 0
    assert len(ev["items"]) == ev["n"]


def test_eval_missing_gives_clear_error(tmp_path):
    import shutil
    from app import create_app
    from ml.predictor import ARTIFACT_DIR, REQUIRED_FILES
    d = tmp_path / "art"
    d.mkdir()
    for f in REQUIRED_FILES:
        shutil.copy(f"{ARTIFACT_DIR}/{f}", d / f)
    app = create_app({"ARTIFACT_DIR": str(d), "DATABASE": str(tmp_path / "x.sqlite3")})
    r = app.test_client().get("/api/eval")
    assert r.status_code == 404 and "train.sh" in r.get_json()["error"]["message"]


def test_unknown_routes_and_methods(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and err_code(r) == "not_found"
    assert client.get("/nope").status_code == 404
    r = client.get("/api/generate")
    assert r.status_code == 405 and err_code(r) == "method_not_allowed"
    assert client.post("/api/feedback/summary").status_code == 405


def test_security_headers(client):
    r = client.get("/api/meta")
    assert r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["Cache-Control"] == "no-store"


def test_generation_is_fast_enough(client):
    t0 = time.perf_counter()
    for _ in range(5):
        client.post("/api/generate", json={"prompt": "A modern website for my bakery called Sweet Crumbs with a menu"})
    assert (time.perf_counter() - t0) / 5 < 1.0       # "well under a second" on a laptop CPU
