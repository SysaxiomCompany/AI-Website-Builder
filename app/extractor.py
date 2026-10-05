"""Requirement Extractor: classifiers (ml/) + slot rules -> requirements."""
from ml.predictor import MANDATORY_SECTIONS, SECTIONS, SITE_TYPES
from .slots import extract_slots

SLOT_KEYS = ("name", "tagline", "email", "phone", "location")


class Extractor:
    def __init__(self, models):
        self.models = models

    def extract(self, text):
        """text: normalised prompt. Returns the requirements dict shown in 'How I understood your request'."""
        a = self.models.analyse(text)
        sections = [s for s in SECTIONS if s in set(a["predicted_sections"]) | set(MANDATORY_SECTIONS)]
        return {
            "site_type": a["site_type"], "confidence": a["confidence"], "type_scores": a["type_scores"],
            "predicted_sections": a["predicted_sections"], "sections": sections,
            "section_scores": a["section_scores"], "slots": extract_slots(text),
            "low_confidence": a["low_confidence"], "low_confidence_reasons": a["low_confidence_reasons"],
            "vocab_coverage": a["vocab_coverage"], "overridden": [],
        }


def apply_overrides(req, overrides):
    """The user may correct the understanding (site type, sections, slots). Returns a new dict."""
    out = dict(req)
    out["slots"] = dict(req["slots"])
    out["overridden"] = []
    if not isinstance(overrides, dict):
        return out
    st = overrides.get("site_type")
    if isinstance(st, str) and st in SITE_TYPES and st != out["site_type"]:
        out["site_type"] = st
        out["overridden"].append("site_type")
    secs = overrides.get("sections")
    if isinstance(secs, list):
        chosen = {s for s in secs if s in SECTIONS} | set(MANDATORY_SECTIONS)
        new = [s for s in SECTIONS if s in chosen]
        if new != out["sections"]:
            out["sections"] = new
            out["overridden"].append("sections")
    slots = overrides.get("slots")
    if isinstance(slots, dict):
        for k in SLOT_KEYS:
            if k in slots and isinstance(slots[k], str) and slots[k].strip() != out["slots"].get(k, ""):
                out["slots"][k] = slots[k].strip()
                out["overridden"].append("slot:" + k)
        for k in ("colors", "tones"):
            if k in slots and isinstance(slots[k], list):
                out["slots"][k] = [str(x) for x in slots[k][:6]]
    return out
