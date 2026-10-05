"""Renderer / Exporter: site model + theme -> index.html, style.css, script.js (and a ZIP).

The Renderer is a pure function of the validated site model. All user text is escaped by Jinja2
autoescaping; the templates never use the 'safe' filter. The JavaScript is always the fixed file
site_templates/script.js. The same code path produces the live preview and the export."""
import io
import os
import re
import zipfile
from html.parser import HTMLParser

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from .sitemodel import validate_model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(ROOT, "site_templates")
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True, undefined=StrictUndefined,
                   trim_blocks=False, lstrip_blocks=False)
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class RenderError(RuntimeError):
    """The rendered output failed the validity checks (this is a bug, never user error)."""


def _read(*parts):
    with open(os.path.join(TEMPLATE_DIR, *parts), encoding="utf-8") as f:
        return f.read()


def fixed_script():
    return _read("script.js")


def build_css(theme):
    return "\n".join([_read("base.css"), _read("themes", theme["palette"] + ".css"),
                      _read("fonts", theme["font"] + ".css")])


def _nav_links(model):
    return [{"id": s["type"], "label": model["nav_labels"].get(s["type"], s["type"].title())}
            for s in model["sections"] if s["visible"] and s["type"] not in ("navbar", "hero", "footer")]


def _render_section(model, sec, nav):
    visible_ids = [s["type"] for s in model["sections"] if s["visible"]]
    ctx = {"slots": model["slots"], "c": sec["content"], "nav": nav, "theme": model["theme"],
           "contact_href": "#contact" if "contact" in visible_ids else "#top",
           "phone_href": re.sub(r"[^0-9+]", "", model["slots"]["phone"]), "cta_href": None}
    if sec["type"] == "hero":
        target = sec["content"]["cta_target"]
        if target in visible_ids:
            ctx["cta_href"] = "#" + target
        elif nav:
            ctx["cta_href"] = "#" + nav[0]["id"]
    return Markup(_env.get_template(f"sections/{sec['type']}.html.j2").render(**ctx))


def render_page(model, inline):
    m = validate_model(model)
    nav = _nav_links(m)
    parts = {"navbar": "", "footer": ""}
    body = []
    for sec in m["sections"]:
        if not sec["visible"]:
            continue
        html = _render_section(m, sec, nav)
        if sec["type"] in parts:
            parts[sec["type"]] = html
        else:
            body.append(html)
    slots = m["slots"]
    desc = (slots["name"] + (" - " + slots["tagline"] if slots["tagline"] else ""))[:160]
    return _env.get_template("base.html.j2").render(
        slots=slots, theme=m["theme"], description=desc, inline=inline,
        css=Markup(build_css(m["theme"])), js=Markup(fixed_script()),
        header_html=parts["navbar"], main_html=Markup("\n".join(body)), footer_html=parts["footer"])


class _Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.viewport = [], [], set(), False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        if "id" in a:
            if a["id"] in self.ids:
                self.errors.append(f"duplicate id {a['id']!r}")
            self.ids.add(a["id"])
        if tag not in _VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected </{tag}> (open: {self.stack[-1] if self.stack else 'none'})")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()


_EXTERNAL = re.compile(r"https?:|(?<![:\w])//[A-Za-z0-9]|@import|url\(\s*['\"]?\s*(?:https?:|//)", re.I)


def check_output(files):
    """Validity checks on the rendered files. Returns a list of problems (empty = valid)."""
    problems = []
    html = files["index.html"]
    chk = _Checker()
    chk.feed(html)
    chk.close()
    problems += chk.errors
    if chk.stack:
        problems.append(f"unclosed tags: {chk.stack}")
    if not html.lstrip().lower().startswith("<!doctype html>"):
        problems.append("missing doctype")
    if not chk.viewport:
        problems.append("missing viewport meta tag")
    if "@media" not in files["style.css"]:
        problems.append("no @media rules")
    for name, text in files.items():
        if _EXTERNAL.search(text):
            problems.append(f"external URL or import in {name}")
    for nid in re.findall(r'href="#([^"]+)"', html):
        if nid != "top" and f'id="{nid}"' not in html:
            problems.append(f"link to missing section #{nid}")
    return problems


def render_files(model):
    """-> {"index.html", "style.css", "script.js"} (strings). Raises ModelError / RenderError."""
    m = validate_model(model)
    files = {"index.html": render_page(m, inline=False), "style.css": build_css(m["theme"]),
             "script.js": fixed_script()}
    problems = check_output(files)
    if problems:
        raise RenderError("; ".join(problems))
    return files


def render_preview(model):
    """One self-contained HTML document (CSS and JS inlined) for the iframe preview."""
    m = validate_model(model)
    return render_page(m, inline=True)


def build_zip(model):
    files = render_files(model)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("index.html", "style.css", "script.js"):
            info = zipfile.ZipInfo(name, date_time=(2025, 1, 1, 0, 0, 0))   # reproducible archive
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, files[name])
    return buf.getvalue()
