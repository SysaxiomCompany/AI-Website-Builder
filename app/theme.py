"""Theme Engine: maps colour and tone words to a palette and a system-font stack (rule-based)."""
from .slots import COLOR_WORDS

PALETTES = {  # id -> display label and swatch (the real colours live in site_templates/themes/<id>.css)
    "ocean": {"label": "Ocean", "swatch": "#0b5cad"},
    "sunset": {"label": "Sunset", "swatch": "#b4440e"},
    "forest": {"label": "Forest", "swatch": "#1b6b3a"},
    "berry": {"label": "Berry", "swatch": "#9d1f63"},
    "slate": {"label": "Slate", "swatch": "#334155"},
    "midnight": {"label": "Midnight (dark)", "swatch": "#7cb7ff"},
}
FONTS = {
    "sans": "Clean sans-serif",
    "serif": "Classic serif",
    "editorial": "Serif headings, sans text",
    "rounded": "Friendly rounded",
    "mono": "Technical monospace",
}
TONE_PALETTE = {"elegant": "slate", "playful": "sunset", "bold": "sunset", "professional": "ocean",
                "friendly": "forest", "calm": "ocean", "minimal": "slate", "minimalist": "slate",
                "dark": "midnight", "warm": "sunset", "cheerful": "sunset", "luxurious": "berry",
                "cozy": "sunset", "cosy": "sunset", "formal": "ocean", "stylish": "slate"}
TONE_FONT = {"elegant": "serif", "classic": "serif", "formal": "serif", "luxurious": "serif",
             "playful": "rounded", "fun": "rounded", "cheerful": "rounded", "friendly": "rounded",
             "colourful": "rounded", "colorful": "rounded", "cozy": "rounded", "cosy": "rounded",
             "minimal": "sans", "minimalist": "sans", "modern": "sans", "clean": "sans", "simple": "sans",
             "bold": "sans", "professional": "sans", "retro": "mono"}
DEFAULT_PALETTE = {"portfolio": "slate", "restaurant": "sunset", "small_business": "ocean",
                   "education": "berry", "blog": "forest", "nonprofit": "ocean"}
DEFAULT_FONT = {"portfolio": "sans", "restaurant": "editorial", "small_business": "sans",
                "education": "rounded", "blog": "editorial", "nonprofit": "sans"}


def choose_theme(slots, site_type):
    """slots: dict with 'colors' and 'tones'. Colour words win over tone words; defaults per site type."""
    palette = None
    for c in slots.get("colors") or []:
        if c in COLOR_WORDS:
            palette = COLOR_WORDS[c]
            break
    if palette is None:
        for t in slots.get("tones") or []:
            if t in TONE_PALETTE:
                palette = TONE_PALETTE[t]
                break
    font = None
    for t in slots.get("tones") or []:
        if t in TONE_FONT:
            font = TONE_FONT[t]
            break
    return {"palette": palette or DEFAULT_PALETTE.get(site_type, "ocean"),
            "font": font or DEFAULT_FONT.get(site_type, "sans")}
