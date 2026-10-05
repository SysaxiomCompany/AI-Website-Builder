import csv
import json
import os
import re
import shutil

import pytest

from app import create_app
from ml.predictor import (ARTIFACT_DIR, MANDATORY_SECTIONS, REQUIRED_FILES, SECTIONS, SITE_TYPES, ArtifactError,
                          ModelBundle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "ml", "data")


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- artifacts
def test_artifacts_exist_and_have_the_required_formats(models):
    for f in REQUIRED_FILES:
        assert os.path.isfile(os.path.join(ARTIFACT_DIR, f)), f
    assert hasattr(models.site_pipe, "predict_proba") and hasattr(models.site_pipe, "classes_")
    assert set(models.sec) >= {"pipeline", "labels", "modeled_labels", "constant_labels", "thresholds"}
    assert set(models.classes) == set(SITE_TYPES)


def test_missing_artifacts_fail_loudly_with_instructions(tmp_path):
    with pytest.raises(ArtifactError) as exc:
        ModelBundle.load(str(tmp_path))
    msg = str(exc.value)
    assert "train.sh" in msg and "train.bat" in msg and "site_type.joblib" in msg and "never falls back" in msg
    with pytest.raises(ArtifactError):
        create_app({"ARTIFACT_DIR": str(tmp_path), "DATABASE": str(tmp_path / "d.sqlite3")})


def test_one_missing_file_is_named(tmp_path):
    for f in REQUIRED_FILES:
        shutil.copy(os.path.join(ARTIFACT_DIR, f), tmp_path / f)
    os.remove(tmp_path / "sections.joblib")
    with pytest.raises(ArtifactError, match="sections.joblib"):
        ModelBundle.load(str(tmp_path))


def test_corrupt_artifact_is_a_clear_error(tmp_path):
    for f in REQUIRED_FILES:
        shutil.copy(os.path.join(ARTIFACT_DIR, f), tmp_path / f)
    (tmp_path / "site_type.joblib").write_bytes(b"garbage")
    with pytest.raises(ArtifactError, match="Could not read"):
        ModelBundle.load(str(tmp_path))


def test_metrics_json_has_every_spec_metric():
    m = json.load(open(os.path.join(ARTIFACT_DIR, "metrics.json"), encoding="utf-8"))
    assert m["stage"] == "evaluated"
    st = m["test"]["site_type"]
    assert {"accuracy", "macro_f1", "confusion_matrix", "per_class"} <= set(st)
    sc = m["test"]["sections"]
    assert {"micro_f1", "macro_f1", "per_section", "exact_set_match"} <= set(sc)
    for s in SECTIONS:
        assert {"precision", "recall"} <= set(sc["per_section"][s])
    assert m["site_type"]["cv"]["k"] == 5 and len(m["site_type"]["cv"]["folds"]) == 5
    assert m["sections"]["cv"]["k"] == 5 and len(m["sections"]["cv"]["folds"]) == 5
    assert m["seed"] == 42 and 0 < m["confidence"]["threshold"] < 1
    assert set(m["sections"]["thresholds"]) == set(SECTIONS)
    assert m["generation_time"]["mean_ms"] > 0 and m["generation_time"]["p95_ms"] >= m["generation_time"]["median_ms"]


def test_model_card_records_thresholds_and_honest_caveats():
    card = open(os.path.join(ARTIFACT_DIR, "model_card.md"), encoding="utf-8").read()
    m = json.load(open(os.path.join(ARTIFACT_DIR, "metrics.json"), encoding="utf-8"))
    assert "optimistic" in card and "team-authored" in card.lower()
    assert str(m["confidence"]["threshold"]) in card
    for s in SECTIONS:
        if s not in MANDATORY_SECTIONS:
            assert f"| {s} | {m['sections']['thresholds'][s]:.2f} |" in card


# ---------------------------------------------------------------- predictions
def test_obvious_prompts_are_classified_confidently(models):
    cases = {"a website for my pizzeria with a menu and gallery": "restaurant",
             "portfolio for a freelance photographer with a photo gallery": "portfolio",
             "a site for our coding bootcamp with course listings": "education",
             "my travel blog with latest posts": "blog",
             "an animal shelter website with volunteer stories": "nonprofit",
             "website for our plumbing company with services": "small_business"}
    for text, expected in cases.items():
        a = models.analyse(text)
        assert a["site_type"] == expected and not a["low_confidence"], (text, a["site_type"], a["confidence"])


def test_section_predictor_follows_explicit_requests(models):
    a = models.analyse("a bakery website with a gallery, pricing and reviews")
    assert {"gallery", "pricing", "testimonials"} <= set(a["predicted_sections"])
    b = models.analyse("a bakery website with only a contact form")
    assert "pricing" not in b["predicted_sections"]


def test_out_of_distribution_inputs_are_flagged(models):
    probes = ["asdf qwerty", "what is the capital of France", "hi", "a", "12345 67890", "lorem ipsum dolor sit amet",
              "ich brauche eine webseite fuer mein restaurant", "我想要一个网站",
              "write me a poem about autumn", "SELECT * FROM users;"]
    for p in probes:
        assert models.analyse(p)["low_confidence"], p


def test_check_cannot_catch_fluent_on_topic_nonsense_and_that_is_documented(models):
    """Documented limitation: relevant vocabulary passes even when the request is not a website request."""
    a = models.analyse("what is the best bakery with a menu and a gallery in France")
    assert not a["low_confidence"]            # known false negative
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read().lower()
    assert "cannot catch" in readme or "can't catch" in readme


# ---------------------------------------------------------------- data files
def test_prompts_csv_meets_the_spec():
    rows = read("prompts.csv")
    assert len(rows) >= 500 and set(rows[0]) == {"text", "site_type", "sections"}
    assert len({r["site_type"] for r in rows}) >= 5 and set(r["site_type"] for r in rows) <= set(SITE_TYPES)
    assert len({len(r["text"].split()) for r in rows}) > 15                       # varied lengths
    for r in rows:
        secs = r["sections"].split("|")
        assert set(secs) <= set(SECTIONS) and set(MANDATORY_SECTIONS) <= set(secs)
    assert len({r["text"].lower() for r in rows}) == len(rows)


def test_split_files_are_a_partition_of_prompts_csv():
    full = {r["text"] for r in read("prompts.csv")}
    parts = [{r["text"] for r in read(f"prompts_{s}.csv")} for s in ("train", "val", "test")]
    assert sum(len(p) for p in parts) == len(full) and set().union(*parts) == full
    assert not (parts[0] & parts[1]) and not (parts[0] & parts[2]) and not (parts[1] & parts[2])
    assert len(parts[0]) > len(parts[1]) and len(parts[0]) > len(parts[2])


def test_eval_prompts_are_held_out():
    ev = read("eval_prompts.csv")
    assert len(ev) >= 80 and set(ev[0]) == {"text", "site_type", "sections"}
    train_like = {r["text"].lower() for r in read("prompts.csv")}
    assert not ({r["text"].lower() for r in ev} & train_like)
    assert len({r["site_type"] for r in ev}) >= 5
    for r in ev:
        assert set(MANDATORY_SECTIONS) <= set(r["sections"].split("|"))


def test_labels_follow_the_documented_rules():
    """Re-derive the key label rule on explicit examples: base set + requested - negated; 'only' drops the base."""
    rows = {r["text"]: r["sections"].split("|") for r in read("prompts.csv")}
    for text, secs in rows.items():
        t = text.lower()
        if "pricing table" in t and "only" not in t and "just" not in t and "no pricing" not in t:
            assert "pricing" in secs, text
    assert any("gallery" not in s for s in rows.values()) and any("gallery" in s for s in rows.values())


def test_eval_set_uses_different_vocabulary_than_training():
    import sys
    sys.path.insert(0, DATA)
    import build_dataset as bd
    train_nouns = {n for v in bd.NOUNS["train"].values() for n in v}
    eval_nouns = {n for v in bd.NOUNS["eval"].values() for n in v}
    assert not (train_nouns & eval_nouns)
    assert not (set(bd.FRAMES["train"]) & set(bd.FRAMES["eval"]))
    assert len(bd.MANUAL_EVAL) >= 15


def test_ood_probe_file_exists():
    assert len(read("ood_probe.csv")) >= 20


def test_uses_the_team_training_tool():
    src = open(os.path.join(ROOT, "ml", "train.py"), encoding="utf-8").read()
    assert "train_text_model" in src and "train_multilabel_text_model" in src and "ML_TRAINING_APP" in src
    assert "random_state=SEED" in src and "StratifiedKFold(5" in src
