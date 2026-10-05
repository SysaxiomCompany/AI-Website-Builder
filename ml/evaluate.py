"""Evaluator: held-out metrics, low-confidence check, generation time -> artifacts + a plot.

  * held-out TEST split (ml/data/prompts_test.csv, never used for fitting or selection):
      site type accuracy, macro F1, confusion matrix, per-class P/R/F1;
      sections micro/macro F1, per-section precision/recall, exact-set-match rate
  * eval_prompts.csv (a different authoring style, never used for training or any threshold)
  * low-confidence check: flagged share on both sets and on ml/data/ood_probe.csv
  * generation time: mean / median / p95 of the full pipeline (prompt -> site model -> rendered files)
    over the eval prompts, measured on this machine

Writes ml/artifacts/metrics.json (extends the training-stage file), model_card.md,
eval_results.json, and the plot docs/test-evidence/ml-evaluation.png.
"""
import json
import os
import platform
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "data"))

from ml.predictor import (MANDATORY_SECTIONS, MIN_VOCAB_COVERAGE, MIN_WORDS, SECTIONS,  # noqa: E402
                          SITE_TYPES, ModelBundle)
from app.engine import Engine  # noqa: E402
from app.preprocess import normalize_prompt  # noqa: E402
from app.renderer import render_files  # noqa: E402
from build_dataset import MANUAL_EVAL  # noqa: E402

ART = os.path.join(HERE, "artifacts")
DATA = os.path.join(HERE, "data")
PLOT = os.path.join(ROOT, "docs", "test-evidence", "ml-evaluation.png")


def indicator(cells):
    Y = np.zeros((len(cells), len(SECTIONS)), dtype=int)
    for i, c in enumerate(cells):
        for s in str(c).split("|"):
            Y[i, SECTIONS.index(s.strip())] = 1
    return Y


def analyse_all(models, texts):
    out = []
    for t in texts:
        a = models.analyse(normalize_prompt(t))
        secs = set(a["predicted_sections"]) | set(MANDATORY_SECTIONS)   # the app's rule
        out.append({"type": a["site_type"], "conf": a["confidence"], "secs": secs,
                    "low": a["low_confidence"], "reasons": a["low_confidence_reasons"]})
    return out


def score(models, df):
    """Metrics of the classifiers on a labelled dataframe (text, site_type, sections)."""
    from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                                 precision_recall_fscore_support)
    texts = df["text"].astype(str).tolist()
    pred = analyse_all(models, texts)
    yt = df["site_type"].astype(str).tolist()
    yp = [p["type"] for p in pred]
    p, r, f, sup = precision_recall_fscore_support(yt, yp, labels=SITE_TYPES, zero_division=0)
    Yt = indicator(df["sections"])
    Yp = np.array([[int(s in p_["secs"]) for s in SECTIONS] for p_ in pred])
    modeled = [i for i, s in enumerate(SECTIONS) if s not in MANDATORY_SECTIONS]
    sp, sr, sf, ss = precision_recall_fscore_support(Yt, Yp, zero_division=0)
    wrong = np.array([a != b for a, b in zip(yt, yp)])
    low = np.array([p_["low"] for p_ in pred])
    return {
        "n": len(df),
        "site_type": {
            "accuracy": float(accuracy_score(yt, yp)),
            "macro_f1": float(f1_score(yt, yp, labels=SITE_TYPES, average="macro", zero_division=0)),
            "labels": SITE_TYPES,
            "confusion_matrix": confusion_matrix(yt, yp, labels=SITE_TYPES).tolist(),
            "per_class": {c: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]),
                              "support": int(sup[i])} for i, c in enumerate(SITE_TYPES)},
        },
        "sections": {
            "scored_labels": [SECTIONS[i] for i in modeled],
            "micro_f1": float(f1_score(Yt[:, modeled], Yp[:, modeled], average="micro", zero_division=0)),
            "macro_f1": float(f1_score(Yt[:, modeled], Yp[:, modeled], average="macro", zero_division=0)),
            "micro_f1_all10": float(f1_score(Yt, Yp, average="micro", zero_division=0)),
            "macro_f1_all10": float(f1_score(Yt, Yp, average="macro", zero_division=0)),
            "exact_set_match": float((Yt == Yp).all(axis=1).mean()),
            "per_section": {SECTIONS[i]: {"precision": float(sp[i]), "recall": float(sr[i]),
                                          "f1": float(sf[i]), "support": int(ss[i])} for i in range(len(SECTIONS))},
        },
        "low_confidence": {
            "flagged": int(low.sum()), "flagged_rate": float(low.mean()),
            "misclassified": int(wrong.sum()),
            "flagged_among_misclassified": int((low & wrong).sum()),
            "flagged_among_correct": int((low & ~wrong).sum()),
        },
        "_pred": pred,
    }


def generation_time(models, df):
    engine = Engine(models)
    texts = df["text"].astype(str).tolist()
    for t in texts[:5]:                       # warm-up (imports, caches); not counted
        render_files(engine.generate(t)["model"])
    ms, ms_engine = [], []
    for t in texts:
        t0 = time.perf_counter()
        res = engine.generate(t)
        t1 = time.perf_counter()
        render_files(res["model"])
        t2 = time.perf_counter()
        ms.append((t2 - t0) * 1000)
        ms_engine.append((t1 - t0) * 1000)
    a = np.array(ms)
    return {"n": len(ms), "mean_ms": float(a.mean()), "median_ms": float(np.median(a)),
            "p95_ms": float(np.percentile(a, 95)), "max_ms": float(a.max()),
            "engine_only_mean_ms": float(np.mean(ms_engine)),
            "scope": "prompt preprocessing + requirement extraction (both classifiers + slot rules) + "
                     "assembly + theme + rendering and validity check of index.html/style.css/script.js, "
                     "one pass over each eval prompt after 5 warm-up runs",
            "machine": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}",
            "all_ms": [round(x, 2) for x in ms]}


def ood_check(models):
    df = pd.read_csv(os.path.join(DATA, "ood_probe.csv"))
    rows, by_kind = [], {}
    for text, kind in zip(df["text"], df["kind"]):
        a = models.analyse(normalize_prompt(text))
        rows.append({"text": text, "kind": kind, "site_type": a["site_type"],
                     "confidence": round(a["confidence"], 3), "flagged": a["low_confidence"]})
        k = by_kind.setdefault(kind, {"n": 0, "flagged": 0})
        k["n"] += 1
        k["flagged"] += int(a["low_confidence"])
    flagged = sum(r["flagged"] for r in rows)
    return {"n": len(rows), "flagged": flagged, "flagged_rate": flagged / len(rows), "by_kind": by_kind,
            "not_flagged": [r for r in rows if not r["flagged"]]}


def plot(test, ev, gen, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    cm = np.array(test["site_type"]["confusion_matrix"])
    a = ax[0][0]
    a.imshow(cm, cmap="Blues")
    a.set_xticks(range(len(SITE_TYPES)), SITE_TYPES, rotation=35, ha="right", fontsize=8)
    a.set_yticks(range(len(SITE_TYPES)), SITE_TYPES, fontsize=8)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            a.text(j, i, cm[i, j], ha="center", va="center", fontsize=8,
                   color="white" if cm[i, j] > cm.max() / 2 else "black")
    a.set_title(f"Site type - confusion matrix, held-out test (n={test['n']})")
    a.set_xlabel("predicted")
    a.set_ylabel("true")
    a = ax[0][1]
    secs = [s for s in SECTIONS if s not in MANDATORY_SECTIONS]
    x = np.arange(len(secs))
    a.bar(x - 0.2, [test["sections"]["per_section"][s]["f1"] for s in secs], 0.4, label="test split")
    a.bar(x + 0.2, [ev["sections"]["per_section"][s]["f1"] for s in secs], 0.4, label="eval_prompts.csv")
    a.set_xticks(x, secs, rotation=30, ha="right", fontsize=8)
    a.set_ylim(0, 1.05)
    a.set_title("Per-section F1")
    a.legend(fontsize=8)
    a = ax[1][0]
    names = ["type acc.", "type macro F1", "sections micro F1", "sections macro F1", "exact set match"]
    g = lambda d: [d["site_type"]["accuracy"], d["site_type"]["macro_f1"], d["sections"]["micro_f1"],
                   d["sections"]["macro_f1"], d["sections"]["exact_set_match"]]
    x = np.arange(len(names))
    b1 = a.bar(x - 0.2, g(test), 0.4, label="test split")
    b2 = a.bar(x + 0.2, g(ev), 0.4, label="eval_prompts.csv")
    for bars in (b1, b2):
        for r in bars:
            a.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.01, f"{r.get_height():.2f}",
                   ha="center", fontsize=8)
    a.set_xticks(x, names, rotation=20, ha="right", fontsize=8)
    a.set_ylim(0, 1.1)
    a.set_title("Summary (team-authored prompts - optimistic)")
    a.legend(fontsize=8)
    a = ax[1][1]
    a.hist(gen["all_ms"], bins=20, color="#4a7bd0")
    a.axvline(gen["mean_ms"], color="k", ls="--", label=f"mean {gen['mean_ms']:.1f} ms")
    a.axvline(gen["p95_ms"], color="r", ls=":", label=f"p95 {gen['p95_ms']:.1f} ms")
    a.set_title(f"Generation time over {gen['n']} eval prompts")
    a.set_xlabel("ms (prompt to rendered files)")
    a.legend(fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def pct(x):
    return f"{100 * x:.1f}%"


def model_card(m, gen, ood):
    st, sc, cf = m["site_type"], m["sections"], m["confidence"]
    t, e = m["test"], m["eval"]
    L = ["# Model card - AI Website Builder classifiers", "",
         f"Generated by `ml/evaluate.py` at {m['generated_at_utc']} from the real training run (seed {m['seed']}). "
         "Every number below was measured; nothing is copied from the base paper.", "",
         "## What the models do", "",
         "- **Site-type classifier**: TF-IDF (word 1-2-grams + character 2-5-grams) + logistic regression -> one of "
         + ", ".join(f"`{x}`" for x in SITE_TYPES) + " with a probability.",
         "- **Section predictor**: the same TF-IDF features + one-vs-rest logistic regression -> which of "
         + ", ".join(f"`{x}`" for x in SECTIONS) + " the site needs, with one decision threshold per section "
         "chosen on the validation split.",
         "- Rule, not learned: `navbar`, `hero` and `footer` are always included (documented rule), as are slot "
         "extraction, theme choice, section order and content-bank selection. Because those three labels are "
         "positive in every training prompt they are stored as constants; the section metrics below score the "
         f"{len(t['sections']['scored_labels'])} learnable sections.", "",
         "## Data (read this first)", "",
         f"- {m['data']['train']} / {m['data']['val']} / {m['data']['test']} prompts in train / validation / test "
         "(stratified 70/15/15 of `ml/data/prompts.csv`), plus the separate `eval_prompts.csv` "
         f"({e['n']} prompts).",
         "- The prompts are **team-authored and templated**, not collected from real users: hand-written vocabulary "
         "combined with hand-written sentence frames, filler sentences and random typos by `ml/data/build_dataset.py`. "
         "Labels are derived by explicit rules from the content written into each prompt, never by a model.",
         "- `eval_prompts.csv` uses different frames, different noun phrases for every site type, different "
         "section wording and names, plus 20 hand-labelled harder prompts. It was never used for training, model "
         "selection or any threshold.",
         "- Because the same authors wrote both sets, **the accuracy below is optimistic for real users' prompts**: "
         "it measures how well the models learn this authors' style and vocabulary, not general language "
         "understanding.", "",
         "## Training setup", "",
         f"- Tool: team's ML-Training-App `text_pipeline.py` (`train_text_model(feature_mode='tfidf')` for the site "
         "type; the generic `train_multilabel_text_model` added for the sections).",
         f"- Site type head chosen on the validation split: `{st['selection']['name']}` (validation macro-F1 "
         f"{st['selection']['val_macro_f1']:.4f}); not refit on train+val so the confidence threshold stays honest.",
         f"- Sections head chosen on the validation split: `{sc['selection']['name']}`; thresholds chosen on the "
         "validation split.",
         f"- Fixed seed {m['seed']}; libraries: " + ", ".join(f"{k} {v}" for k, v in m["libraries"].items()) + ".", "",
         "## Five-fold cross-validation (train split only)", "",
         f"- Site type: accuracy {st['cv']['accuracy_mean']:.4f} +/- {st['cv']['accuracy_std']:.4f}, macro-F1 "
         f"{st['cv']['macro_f1_mean']:.4f} +/- {st['cv']['macro_f1_std']:.4f} (n={st['cv']['n']}).",
         f"- Sections (stored thresholds applied): micro-F1 {sc['cv']['micro_f1_mean']:.4f} +/- "
         f"{sc['cv']['micro_f1_std']:.4f}, macro-F1 {sc['cv']['macro_f1_mean']:.4f} +/- "
         f"{sc['cv']['macro_f1_std']:.4f}, exact-set match {sc['cv']['exact_match_mean']:.4f} (7 learnable sections).", "",
         "## Held-out test split", "",
         f"- Site type: accuracy {t['site_type']['accuracy']:.4f}, macro-F1 {t['site_type']['macro_f1']:.4f} "
         f"(n={t['n']}).", "",
         "Confusion matrix (rows true, columns predicted; order: " + ", ".join(SITE_TYPES) + "):", "", "```"]
    L += [" ".join(f"{v:3d}" for v in row) for row in t["site_type"]["confusion_matrix"]]
    L += ["```", "",
          f"- Sections: micro-F1 {t['sections']['micro_f1']:.4f}, macro-F1 {t['sections']['macro_f1']:.4f} "
          f"(7 learnable; all 10 labels: micro {t['sections']['micro_f1_all10']:.4f}), exact-set-match rate "
          f"{t['sections']['exact_set_match']:.4f}.", "",
          "| section | threshold | precision | recall | F1 | support |", "|---|---|---|---|---|---|"]
    for s in SECTIONS:
        if s in MANDATORY_SECTIONS:
            continue
        r = t["sections"]["per_section"][s]
        L.append(f"| {s} | {sc['thresholds'][s]:.2f} | {r['precision']:.3f} | {r['recall']:.3f} | "
                 f"{r['f1']:.3f} | {r['support']} |")
    L += ["", "## Held-out `eval_prompts.csv` (different style; includes harder prompts)", "",
          f"- Site type: accuracy {e['site_type']['accuracy']:.4f}, macro-F1 {e['site_type']['macro_f1']:.4f} (n={e['n']}).",
          f"- Sections: micro-F1 {e['sections']['micro_f1']:.4f}, macro-F1 {e['sections']['macro_f1']:.4f}, "
          f"exact-set-match {e['sections']['exact_set_match']:.4f}.",
          f"- The 20 hand-labelled harder prompts alone: site-type accuracy {e['hard_subset']['site_type_accuracy']:.4f}, "
          f"sections micro-F1 {e['hard_subset']['sections_micro_f1']:.4f} (n={e['hard_subset']['n']}).", "",
          "## Low-confidence check", "",
          f"- Rule: {cf['rule']}.",
          f"- Confidence threshold: **{cf['threshold']}** ({cf['threshold_choice']}).",
          f"- Share of prompts flagged: test {pct(t['low_confidence']['flagged_rate'])}, eval "
          f"{pct(e['low_confidence']['flagged_rate'])}; of the {e['low_confidence']['misclassified']} eval prompts whose "
          f"site type was wrong, {e['low_confidence']['flagged_among_misclassified']} were flagged.",
          f"- On {ood['n']} hand-written unrelated / nonsense / very short / non-English probes "
          f"(`ml/data/ood_probe.csv`): {ood['flagged']} flagged ({pct(ood['flagged_rate'])}). Not flagged: "
          + ("; ".join(f"\"{r['text']}\" ({r['kind']}, -> {r['site_type']} {r['confidence']})" for r in ood["not_flagged"])
             or "none") + ".",
          "- What the check cannot catch: fluent English that mentions a supported topic (for example a question about "
          "bakeries) will pass as a confident site; adversarial text, partly relevant prompts and requests that use "
          "familiar words in an unrelated way are not detected. It is a heuristic warning, not a guarantee.", "",
          "## Generation time", "",
          f"- Mean {gen['mean_ms']:.1f} ms, median {gen['median_ms']:.1f} ms, 95th percentile {gen['p95_ms']:.1f} ms, "
          f"max {gen['max_ms']:.1f} ms over {gen['n']} eval prompts ({gen['scope']}). Machine: {gen['machine']}.", "",
          "## Limitations", "",
          "- Trained on team-written prompts: measured accuracy is not general accuracy.",
          "- Prompts in other languages, very long prompts, and requests outside the six site types are handled poorly "
          "(the app warns when confidence is low).",
          "- Only 6 site types and 10 sections; the system selects and fills templates, it does not invent layouts.",
          "- The learned parts are only the two classifiers; everything else is rule-based or template assembly.", ""]
    return "\n".join(L)


def main():
    models = ModelBundle.load(ART)
    with open(os.path.join(ART, "metrics.json"), encoding="utf-8") as f:
        m = json.load(f)
    test_df = pd.read_csv(os.path.join(DATA, "prompts_test.csv"))
    eval_df = pd.read_csv(os.path.join(DATA, "eval_prompts.csv"))
    train_texts = set(pd.read_csv(os.path.join(DATA, "prompts.csv"))["text"].str.lower())
    assert not (train_texts & set(eval_df["text"].str.lower())), "eval prompts overlap training prompts"

    test = score(models, test_df)
    ev = score(models, eval_df)
    hard_texts = {t.lower() for t, _, _ in MANUAL_EVAL}
    mask = eval_df["text"].str.lower().isin(hard_texts).values
    hard = score(models, eval_df[mask])
    ev["hard_subset"] = {"n": int(mask.sum()), "site_type_accuracy": hard["site_type"]["accuracy"],
                         "sections_micro_f1": hard["sections"]["micro_f1"],
                         "sections_exact_set_match": hard["sections"]["exact_set_match"]}
    ood = ood_check(models)
    gen = generation_time(models, eval_df)

    items = []
    for (_, row), p, ms in zip(eval_df.iterrows(), ev["_pred"], gen["all_ms"]):
        items.append({"text": row["text"], "true_type": row["site_type"], "pred_type": p["type"],
                      "confidence": round(p["conf"], 3), "true_sections": row["sections"].split("|"),
                      "pred_sections": [s for s in SECTIONS if s in p["secs"]],
                      "low_confidence": p["low"], "gen_ms": ms})
    for d in (test, ev):
        d.pop("_pred")
    m["stage"] = "evaluated"
    m["generated_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    m["test"] = test
    m["eval"] = ev
    m["confidence"]["test_flagged_rate"] = test["low_confidence"]["flagged_rate"]
    m["confidence"]["eval_flagged_rate"] = ev["low_confidence"]["flagged_rate"]
    m["confidence"]["ood_probe"] = ood
    m["generation_time"] = {k: v for k, v in gen.items() if k != "all_ms"}
    m["provenance"] = ("Team-authored, templated prompts (ml/data/build_dataset.py); labels derived by rules from the "
                       "written content; accuracy is optimistic for real users' prompts.")
    flat = {"site_type": m["site_type"], "sections": m["sections"], "confidence": m["confidence"],
            "test": test, "eval": ev, "data": m["data"], "seed": m["seed"], "libraries": m["libraries"],
            "generated_at_utc": m["generated_at_utc"]}
    with open(os.path.join(ART, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2)
    with open(os.path.join(ART, "model_card.md"), "w", encoding="utf-8") as f:
        f.write(model_card(flat, gen, ood))
    results = {"generated_at_utc": m["generated_at_utc"], "n": ev["n"], "source": "ml/data/eval_prompts.csv",
               "site_type": ev["site_type"], "sections": ev["sections"], "hard_subset": ev["hard_subset"],
               "low_confidence": ev["low_confidence"], "ood_probe": {k: v for k, v in ood.items()},
               "generation_time": m["generation_time"], "provenance": m["provenance"], "items": items}
    with open(os.path.join(ART, "eval_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    plot(test, ev, gen, PLOT)
    print(f"test: type acc {test['site_type']['accuracy']:.4f} macroF1 {test['site_type']['macro_f1']:.4f} | "
          f"sections micro {test['sections']['micro_f1']:.4f} macro {test['sections']['macro_f1']:.4f} "
          f"exact {test['sections']['exact_set_match']:.4f}")
    print(f"eval: type acc {ev['site_type']['accuracy']:.4f} macroF1 {ev['site_type']['macro_f1']:.4f} | "
          f"sections micro {ev['sections']['micro_f1']:.4f} macro {ev['sections']['macro_f1']:.4f} "
          f"exact {ev['sections']['exact_set_match']:.4f} | hard acc {ev['hard_subset']['site_type_accuracy']:.4f}")
    print(f"low-confidence: test {test['low_confidence']['flagged_rate']:.3f} eval {ev['low_confidence']['flagged_rate']:.3f} "
          f"ood {ood['flagged']}/{ood['n']}")
    print(f"generation ms: mean {gen['mean_ms']:.2f} median {gen['median_ms']:.2f} p95 {gen['p95_ms']:.2f}")
    print("Wrote metrics.json, model_card.md, eval_results.json and", PLOT)


if __name__ == "__main__":
    main()
