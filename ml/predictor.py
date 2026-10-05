"""Runtime model loader: Site-Type Classifier + Section Predictor.

Loads ONLY the files in ``ml/artifacts/`` with plain joblib/scikit-learn (no dependency on
the ML-Training-App folder that trained them) and fails loudly when they are missing.
"""
import json
import os
import re

SITE_TYPES = ["portfolio", "restaurant", "small_business", "education", "blog", "nonprofit"]
SECTIONS = ["navbar", "hero", "about", "features", "gallery", "pricing", "testimonials", "faq",
            "contact", "footer"]
MANDATORY_SECTIONS = ["navbar", "hero", "footer"]
REQUIRED_FILES = ("site_type.joblib", "sections.joblib", "metrics.json", "model_card.md")
ARTIFACT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")

# Hand-written low-confidence rules (not learned). The confidence threshold itself is chosen
# on the validation split by ml/train.py and read from metrics.json.
MIN_WORDS = 2             # fewer words than this -> too short to classify
MIN_VOCAB_COVERAGE = 0.5  # share of words the TF-IDF vocabulary has seen during training


class ArtifactError(RuntimeError):
    """Raised at startup when the trained model files are missing or unreadable."""


def tokens(text):
    return re.findall(r"[a-z]+", text.lower())


class ModelBundle:
    def __init__(self, site_pipe, sec_bundle, metrics, card, artifact_dir):
        self.site_pipe = site_pipe
        self.sec = sec_bundle
        self.metrics = metrics
        self.model_card = card
        self.artifact_dir = artifact_dir
        self.classes = [str(c) for c in site_pipe.classes_]
        self.confidence_threshold = float(metrics["confidence"]["threshold"])
        vec = site_pipe.named_steps["tfidf"]
        words = getattr(vec, "transformer_list", None)
        word_vec = dict(words)["word"] if words else vec
        self.vocab = set(word_vec.vocabulary_)

    @classmethod
    def load(cls, artifact_dir=ARTIFACT_DIR):
        missing = [f for f in REQUIRED_FILES if not os.path.isfile(os.path.join(artifact_dir, f))]
        if missing:
            raise ArtifactError(
                f"Trained model files are missing from {artifact_dir}: {', '.join(missing)}.\n"
                "Create them with  ./train.sh  (macOS/Linux)  or  train.bat  (Windows).  "
                "The app never falls back to another method.")
        import joblib
        try:
            site_pipe = joblib.load(os.path.join(artifact_dir, "site_type.joblib"))
            sec = joblib.load(os.path.join(artifact_dir, "sections.joblib"))
            with open(os.path.join(artifact_dir, "metrics.json"), encoding="utf-8") as f:
                metrics = json.load(f)
            with open(os.path.join(artifact_dir, "model_card.md"), encoding="utf-8") as f:
                card = f.read()
            return cls(site_pipe, sec, metrics, card, artifact_dir)
        except Exception as exc:  # corrupt file, version mismatch, wrong schema
            raise ArtifactError(
                f"Could not read the trained model files in {artifact_dir}: {exc}.\n"
                "Re-create them with ./train.sh (macOS/Linux) or train.bat (Windows).") from exc

    # -------------------------------------------------------------- predictions
    def predict_site_type(self, text):
        proba = self.site_pipe.predict_proba([text])[0]
        order = sorted(range(len(proba)), key=lambda i: -proba[i])
        return {"site_type": self.classes[order[0]], "confidence": float(proba[order[0]]),
                "scores": {self.classes[i]: float(proba[i]) for i in order}}

    def predict_sections(self, text):
        sec = self.sec
        labels = sec["labels"]
        scores = {lab: 0.0 for lab in labels}
        modeled = sec["modeled_labels"]
        if modeled:
            proba = sec["pipeline"].predict_proba([text])[0]
            scores.update({lab: float(p) for lab, p in zip(modeled, proba)})
        for lab, val in sec["constant_labels"].items():
            scores[lab] = 1.0 if val else 0.0
        chosen = [lab for lab in labels if scores[lab] >= sec["thresholds"][lab]]
        return {"sections": [s for s in SECTIONS if s in chosen], "scores": scores,
                "thresholds": dict(sec["thresholds"])}

    def vocab_coverage(self, text):
        toks = [t for t in tokens(text) if len(t) > 1]
        if not toks:
            return 0.0
        return sum(1 for t in toks if t in self.vocab) / len(toks)

    def confidence_check(self, text, confidence):
        """Returns (low_confidence, reasons). A heuristic, not a guarantee (see README)."""
        reasons = []
        words = tokens(text)
        if len(words) < MIN_WORDS:
            reasons.append(f"The description is very short ({len(words)} word"
                           f"{'' if len(words) == 1 else 's'}).")
        cov = self.vocab_coverage(text)
        if cov < MIN_VOCAB_COVERAGE:
            reasons.append(f"Only {round(cov * 100)}% of the words were seen in the training prompts.")
        if confidence < self.confidence_threshold:
            reasons.append(f"The site-type confidence ({confidence:.2f}) is below the threshold "
                           f"({self.confidence_threshold:.2f}).")
        return bool(reasons), reasons

    def analyse(self, text):
        st = self.predict_site_type(text)
        sc = self.predict_sections(text)
        low, reasons = self.confidence_check(text, st["confidence"])
        return {"site_type": st["site_type"], "confidence": st["confidence"], "type_scores": st["scores"],
                "predicted_sections": sc["sections"], "section_scores": sc["scores"],
                "low_confidence": low, "low_confidence_reasons": reasons,
                "vocab_coverage": self.vocab_coverage(text)}
