"""Independent QA recompute: score ml/data/eval_prompts.csv with the shipped artifacts; metrics computed by hand."""
import csv, sys
sys.path.insert(0, ".")
from ml.predictor import ModelBundle
mb = ModelBundle.load()
rows = list(csv.DictReader(open("ml/data/eval_prompts.csv", encoding="utf-8")))
from app.preprocess import normalize_prompt
ok = 0; tp = fp = fn = 0
for r in rows:
    a = mb.analyse(normalize_prompt(r["text"]))
    ok += a["site_type"] == r["site_type"]
    gold = set(r["sections"].split("|")) - {"navbar", "hero", "footer"}
    pred = set(a["predicted_sections"]) - {"navbar", "hero", "footer"}
    tp += len(gold & pred); fp += len(pred - gold); fn += len(gold - pred)
p = tp/(tp+fp); rc = tp/(tp+fn)
print(f"n={len(rows)} site_type_accuracy={ok/len(rows):.4f} ({ok}/{len(rows)})")
print(f"sections(7 learnable) micro precision={p:.4f} recall={rc:.4f} F1={2*p*rc/(p+rc):.4f}  tp={tp} fp={fp} fn={fn}")
