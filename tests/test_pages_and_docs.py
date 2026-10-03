import json
import os
import re
from html.parser import HTMLParser

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = [("/", "Describe the website you want"), ("/projects", "Projects"), ("/about", "About the AI")]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.stack = [], []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src", "action") and v:
                self.refs.append(v)


@pytest.mark.parametrize("path,heading", PAGES)
def test_pages_render_with_theme_toggle_and_icons(client, path, heading):
    r = client.get(path)
    assert r.status_code == 200
    html = r.data.decode()
    assert heading in html and 'id="theme-toggle"' in html
    assert 'name="viewport"' in html and "favicon.ico" in html and "icon-180.png" in html
    p = Links()
    p.feed(html)
    for ref in p.refs:
        assert not re.match(r"(https?:)?//", ref), ref                              # no external requests
        if ref.startswith("/static/"):
            assert client.get(ref).status_code == 200, ref


def test_editor_page_renders(client, project):
    html = client.get(f"/editor/{project['id']}").data.decode()
    assert 'sandbox="allow-scripts"' in html and "Desktop" in html and "Tablet" in html and "Mobile" in html
    assert "Download ZIP" in html and "Rate" in html


def test_no_external_urls_anywhere_in_ui_or_site_assets():
    bad = re.compile(r"https?://|(?<![:\w\"'])//[a-z]|@import|url\(\s*['\"]?https?:", re.I)
    roots = [os.path.join(ROOT, d) for d in ("app/templates", "app/static", "site_templates", "content")]
    for base in roots:
        for folder, _, files in os.walk(base):
            for f in files:
                if f.endswith((".png", ".ico")):
                    continue
                text = open(os.path.join(folder, f), encoding="utf-8").read()
                assert not bad.search(text), os.path.join(folder, f)


def test_builder_ui_uses_system_fonts_only():
    css = open(os.path.join(ROOT, "app/static/css/app.css"), encoding="utf-8").read()
    assert "@font-face" not in css and "system-ui" in css


def test_about_page_has_no_hardcoded_measurements():
    """The About page must read metrics from the API: no digits-with-% / ms literals in its template or script."""
    html = open(os.path.join(ROOT, "app/templates/about.html"), encoding="utf-8").read()
    js = open(os.path.join(ROOT, "app/static/js/about.js"), encoding="utf-8").read()
    assert "/api/ml/info" in js and "/api/eval" in js and "/api/feedback/summary" in js
    assert not re.search(r"\b\d+(\.\d+)?\s?%|\b\d+(\.\d+)?\s?ms\b", html)
    assert not re.search(r"['\"]\d+(\.\d+)?\s?%|['\"]\d+(\.\d+)?\s?ms\b", js)


def test_dark_theme_defined_for_builder_ui():
    css = open(os.path.join(ROOT, "app/static/css/app.css"), encoding="utf-8").read()
    assert 'html[data-theme="dark"]' in css and 'html[data-theme="light"]' in css


# ---------------------------------------------------------------- docs match code
def test_docs_match_code_defaults():
    metrics = json.load(open(os.path.join(ROOT, "ml/artifacts/metrics.json"), encoding="utf-8"))
    thr = str(metrics["confidence"]["threshold"])
    env = open(os.path.join(ROOT, ".env.example"), encoding="utf-8").read()
    assert "AIWB_PORT=5050" in env
    app_py = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    assert 'AIWB_PORT", "5050"' in app_py                      # the code default matches the docs
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    info = open(os.path.join(ROOT, "docs", "Project Information - AI Website Builder.md"), encoding="utf-8").read()
    for name, text in (("README.md", readme), ("Project Information", info)):
        assert "5050" in text, name
        assert thr in text, f"{name} does not state the confidence threshold {thr}"
    # real measured numbers quoted in the README must be the ones in metrics.json
    acc = f"{metrics['test']['site_type']['accuracy'] * 100:.1f}%"
    assert acc in readme, f"README should quote the measured test accuracy {acc}"
    ev = f"{metrics['eval']['site_type']['accuracy'] * 100:.1f}%"
    assert ev in readme, f"README should quote the measured eval accuracy {ev}"


def test_main_documents_exist_and_cite_the_base_paper():
    for rel in ("README.md", "docs/Project Information - AI Website Builder.md", "docs/Requirements Traceability.md"):
        assert os.path.isfile(os.path.join(ROOT, rel)), rel
    for rel in ("README.md", "docs/Project Information - AI Website Builder.md"):
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        assert "IJCRTBH02018" in text and "not provided in the source" in text
        assert "doi.org" not in text.lower()


def test_required_layout_and_scripts_exist():
    for rel in ("app/__init__.py", "site_templates/base.css", "content/blog.json", "ml/train.py", "ml/evaluate.py",
                "tests", "docs/screenshots", "docs/test-fixtures", "docs/test-evidence", "docs/Confluence",
                "docs/Demo", "docs/Documentation", "docs/base paper", "start.sh", "start.bat", "train.sh",
                "train.bat", "requirements.txt", ".env.example", ".gitignore", "app.py"):
        assert os.path.exists(os.path.join(ROOT, rel)), rel
    reqs = open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8").read().splitlines()
    assert all("==" in line for line in reqs if line.strip() and not line.startswith("#"))
    ignore = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
    for item in (".venv/", "__pycache__/", ".pytest_cache/", ".env", "*.pyc", "*.zip", "sqlite3"):
        assert item in ignore
