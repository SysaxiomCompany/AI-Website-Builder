import re
from html.parser import HTMLParser

import pytest

from app.assembler import assemble
from app.renderer import fixed_script, render_files, render_preview
from ml.predictor import SECTIONS

XSS = [
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "' onmouseover='alert(1)",
    "</title><script>alert(2)</script>",
    "javascript:alert(3)",
    "<svg onload=alert(4)>",
]


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts, self.event_attrs, self.tags, self.js_urls = [], [], [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        for k, v in attrs:
            if k.lower().startswith("on"):
                self.event_attrs.append((tag, k))
            if k in ("href", "src", "action") and v and v.strip().lower().startswith("javascript:"):
                self.js_urls.append(v)
        if tag == "script":
            self.scripts.append(attrs)


def scan(html):
    s = Scan()
    s.feed(html)
    return s


def hostile_model(payload):
    m = assemble({"site_type": "restaurant", "sections": SECTIONS,
                  "slots": {"name": payload, "tagline": payload, "email": "", "phone": "", "location": payload,
                            "colors": [], "tones": []}}, prompt=payload)
    for s in m["sections"]:
        c = s["content"]
        for k, v in list(c.items()):
            if isinstance(v, str):
                c[k] = payload
            elif isinstance(v, list):
                c[k] = [payload if isinstance(x, str) else {kk: (payload if isinstance(vv, str) and kk != "icon" else vv)
                                                            for kk, vv in x.items()} for x in v]
    return m


@pytest.mark.parametrize("payload", XSS)
def test_user_text_is_escaped_everywhere(payload):
    model = hostile_model(payload)
    for html in (render_files(model)["index.html"], render_preview(model)):
        sc = scan(html)
        assert sc.event_attrs == []
        assert sc.js_urls == []
        assert len(sc.scripts) == 1                      # only the fixed script (inline in preview, src in export)
        assert "<img" not in html and "<svg onload" not in html
        if "<" in payload or '"' in payload or "'" in payload:
            assert payload not in html                   # markup characters never appear raw
            assert "&lt;" in html or "&#34;" in html or "&#39;" in html


def test_prompt_with_script_tag_through_the_api_is_escaped(client):
    prompt = 'A bakery called <script>alert(1)</script> with a menu, email me "><img src=x onerror=alert(1)>'
    r = client.post("/api/generate", json={"prompt": prompt})
    assert r.status_code == 201
    pid = r.get_json()["project"]["id"]
    for url in (f"/preview/{pid}",):
        html = client.get(url).data.decode()
        sc = scan(html)
        assert sc.event_attrs == [] and len(sc.scripts) == 1
        assert "<script>alert(1)" not in html
    assert b"<script>alert" not in client.get(f"/preview/{pid}").data


def test_edit_with_html_attributes_is_escaped_through_save_and_export(client, project):
    pid = project["id"]
    model = project["model"]
    model["sections"][1]["content"]["headline"] = '"><script>alert(1)</script><b onclick="x">'
    model["sections"][2]["content"]["title"] = "<img src=x onerror=alert(1)>"
    r = client.put(f"/api/projects/{pid}", json={"name": "<b>bold</b>", "model": model})
    assert r.status_code == 200
    import io
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/projects/{pid}/export").data))
    html = z.read("index.html").decode()
    sc = scan(html)
    assert sc.event_attrs == [] and "<img" not in html and len(sc.scripts) == 1
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert z.read("script.js").decode() == fixed_script()


def test_generated_javascript_is_only_the_fixed_template(client, project):
    html = client.get(f"/preview/{project['id']}").data.decode()
    inline = re.findall(r"<script>\n(.*?)\n</script>", html, re.S)
    assert inline == [fixed_script().rstrip("\n")] or inline == [fixed_script()]


def test_invalid_email_and_phone_cannot_inject(client):
    r = client.post("/api/generate", json={"prompt": "site called X email me at a@b.co\" onfocus=\"alert(1) phone 123"})
    pid = r.get_json()["project"]["id"]
    html = client.get(f"/preview/{pid}").data.decode()
    assert scan(html).event_attrs == []
    model = r.get_json()["project"]["model"]
    model["slots"]["email"] = 'x@y.co" onfocus="alert(1)'
    model["slots"]["phone"] = "javascript:alert(1)"
    resp = client.put(f"/api/projects/{pid}", json={"model": model})
    saved = resp.get_json()["project"]["model"]["slots"]
    assert saved["email"] == "" and saved["phone"] == ""
