"""Slot Extractor: rule-based (regular expressions and word lists) - name, tagline, email, phone,
location, colour words and tone words. Nothing here is learned."""
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\w@])(\+?\(?\d[\d\s().-]{5,}\d)(?![\w@])")
_QUOTED = r"[\"“]([^\"”]{2,80})[\"”]"
TAGLINE_QUOTED_RE = re.compile(r"(?:tag\s?line|slogan|motto|strapline)\s*(?:is|:|of|says|saying|reads|-)?\s*" + _QUOTED, re.I)
TAGLINE_PLAIN_RE = re.compile(r"(?:tag\s?line|slogan|motto)\s*(?:is|:|of)\s+([^.;\"“”]{3,80})", re.I)
NAME_CUE_RE = re.compile(r"\b(?:called|named|name\s+is|name's|titled|branded)\b[\s:,-]*", re.I)
QUOTED_RE = re.compile(_QUOTED)
LOCATION_CUE_RE = re.compile(r"\b(?:based\s+in|based\s+at|located\s+in|located\s+at|located\s+on|situated\s+in|"
                             r"found\s+in|near|from)\s+", re.I)
BARE_IN_RE = re.compile(r"\b(?:in|at)\s+([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,2})")

STOP = {"with", "and", "that", "for", "which", "who", "in", "on", "at", "it", "its", "i", "we", "a", "an",
        "the", "to", "of", "my", "our", "but", "so", "please", "include", "includes", "add", "want", "need",
        "should", "shows", "show", "has", "have", "use", "using", "is", "are", "no", "only", "just",
        "skip", "without", "plus", "can", "will", "when", "where", "because", "based", "located", "from",
        "near", "i'd", "we're", "it's", "looking", "make", "build", "create", "using"}
KNOWN_PLACES = {"austin", "seattle", "denver", "boston", "portland", "chicago", "miami", "toronto", "london",
                "dublin", "leeds", "madison", "tucson", "halifax", "bristol", "raleigh", "perth", "cork",
                "paris", "berlin", "madrid", "rome", "sydney", "melbourne", "mumbai", "delhi", "bangalore",
                "chennai", "singapore", "tokyo", "new york", "los angeles", "san francisco", "dallas",
                "houston", "atlanta", "vancouver", "manchester", "glasgow", "edinburgh", "amsterdam"}

# colour word -> palette id (first match in the prompt wins); words are matched whole-word.
COLOR_WORDS = {
    "blue": "ocean", "navy": "ocean", "teal": "ocean", "cyan": "ocean", "aqua": "ocean", "turquoise": "ocean",
    "orange": "sunset", "red": "sunset", "brown": "sunset", "yellow": "sunset", "gold": "sunset",
    "golden": "sunset", "amber": "sunset", "coral": "sunset", "terracotta": "sunset", "warm": "sunset",
    "green": "forest", "olive": "forest", "mint": "forest", "sage": "forest", "emerald": "forest",
    "purple": "berry", "pink": "berry", "violet": "berry", "magenta": "berry", "lavender": "berry",
    "rose": "berry", "berry": "berry",
    "black": "slate", "grey": "slate", "gray": "slate", "silver": "slate", "charcoal": "slate",
    "slate": "slate", "white": "slate", "monochrome": "slate",
    "midnight": "midnight",
}
TONE_WORDS = ["elegant", "playful", "minimal", "minimalist", "bold", "professional", "friendly", "modern",
              "clean", "calm", "dark", "cheerful", "luxurious", "simple", "cozy", "cosy", "creative", "formal",
              "fun", "serious", "retro", "classic", "warm", "stylish", "colourful", "colorful"]


def _words(text):
    return re.findall(r"[A-Za-z']+", text.lower())


def _clean_name(s):
    s = re.sub(r"\s+", " ", s).strip(" \t.,;:!?-–—\"'“”")
    return s[:60]


def _capture_phrase(text, max_tokens):
    """Take up to max_tokens tokens from the start of text for a name/place: stops at punctuation
    or a stop word; accepts '&' / 'and' / 'of' joining capitalised words (e.g. 'Cedar & Co')."""
    tokens = text.split()
    out = []
    i = 0
    while i < len(tokens) and len(out) < max_tokens:
        raw = tokens[i]
        word = raw.rstrip(".,;:!?)\"”")
        low = word.lower()
        if not word:
            break
        joiner = low in ("&", "and", "of") and out and i + 1 < len(tokens) and tokens[i + 1][:1].isupper() \
            and out[-1][:1].isupper()
        if low in STOP and not joiner:
            break
        out.append(word)
        if raw != word and raw[len(word):][:1] in ".,;:!?":
            break
        i += 1
    if out and not any(w[:1].isupper() for w in out):
        out = [w.capitalize() if w not in ("&",) else w for w in out]
    return " ".join(out)


def extract_name(text):
    q = None
    for m in QUOTED_RE.finditer(text):
        before = text[max(0, m.start() - 40):m.start()].lower()
        if re.search(r"(tag\s?line|slogan|motto|saying|says|reads)\W*(is|:)?\W*$", before):
            continue
        q = m.group(1)
        break
    for m in NAME_CUE_RE.finditer(text):
        rest = text[m.end():]
        mq = re.match(_QUOTED, rest)
        if mq:
            return _clean_name(mq.group(1))
        phrase = _capture_phrase(rest, 5)
        if phrase:
            return _clean_name(phrase)
    if q:
        return _clean_name(q)
    return ""


def extract_tagline(text):
    m = TAGLINE_QUOTED_RE.search(text) or TAGLINE_PLAIN_RE.search(text)
    return _clean_name(m.group(1))[:100] if m else ""


def extract_email(text):
    m = EMAIL_RE.search(text)
    return m.group(0) if m else ""


def extract_phone(text):
    stripped = EMAIL_RE.sub(" ", text)
    for m in PHONE_RE.finditer(stripped):
        digits = re.sub(r"\D", "", m.group(1))
        if 7 <= len(digits) <= 15:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def extract_location(text):
    for m in LOCATION_CUE_RE.finditer(text):
        phrase = _capture_phrase(text[m.end():], 3)
        if phrase:
            return phrase[:60].title() if phrase.islower() else phrase[:60]
    for m in BARE_IN_RE.finditer(text):
        cand = m.group(1)
        if cand.lower().split(",")[0] in KNOWN_PLACES or cand.lower() in KNOWN_PLACES:
            return cand
    low = text.lower()
    for place in KNOWN_PLACES:
        if re.search(r"\b(?:in|at)\s+" + re.escape(place) + r"\b", low):
            return place.title()
    return ""


def extract_colors(text):
    found = []
    for w in _words(text):
        if w in COLOR_WORDS and w not in found:
            found.append(w)
    return found


def extract_tones(text):
    words = _words(text)
    return [t for t in TONE_WORDS if t in words]


def extract_slots(text):
    """text -> {"name","tagline","email","phone","location","colors","tones"} (empty values when absent)."""
    return {"name": extract_name(text), "tagline": extract_tagline(text), "email": extract_email(text),
            "phone": extract_phone(text), "location": extract_location(text),
            "colors": extract_colors(text), "tones": extract_tones(text)}
