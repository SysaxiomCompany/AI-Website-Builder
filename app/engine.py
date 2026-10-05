"""AI Engine: Prompt Preprocessor -> Requirement Extractor -> Component Assembler (+ Theme Engine)."""
import time

from .assembler import assemble
from .extractor import Extractor, apply_overrides
from .preprocess import normalize_prompt


class Engine:
    def __init__(self, models):
        self.models = models
        self.extractor = Extractor(models)

    def generate(self, prompt, overrides=None):
        """-> {"model": site model, "requirements": requirements, "timing_ms": float}"""
        t0 = time.perf_counter()
        text = normalize_prompt(prompt)
        req = apply_overrides(self.extractor.extract(text), overrides)
        model = assemble(req, prompt=text)
        return {"model": model, "requirements": req, "timing_ms": (time.perf_counter() - t0) * 1000.0}
