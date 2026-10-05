import os
import re
from html.parser import HTMLParser

import pytest

from app.assembler import ORDER, assemble, content_bank
from app.renderer import (TEMPLATE_DIR, build_css, check_output, fixed_script, render_files, render_preview)
from app.sitemodel import ModelError, validate_model
from ml.predictor import MANDATORY_SECTIONS, SECTIONS, SITE_TYPES


def req(site_type, sections, **slots):
    base = {"name": "", "tagline": "", "email": "", "phone": "", "location": "", "colors": [], "tones": []}
    base.update(slots)
    return {"site_type": site_type, "sections": sections, "slots": base}


def section_ids(html):
    return re.findall(r'<(?:section|header|footer)[^>]*\sid="([a-z]+)"', html)


def test_at_least_five_site_types_with_content_banks():
    assert len(SITE_TYPES) >= 5
    for t in SITE_TYPES:
        bank = content_bank(t)
        for sec in SECTIONS:
            if sec != "navbar":
                assert sec in bank, (t, sec)


@pytest.mark.parametrize("site_type", SITE_TYPES)
def test_every_site_type_renders_with_every_section(site_type):
    model = assemble(req(site_type, SECTIONS, name="Test Co", email="a@b.co", phone="+1 555 123 4567",
                         location="Austin"))
    files = render_files(model)
    assert check_output(files) == []
    html = files["index.html"]
    assert '<meta name="viewport"' in html
    assert "@media" in files["style.css"]
    ids = section_ids(html)
    for sec in SECTIONS:
        assert sec in ids, f"{site_type}: {sec} missing from {ids}"


@pytest.mark.parametrize("site_type", SITE_TYPES)
@pytest.mark.parametrize("section", [s for s in SECTIONS if s not in MANDATORY_SECTIONS])
def test_each_section_renders_on_its_own(site_type, section):
    model = assemble(req(site_type, [section]))
    ids = section_ids(render_files(model)["index.html"])
    assert section in ids and set(MANDATORY_SECTIONS) <= set(ids)


def test_navbar_hero_footer_always_present_even_when_nothing_predicted():
    model = assemble(req("blog", []))
    assert [s["type"] for s in model["sections"]] == ["navbar", "hero", "footer"]
    ids = section_ids(render_files(model)["index.html"])
    assert ids == ["navbar", "hero", "footer"]


def test_no_external_urls_and_valid_html_for_all_types():
    for t in SITE_TYPES:
        files = render_files(assemble(req(t, SECTIONS)))
        for name, text in files.items():
            assert not re.search(r"https?://|(?<![:\w])//[a-z]", text, re.I), (t, name)
        assert check_output(files) == []


def test_hidden_sections_are_absent_and_nav_links_follow():
    model = assemble(req("restaurant", SECTIONS))
    for s in model["sections"]:
        if s["type"] in ("gallery", "pricing"):
            s["visible"] = False
    html = render_files(model)["index.html"]
    ids = section_ids(html)
    assert "gallery" not in ids and "pricing" not in ids
    assert 'href="#gallery"' not in html and 'href="#pricing"' not in html


def test_mandatory_sections_cannot_be_hidden():
    model = assemble(req("blog", SECTIONS))
    for s in model["sections"]:
        s["visible"] = False
    cleaned = validate_model(model)
    vis = {s["type"]: s["visible"] for s in cleaned["sections"]}
    assert vis["navbar"] and vis["hero"] and vis["footer"]
    assert not vis["about"]


def test_reordering_is_respected_and_navbar_footer_stay_at_ends():
    model = assemble(req("restaurant", SECTIONS))
    secs = model["sections"]
    names = [s["type"] for s in secs]
    i, j = names.index("faq"), names.index("about")
    secs[i], secs[j] = secs[j], secs[i]
    expected = [s["type"] for s in secs]
    ids = section_ids(render_files(model)["index.html"])
    assert ids == expected
    # a hostile order still keeps navbar first and footer last
    secs.reverse()
    ids = section_ids(render_files(model)["index.html"])
    assert ids[0] == "navbar" and ids[-1] == "footer"


def test_default_order_per_site_type_is_used():
    for t in SITE_TYPES:
        m = assemble(req(t, SECTIONS))
        assert [s["type"] for s in m["sections"]] == ORDER[t]


def test_slots_fill_content_and_defaults_apply():
    m = assemble(req("restaurant", ["contact"], name="Sweet Crumbs", location="Austin"))
    html = render_files(m)["index.html"]
    assert "Welcome to Sweet Crumbs" in html and "Austin" in html
    m2 = assemble(req("restaurant", ["contact"]))
    assert "{location}" not in render_files(m2)["index.html"] and "{name}" not in render_files(m2)["index.html"]
    assert m2["slots"]["name"] == content_bank("restaurant")["default_name"]


def test_theme_files_are_applied_in_output_css():
    m = assemble(req("blog", [], colors=["purple"], tones=["elegant"]))
    css = build_css(m["theme"])
    assert m["theme"] == {"palette": "berry", "font": "serif"}
    assert "#9d1f63" in css and "Georgia" in css


def test_script_is_the_fixed_template_and_contact_form_is_static():
    files = render_files(assemble(req("blog", SECTIONS)))
    with open(os.path.join(TEMPLATE_DIR, "script.js"), encoding="utf-8") as f:
        assert files["script.js"] == f.read() == fixed_script()
    assert 'action="mailto:' in files["index.html"] and "<label for=\"contact-name\"" in files["index.html"]


def test_no_img_tags_and_decorative_art_is_labelled():
    html = render_files(assemble(req("portfolio", SECTIONS)))["index.html"]
    assert "<img" not in html
    assert 'role="img" aria-label=' in html


def test_preview_and_export_share_the_same_markup():
    m = assemble(req("education", SECTIONS, name="Bright Minds"))
    export = render_files(m)
    preview = render_preview(m)

    class Body(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts, self.skip = [], 0

        def handle_starttag(self, tag, attrs):
            if tag in ("style", "script"):
                self.skip += 1

        def handle_endtag(self, tag):
            if tag in ("style", "script"):
                self.skip -= 1

        def handle_data(self, data):
            if not self.skip and data.strip():
                self.parts.append(data.strip())

    def text(html):
        p = Body()
        p.feed(html)
        return p.parts

    assert text(preview) == text(export["index.html"])
    assert export["style.css"] in preview and export["script.js"] in preview


def test_templates_never_use_safe_filter():
    for folder, _, files in os.walk(TEMPLATE_DIR):
        for f in files:
            if f.endswith(".j2"):
                src = open(os.path.join(folder, f), encoding="utf-8").read()
                assert "|safe" not in src.replace(" ", "") and "autoescape false" not in src, f


def test_validate_model_rejects_bad_input():
    good = assemble(req("blog", SECTIONS))
    for mutate in (lambda m: m.update(site_type="spaceship"),
                   lambda m: m["theme"].update(palette="neon"),
                   lambda m: m["theme"].update(font="comic"),
                   lambda m: m.update(sections=[]),
                   lambda m: m["sections"].append(dict(m["sections"][0])),
                   lambda m: m["sections"][2].update(type="bogus"),
                   lambda m: m.update(sections=[s for s in m["sections"] if s["type"] != "footer"])):
        bad = validate_model(good)
        mutate(bad)
        with pytest.raises(ModelError):
            validate_model(bad)
    with pytest.raises(ModelError):
        validate_model("not a dict")


def test_validate_model_caps_and_drops_unknown_keys():
    m = assemble(req("blog", SECTIONS))
    m["sections"][1]["content"]["headline"] = "x" * 5000
    m["sections"][1]["content"]["evil"] = "<script>"
    cleaned = validate_model(m)
    hero = cleaned["sections"][1]["content"]
    assert len(hero["headline"]) == 2000 and "evil" not in hero
