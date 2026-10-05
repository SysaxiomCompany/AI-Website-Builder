"""The site model: a plain JSON structure (site type, theme, slots, ordered sections with content and
visibility). validate_model() returns a cleaned copy and is the single gate that every model passes
(on generate, on save, on preview and before rendering), so the Renderer only ever sees known keys,
bounded strings and whitelisted values."""
import copy
import re

from ml.predictor import MANDATORY_SECTIONS, SECTIONS, SITE_TYPES
from .slots import EMAIL_RE
from .theme import FONTS, PALETTES

MODEL_VERSION = 1
ICONS = ["star", "heart", "bolt", "shield", "clock", "check", "book", "camera"]
STR_CAP = 2000
LIST_CAP = 24
EDITABLE_ORDER_SECTIONS = [s for s in SECTIONS if s not in ("navbar", "footer")]
CTA_TARGETS = [s for s in SECTIONS if s not in ("navbar", "hero", "footer")]

S = str
SHAPES = {
    "navbar": {},
    "hero": {"headline": S, "subheadline": S, "cta_label": S, "cta_target": S},
    "about": {"title": S, "paragraphs": [S]},
    "features": {"title": S, "intro": S, "items": [{"title": S, "text": S, "icon": S}]},
    "gallery": {"title": S, "items": [S]},
    "pricing": {"title": S, "intro": S, "plans": [{"name": S, "price": S, "period": S, "features": [S],
                                                    "highlight": bool}]},
    "testimonials": {"title": S, "items": [{"quote": S, "author": S, "role": S}]},
    "faq": {"title": S, "items": [{"q": S, "a": S}]},
    "contact": {"title": S, "intro": S},
    "footer": {"text": S},
}


class ModelError(ValueError):
    """The site model is malformed (message is safe to show to the user)."""


def _conform(value, shape):
    if shape is bool:
        return bool(value) if isinstance(value, (bool, int)) else False
    if shape is str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            raise ModelError("A text field contained a list or object.")
        return str(value)[:STR_CAP]
    if isinstance(shape, list):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ModelError("A list field was not a list.")
        return [_conform(v, shape[0]) for v in value[:LIST_CAP]]
    if isinstance(shape, dict):
        if value is None:
            value = {}
        if not isinstance(value, dict):
            raise ModelError("A content block was not an object.")
        return {k: _conform(value.get(k), sub) for k, sub in shape.items()}
    raise ModelError("Unknown content shape.")


def clean_slots(slots):
    slots = slots if isinstance(slots, dict) else {}

    def text(key, cap):
        v = slots.get(key)
        return re.sub(r"\s+", " ", str(v)).strip()[:cap] if isinstance(v, (str, int, float)) else ""

    email = text("email", 120)
    phone = text("phone", 30)
    return {
        "name": text("name", 80) or "My Website",
        "tagline": text("tagline", 140),
        "email": email if EMAIL_RE.fullmatch(email) else "",
        "phone": phone if re.fullmatch(r"[0-9+()\-. ]{7,30}", phone) else "",
        "location": text("location", 80),
        "colors": [str(c)[:20] for c in (slots.get("colors") or [])[:6] if isinstance(c, str)],
        "tones": [str(t)[:20] for t in (slots.get("tones") or [])[:6] if isinstance(t, str)],
    }


def validate_model(model):
    """Return a cleaned deep copy of ``model`` or raise ModelError."""
    if not isinstance(model, dict):
        raise ModelError("The site model must be a JSON object.")
    site_type = model.get("site_type")
    if site_type not in SITE_TYPES:
        raise ModelError(f"Unknown site type. Expected one of: {', '.join(SITE_TYPES)}.")
    theme = model.get("theme") if isinstance(model.get("theme"), dict) else {}
    if theme.get("palette") not in PALETTES:
        raise ModelError(f"Unknown palette. Expected one of: {', '.join(PALETTES)}.")
    if theme.get("font") not in FONTS:
        raise ModelError(f"Unknown font. Expected one of: {', '.join(FONTS)}.")
    raw_sections = model.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ModelError("The site model needs a list of sections.")
    if len(raw_sections) > len(SECTIONS):
        raise ModelError("The site model has too many sections.")
    seen, sections = set(), []
    for raw in raw_sections:
        if not isinstance(raw, dict) or raw.get("type") not in SECTIONS:
            raise ModelError("A section has an unknown type.")
        stype = raw["type"]
        if stype in seen:
            raise ModelError(f"Section '{stype}' appears twice.")
        seen.add(stype)
        content = _conform(raw.get("content"), SHAPES[stype])
        if stype == "features":
            for item in content["items"]:
                if item["icon"] not in ICONS:
                    item["icon"] = "star"
        if stype == "hero" and content["cta_target"] not in CTA_TARGETS:
            content["cta_target"] = "features"
        visible = True if stype in MANDATORY_SECTIONS else bool(raw.get("visible", True))
        sections.append({"id": stype, "type": stype, "visible": visible, "content": content})
    for need in MANDATORY_SECTIONS:
        if need not in seen:
            raise ModelError(f"The section '{need}' is required in every site.")
    # navbar is always first and footer always last
    sections.sort(key=lambda s: (s["type"] != "navbar", s["type"] == "footer"))
    nav = model.get("nav_labels") if isinstance(model.get("nav_labels"), dict) else {}
    nav_labels = {s: (str(nav.get(s) or s.title())[:24]) for s in CTA_TARGETS}
    reqs = model.get("requirements") if isinstance(model.get("requirements"), dict) else {}
    return {
        "version": MODEL_VERSION,
        "site_type": site_type,
        "prompt": str(model.get("prompt") or "")[:1000],
        "slots": clean_slots(model.get("slots")),
        "theme": {"palette": theme["palette"], "font": theme["font"]},
        "nav_labels": nav_labels,
        "sections": sections,
        "requirements": copy.deepcopy(reqs) if len(str(reqs)) < 20000 else {},
    }


def summarize_edit(old, new):
    """Short human-readable description of what changed between two validated models (for the edits log)."""
    changes = []
    if old["slots"]["name"] != new["slots"]["name"]:
        changes.append("site name")
    if old["theme"] != new["theme"]:
        changes.append("theme/font")
    old_order = [s["type"] for s in old["sections"]]
    new_order = [s["type"] for s in new["sections"]]
    if old_order != new_order:
        changes.append("section order/set")
    old_by = {s["type"]: s for s in old["sections"]}
    for s in new["sections"]:
        o = old_by.get(s["type"])
        if o is None:
            changes.append(f"added {s['type']}")
            continue
        if o["visible"] != s["visible"]:
            changes.append(("showed " if s["visible"] else "hid ") + s["type"])
        if o["content"] != s["content"]:
            changes.append(f"edited {s['type']} text")
    if old["slots"] != new["slots"] and "site name" not in changes:
        changes.append("slots")
    return "; ".join(changes) if changes else "saved (no changes)"
