"""Train the two classifiers with the team's generic ML-Training-App pipeline.

  site type  : ML-Training-App/text_pipeline.train_text_model(feature_mode="tfidf", ...)
  sections   : ML-Training-App/text_pipeline.train_multilabel_text_model(...)   (one-vs-rest,
               per-label thresholds chosen on the validation split)

Fixed seed (42), five-fold cross-validation on the TRAIN split only, validation split used for
model selection / thresholds, test split and eval_prompts.csv untouched here (see evaluate.py).

The ML-Training-App folder is found via the ML_TRAINING_APP environment variable (default:
the sibling folder ../ML-Training-App next to this repository). It is needed only for
training; the Flask app loads ml/artifacts/ with plain scikit-learn + joblib.

Writes to ml/artifacts/: site_type.joblib, sections.joblib, metrics.json (training-stage part: CV,
selection, thresholds), site_type_training_metrics.json, site_type_training_card.md and a stub
model_card.md; evaluate.py then extends metrics.json, rewrites model_card.md and writes
eval_results.json.
"""
import json
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from ml.predictor import (MIN_VOCAB_COVERAGE, MIN_WORDS, SECTIONS, SITE_TYPES,  # noqa: E402
                          MANDATORY_SECTIONS, tokens)

SEED = 42
DATA = os.path.join(HERE, "data")
ART = os.path.join(HERE, "artifacts")
WORK = os.path.join(HERE, "work")      # tool's own bundle + intermediate files (gitignored)
CONF_PERCENTILE = 5                    # threshold = 5th percentile of validation max-probability


def load_text_pipeline():
    tool = os.environ.get("ML_TRAINING_APP") or os.path.normpath(os.path.join(ROOT, "..", "ML-Training-App"))
    if not os.path.isfile(os.path.join(tool, "text_pipeline.py")):
        raise SystemExit(f"text_pipeline.py not found in {tool!r}. Set the ML_TRAINING_APP environment "
                         "variable to the folder of the ML-Training-App.")
    sys.path.insert(0, tool)
    import text_pipeline
    if not hasattr(text_pipeline, "train_multilabel_text_model"):
        raise SystemExit("This copy of text_pipeline.py has no train_multilabel_text_model; "
                         "update ML-Training-App.")
    return text_pipeline, tool


def main():
    tp, tool = load_text_pipeline()
    from sklearn.base import clone
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import KFold, StratifiedKFold

    os.makedirs(ART, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    tr, va, te = (os.path.join(DATA, f"prompts_{s}.csv") for s in ("train", "val", "test"))
    t0 = time.time()

    # ---------------- site type (the tool's single-label TF-IDF path) ----------------
    heads = [(f"logreg(C={c},balanced)", {"family": "logistic_regression", "C": c, "class_weight": "balanced"},
              (lambda c=c: LogisticRegression(C=c, max_iter=5000, class_weight="balanced", random_state=SEED)))
             for c in (1.0, 3.0, 10.0, 30.0)]            # probability-capable heads only (confidence)
    out_st = os.path.join(WORK, "site_type")
    res = tp.train_text_model(
        tr, va, te, out_st, text_columns=["text"], classification_target="site_type",
        class_order=SITE_TYPES, feature_mode="tfidf", classifier_candidates=heads,
        refit_on_train_val=False, seed=SEED, artifact_name="site_type_bundle.joblib",
        plain_classifier_name="site_type.joblib", write_report=True,
        report_title="Site-type classifier (tool report)",
        report_notes="Produced by ML-Training-App/text_pipeline.train_text_model; the metrics below are "
                     "on the team-authored test split (templated prompts, optimistic).",
        report_limitations=["Team-authored templated prompts; accuracy is not general accuracy."])
    site_pipe = res["bundle"]["classifier"]
    shutil.copy(res["plain_classifier_path"], os.path.join(ART, "site_type.joblib"))
    shutil.copy(res["report_paths"]["metrics_json"], os.path.join(ART, "site_type_training_metrics.json"))
    shutil.copy(res["report_paths"]["model_card"], os.path.join(ART, "site_type_training_card.md"))

    # ---------------- sections (generic multi-label capability added to the tool) ----------------
    ml = tp.train_multilabel_text_model(tr, va, te, os.path.join(WORK, "sections"), ["text"], "sections",
                                        label_sep="|", labels=SECTIONS, seed=SEED,
                                        artifact_name="sections_bundle.joblib")
    sec = ml["bundle"]
    import joblib
    joblib.dump(sec, os.path.join(ART, "sections.joblib"))

    # ---------------- five-fold cross-validation on the TRAIN split ----------------
    dtr = pd.read_csv(tr)
    texts = dtr["text"].astype(str).tolist()
    ytype = dtr["site_type"].astype(str).values
    folds = []
    for k, (a, b) in enumerate(StratifiedKFold(5, shuffle=True, random_state=SEED).split(texts, ytype)):
        m = clone(site_pipe).fit([texts[i] for i in a], ytype[a])
        p = m.predict([texts[i] for i in b])
        folds.append({"fold": k + 1, "accuracy": float(accuracy_score(ytype[b], p)),
                      "macro_f1": float(f1_score(ytype[b], p, labels=SITE_TYPES, average="macro",
                                                 zero_division=0))})
    cv_type = {"k": 5, "split": "train", "n": len(texts), "folds": folds,
               "accuracy_mean": float(np.mean([f["accuracy"] for f in folds])),
               "accuracy_std": float(np.std([f["accuracy"] for f in folds])),
               "macro_f1_mean": float(np.mean([f["macro_f1"] for f in folds])),
               "macro_f1_std": float(np.std([f["macro_f1"] for f in folds]))}

    Y = tp.multilabel_indicator(dtr["sections"].tolist(), SECTIONS, "|")
    mc = [SECTIONS.index(s) for s in sec["modeled_labels"]]
    thr = np.array([sec["thresholds"][s] for s in sec["modeled_labels"]])
    sfolds = []
    for k, (a, b) in enumerate(KFold(5, shuffle=True, random_state=SEED).split(texts)):
        m = clone(sec["pipeline"]).fit([texts[i] for i in a], Y[a][:, mc])
        pred = (m.predict_proba([texts[i] for i in b]) >= thr).astype(int)
        sfolds.append({"fold": k + 1,
                       "micro_f1": float(f1_score(Y[b][:, mc], pred, average="micro", zero_division=0)),
                       "macro_f1": float(f1_score(Y[b][:, mc], pred, average="macro", zero_division=0)),
                       "exact_match": float((Y[b][:, mc] == pred).all(axis=1).mean())})
    cv_sec = {"k": 5, "split": "train", "n": len(texts), "labels_scored": sec["modeled_labels"],
              "thresholds_used": "thresholds chosen on the validation split",
              "folds": sfolds}
    for key in ("micro_f1", "macro_f1", "exact_match"):
        cv_sec[key + "_mean"] = float(np.mean([f[key] for f in sfolds]))
        cv_sec[key + "_std"] = float(np.std([f[key] for f in sfolds]))

    # ---------------- low-confidence threshold from the VALIDATION split ----------------
    dva = pd.read_csv(va)
    vproba = site_pipe.predict_proba(dva["text"].astype(str).tolist()).max(axis=1)
    conf_thr = float(np.percentile(vproba, CONF_PERCENTILE))
    vocab = set(dict(site_pipe.named_steps["tfidf"].transformer_list)["word"].vocabulary_)
    cov = [sum(t in vocab for t in tokens(t_) if len(t) > 1) / max(1, len([x for x in tokens(t_) if len(x) > 1]))
           for t_ in dva["text"].astype(str)]
    confidence = {
        "threshold": round(conf_thr, 4),
        "rule": f"low confidence if max site-type probability < threshold, or fewer than {MIN_WORDS} "
                f"words, or < {int(MIN_VOCAB_COVERAGE * 100)}% of words in the training vocabulary",
        "threshold_choice": f"{CONF_PERCENTILE}th percentile of the max predicted probability over the "
                            "validation split (so about 5% of in-distribution validation prompts are "
                            "flagged by design)",
        "min_words": MIN_WORDS, "min_vocab_coverage": MIN_VOCAB_COVERAGE,
        "validation_flagged_by_threshold": float(np.mean(vproba < conf_thr)),
        "validation_flagged_by_coverage": float(np.mean(np.array(cov) < MIN_VOCAB_COVERAGE)),
        "validation_n": int(len(dva)),
    }

    import importlib
    libs = {n: importlib.import_module(n).__version__ for n in ("sklearn", "numpy", "pandas", "joblib", "scipy")}
    report = {
        "trained_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": SEED, "train_seconds": round(time.time() - t0, 1), "libraries": libs,
        "tool": {"folder": tool, "single_label": "train_text_model(feature_mode='tfidf')",
                 "multi_label": "train_multilabel_text_model"},
        "data": {"train": len(dtr), "val": len(dva), "test": len(pd.read_csv(te)),
                 "site_types": SITE_TYPES, "sections": SECTIONS, "mandatory_sections": MANDATORY_SECTIONS},
        "site_type": {"selection": res["bundle"]["selection"]["clf"], "cv": cv_type,
                      "refit_on_train_val": False},
        "sections": {"selection": sec["selection"], "labels": sec["labels"],
                     "modeled_labels": sec["modeled_labels"], "constant_labels": sec["constant_labels"],
                     "thresholds": sec["thresholds"], "cv": cv_sec},
        "confidence": confidence,
    }
    report["stage"] = "trained; evaluate.py has not been run yet"
    with open(os.path.join(ART, "metrics.json"), "w", encoding="utf-8") as f:     # evaluate.py extends it
        json.dump(report, f, indent=2)
    with open(os.path.join(ART, "model_card.md"), "w", encoding="utf-8") as f:    # evaluate.py rewrites it
        f.write("# Model card (training stage only)\n\nRun ml/evaluate.py to complete this card.\n")
    print(f"site type CV accuracy {cv_type['accuracy_mean']:.4f} +/- {cv_type['accuracy_std']:.4f}; "
          f"sections CV micro-F1 {cv_sec['micro_f1_mean']:.4f} +/- {cv_sec['micro_f1_std']:.4f}; "
          f"confidence threshold {confidence['threshold']}")
    print("Wrote", ART)


if __name__ == "__main__":
    main()
