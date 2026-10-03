import os
import re

import pytest

from app.renderer import TEMPLATE_DIR
from app.theme import FONTS, PALETTES, choose_theme


def hex_to_lum(h):
    h = h.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((hex_to_lum(a), hex_to_lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def palette_vars(name):
    with open(os.path.join(TEMPLATE_DIR, "themes", name + ".css"), encoding="utf-8") as f:
        return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", f.read()))


def test_at_least_four_theme_files():
    assert len(PALETTES) >= 4
    for name in PALETTES:
        assert os.path.isfile(os.path.join(TEMPLATE_DIR, "themes", name + ".css"))


@pytest.mark.parametrize("name", list(PALETTES))
def test_palette_contrast_is_accessible(name):
    v = palette_vars(name)
    pairs = {"text/bg": ("text", "bg"), "text/surface": ("text", "surface"), "muted/bg": ("muted", "bg"),
             "muted/surface": ("muted", "surface"), "link(primary)/bg": ("primary", "bg"),
             "link(primary)/surface": ("primary", "surface"), "on-primary/primary": ("on-primary", "primary"),
             "on-primary/primary-2": ("on-primary", "primary-2"), "primary-2/on-primary (hero button)": ("primary-2", "on-primary")}
    for label, (fg, bg) in pairs.items():
        assert contrast(v[fg], v[bg]) >= 4.5, f"{name}: {label} contrast {contrast(v[fg], v[bg]):.2f}"


def test_fonts_are_system_stacks_only():
    for name in FONTS:
        css = open(os.path.join(TEMPLATE_DIR, "fonts", name + ".css"), encoding="utf-8").read()
        assert "@font-face" not in css and "@import" not in css and "url(" not in css


def test_choose_theme_rules():
    assert choose_theme({"colors": ["green"], "tones": []}, "blog")["palette"] == "forest"
    assert choose_theme({"colors": [], "tones": ["dark"]}, "blog")["palette"] == "midnight"
    assert choose_theme({"colors": ["orange"], "tones": ["dark"]}, "blog")["palette"] == "sunset"   # colour wins
    assert choose_theme({"colors": [], "tones": ["elegant"]}, "blog")["font"] == "serif"
    d = choose_theme({"colors": [], "tones": []}, "restaurant")
    assert d == {"palette": "sunset", "font": "editorial"}
