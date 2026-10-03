"""Prompt Preprocessor: raw prompt -> normalised text."""
import re
import unicodedata

MAX_PROMPT_CHARS = 1000
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def normalize_prompt(raw):
    """NFKC-normalise, drop control characters, turn newlines/tabs into spaces, collapse spaces."""
    text = unicodedata.normalize("NFKC", str(raw if raw is not None else ""))
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = _CONTROL.sub("", text)
    return re.sub(r"\s+", " ", text).strip()
