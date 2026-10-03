"""Component Assembler: requirements -> site model (ordered sections filled from the content bank)."""
import copy
import json
import os
import re

from ml.predictor import MANDATORY_SECTIONS, SECTIONS, SITE_TYPES
from .sitemodel import MODEL_VERSION, validate_model
from .theme import choose_theme

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(ROOT, "content")

# Section order per site type (a hand-written layout rule).
ORDER = {
    "portfolio": ["navbar", "hero", "features", "gallery", "about", "testimonials", "pricing", "faq",
                  "contact", "footer"],
    "restaurant": ["navbar", "hero", "about", "features", "gallery", "pricing", "testimonials", "faq",
                   "contact", "footer"],
    "small_business": ["navbar", "hero", "features", "about", "pricing", "testimonials", "gallery", "faq",
                       "contact", "footer"],
    "education": ["navbar", "hero", "about", "features", "pricing", "testimonials", "gallery", "faq",
                  "contact", "footer"],
    "blog": ["navbar", "hero", "features", "about", "gallery", "pricing", "testimonials", "faq", "contact",
             "footer"],
    "nonprofit": ["navbar", "hero", "about", "features", "gallery", "testimonials", "pricing", "faq",
                  "contact", "footer"],
}
_cache = {}


def content_bank(site_type):
    if site_type not in SITE_TYPES:
        raise ValueError(f"unknown site type {site_type!r}")
    if site_type not in _cache:
        with open(os.path.join(CONTENT_DIR, site_type + ".json"), encoding="utf-8") as f:
            _cache[site_type] = json.load(f)
    return copy.deepcopy(_cache[site_type])


def _fill_text(text, slots):
    if "{location}" in text and not slots.get("location"):
        sentences = re.split(r"(?<=[.!?])\s+", text)
        text = " ".join(s for s in sentences if "{location}" not in s)
    return text.replace("{name}", slots["name"]).replace("{location}", slots.get("location", ""))


def _fill(value, slots):
    if isinstance(value, str):
        return _fill_text(value, slots)
    if isinstance(value, list):
        return [_fill(v, slots) for v in value]
    if isinstance(value, dict):
        return {k: _fill(v, slots) for k, v in value.items()}
    return value


def assemble(requirements, prompt=""):
    """requirements: {"site_type", "sections": [...], "slots": {...extracted...}, + info keys}.
    Navbar, hero and footer are always included (documented rule). Returns a validated site model."""
    site_type = requirements["site_type"]
    bank = content_bank(site_type)
    extracted = requirements.get("slots") or {}
    slots = {
        "name": extracted.get("name") or bank["default_name"],
        "tagline": extracted.get("tagline") or bank["default_tagline"],
        "email": extracted.get("email", ""), "phone": extracted.get("phone", ""),
        "location": extracted.get("location", ""),
        "colors": list(extracted.get("colors") or []), "tones": list(extracted.get("tones") or []),
    }
    wanted = set(requirements.get("sections") or []) | set(MANDATORY_SECTIONS)
    wanted &= set(SECTIONS)
    sections = []
    for sec in ORDER[site_type]:
        if sec not in wanted:
            continue
        content = {} if sec == "navbar" else _fill(bank[sec], slots)
        sections.append({"id": sec, "type": sec, "visible": True, "content": content})
    info = {k: requirements[k] for k in ("site_type", "confidence", "predicted_sections", "low_confidence",
                                         "low_confidence_reasons", "overridden") if k in requirements}
    info["extracted_slots"] = extracted
    model = {"version": MODEL_VERSION, "site_type": site_type, "prompt": prompt, "slots": slots,
             "theme": choose_theme(slots, site_type), "nav_labels": bank["nav_labels"],
             "sections": sections, "requirements": info}
    return validate_model(model)


def add_section(model, section_type):
    """Used by the editor API when the user shows a section that is not in the model yet."""
    if any(s["type"] == section_type for s in model["sections"]):
        return model
    bank = content_bank(model["site_type"])
    sec = {"id": section_type, "type": section_type, "visible": True,
           "content": _fill(bank[section_type], model["slots"])}
    order = ORDER[model["site_type"]]
    idx = len(model["sections"]) - 1
    for i, s in enumerate(model["sections"]):
        if order.index(s["type"]) > order.index(section_type):
            idx = i
            break
    model["sections"].insert(idx, sec)
    return model
