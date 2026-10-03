# AI Website Builder

A local Python (Flask) web app that turns a plain-English description of a website into a complete, responsive, multi-section site (HTML, CSS and a little JavaScript). Two small machine-learning classifiers trained by this project's own pipeline decide **what kind of site it is** and **which sections it needs**; rule-based extraction reads the name, tagline, email, phone, location and color or tone words; the page is assembled from a library of section templates and a team-written content bank, shown in a live preview (desktop, tablet, mobile), edited in the app, saved to SQLite and exported as a ZIP that opens offline.

Based on: Reddy, Bodhke, Patil, Gorad, Chavan, Mall, "AI Website Builder", International Journal of Creative Research Thoughts (IJCRT), Vol. 13, Issue 10, October 2025, paper ID IJCRTBH02018. DOI: not provided in the source. This project implements the paper's idea as a self-contained application and measures its own results; the paper's reported figures are not reused.

Facts: Python 3.11+ (see Notes), Flask + Jinja2, scikit-learn (TF-IDF + logistic regression), SQLite, port **5050**, no internet needed after the one-time package install, no external requests from the builder or from generated sites.

## Screenshots (real browser captures, Chrome)

Captured by `scripts/capture_screenshots.py` against the running app (screens in `docs/screenshots/`).

| Screen | Light | Dark / other |
|---|---|---|
| Builder, empty state | [builder-empty](docs/screenshots/builder-empty.png) | |
| Builder, "How I understood your request" | [builder-result](docs/screenshots/builder-result.png) | [dark](docs/screenshots/builder-result-dark.png) |
| Builder, low-confidence warning (`asdf qwerty`) | [builder-low-confidence](docs/screenshots/builder-low-confidence.png) | |
| Editor, desktop 1440 px | [editor-desktop](docs/screenshots/editor-desktop.png) | [dark](docs/screenshots/editor-desktop-dark.png) |
| Editor, tablet 820 px | [preview](docs/screenshots/editor-tablet.png) | [edit tab](docs/screenshots/editor-tablet-edit.png) |
| Editor, mobile 390 px | [preview](docs/screenshots/editor-mobile.png) | [edit tab](docs/screenshots/editor-mobile-edit.png) |
| Preview width toggles inside the desktop editor | [tablet](docs/screenshots/editor-preview-tablet.png) | [mobile](docs/screenshots/editor-preview-mobile.png) |
| Projects | [projects](docs/screenshots/projects.png), [empty](docs/screenshots/projects-empty.png) | [dark](docs/screenshots/projects-dark.png) |
| About the AI | [about](docs/screenshots/about.png) | [dark](docs/screenshots/about-dark.png) |
| Exported ZIP opened from `file://` | [desktop](docs/screenshots/exported-site-desktop.png) | [mobile](docs/screenshots/exported-site-mobile.png), [menu](docs/screenshots/exported-site-mobile-menu.png) |

## Run it

### 1. One command (recommended)

```bash
./start.sh        # macOS / Linux
start.bat         # Windows (double-click or run in a terminal)
```

The script creates `.venv` if missing, installs `requirements.txt` (the only step that needs the internet, once), copies `.env.example` to `.env`, and starts the app. Open **http://127.0.0.1:5050**.

### 2. Manual

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate.bat  (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
python app.py                        # or: python -m flask run --port 5050
```

`python -m flask run` uses Flask's default port 5000 unless you pass `--port 5050`. Settings live in `.env` (`AIWB_HOST`, `AIWB_PORT=5050`, `AIWB_DB`).

### Platform notes

- **macOS / Linux:** `./start.sh` needs `bash` and `python3` (3.11+). Set `PYTHON=/path/to/python3.11` if `python3` is older. If the script is not executable: `chmod +x start.sh train.sh`.
- **Windows:** `start.bat` uses the `py` launcher when present. If PowerShell blocks `Activate.ps1`, use `activate.bat` or run `start.bat`. The `.bat` files were written for Windows but **have not been run on a Windows machine** in this build (only macOS was available).
- **Linux:** a minimal distro may need `python3-venv` (`sudo apt install python3-venv`).
- The app only listens on `127.0.0.1`; it is single-user and local.

## Using the app

1. **Builder:** type a description (max 1000 characters) or click an example, press Generate. The page shows how the prompt was understood: site type with confidence, sections, name, tagline, email, phone, location, color and tone words. Correct anything and press *Rebuild with my changes*, or *Open in editor*.
2. **Editor:** edit text of any section, show/hide sections (navigation bar, hero and footer are always present), reorder, add a section that was not generated, change palette and font, edit the prompt and regenerate, switch the preview between desktop, tablet and mobile, Save, Download ZIP, rate the result 1-5 with an optional comment.
3. **Projects:** open, duplicate, download or delete saved projects (local SQLite file `data/projects.sqlite3`).
4. **About the AI:** reads `/api/ml/info`, `/api/eval` and `/api/feedback/summary` and shows only measured values.

Generating a project saves it immediately as a draft row; Save in the editor stores your edits and writes an entry to the edits log.

## Architecture

```
ml/data/*.csv --(ml/train.py -> ML-Training-App/text_pipeline.py)--> ml/artifacts/
   site_type.joblib  sections.joblib  metrics.json  model_card.md  eval_results.json

Browser (HTML/CSS/vanilla JS)  <-HTTP->  Flask (app/)
  Builder / Editor+preview / Projects / About     Prompt Preprocessor -> Requirement Extractor
                                                    (ml/predictor.py classifiers + app/slots.py rules)
                                                  -> Component Assembler (site_templates/ + content/)
                                                  -> Theme Engine -> Renderer/Exporter (HTML, CSS, JS, ZIP)
                                                  Project Store (SQLite)
```

**Learned:** the site-type classifier and the section predictor, and nothing else. **Rule-based:** slot extraction, theme choice, section order, the always-on navbar/hero/footer rule, content-bank selection, the low-confidence heuristics. **Template assembly:** the pages themselves; the app selects, fills and styles templates and cannot invent layouts. The generated JavaScript is always the one fixed file `site_templates/script.js`; all user text is escaped by Jinja2 autoescaping.

## Retraining

```bash
./train.sh        # macOS / Linux          train.bat   (Windows)
```

Creates the venv, installs requirements, runs `ml/train.py` then `ml/evaluate.py`. Training uses the team's generic **ML-Training-App** (`text_pipeline.py`): `train_text_model(feature_mode="tfidf", plain_classifier_name=..., write_report=True)` for the site type, and the new generic `train_multilabel_text_model` (one-vs-rest heads, per-label thresholds chosen on the validation split) for the sections. The folder is found through the environment variable `ML_TRAINING_APP` (default: the sibling folder `../ML-Training-App`). It is needed only for retraining; the app loads `ml/artifacts/` with plain scikit-learn and joblib and never imports the tool. Artifacts are committed so the demo runs without retraining. If they are missing the app refuses to start with instructions (no fallback).

`python ml/data/build_dataset.py` regenerates the prompt CSVs (seeded, deterministic). `python scripts/make_icons.py` regenerates the icons. `python scripts/capture_screenshots.py` (needs `pip install playwright` and Google Chrome) recaptures the screenshots.

## Results (measured; read the caveat)

**Caveat:** every prompt (training, validation, test and evaluation) was written by the team from templates (see *Data*). Scores show how well the models learn that style of writing, not general accuracy; real users' prompts will usually score lower, and the second column below shows how much lower when the wording is unseen.

| Measure | 5-fold CV (train split) | Held-out test (180 prompts) | `eval_prompts.csv` (122 prompts, unseen wording) |
|---|---|---|---|
| Site type accuracy | 0.957 +/- 0.014 | **98.9%** | **63.1%** |
| Site type macro F1 | 0.957 +/- 0.014 | 0.989 | 0.633 |
| Sections micro F1 (7 learnable) | 0.933 +/- 0.006 | 0.941 | 0.822 |
| Sections macro F1 | 0.929 | 0.943 | 0.753 |
| Exact-set match | 0.587 | 0.650 | 0.287 |

- The 20 hand-labelled harder prompts inside `eval_prompts.csv`: site-type accuracy 80.0%.
- Generation time (full pipeline incl. rendering and validity check, 122 prompts, after warm-up, Apple-silicon Mac): mean 4.23 ms, median 4.24 ms, 95th percentile 4.82 ms. The paper's own reported figure is not used.
- User ratings: collected in the app; the About page shows the average and the number of ratings (none until someone rates).
- Per-section precision/recall, the confusion matrix and the thresholds are in `ml/artifacts/model_card.md`, `ml/artifacts/metrics.json`, the About page and `docs/test-evidence/ml-evaluation.png`.

### Data

`ml/data/prompts.csv` (1200 prompts, 6 site types: portfolio, restaurant, small business, education, blog, non-profit; split 840 / 180 / 180 into `prompts_train/val/test.csv`, stratified) and `ml/data/eval_prompts.csv` (122 prompts) did not exist, so the developer authored them with `ml/data/build_dataset.py`: hand-written vocabulary (who the site is for, how each section can be asked for, names, cities, colors) combined with hand-written sentence frames, filler sentences and random typos. Labels are derived by explicit rules from what was written into each prompt (site type = the noun phrase used; sections = the site type's base set plus requested sections minus negated ones, or only the requested ones for "only/just" prompts; plus navbar, hero, footer), never by a model. `eval_prompts.csv` uses different frames, different noun phrases for every site type, different section wording and names, no-hint prompts and 20 hand-labelled harder prompts; it is disjoint from training and was not used for training, selection or any threshold. A **team review of the labels has not happened.**

Development note: the first run used 12 training noun phrases per site type and reached 59.8% site-type accuracy on `eval_prompts.csv` with 70% of its prompts flagged low-confidence. The training vocabulary was then enlarged once to about 30 noun phrases per type (no `eval_prompts.csv` phrase was added) and the data was regenerated. The numbers above are from after that change, so `eval_prompts.csv` is not perfectly blind to that one design decision.

Second data change (tester defect): the prompt "An online coding school called CodeNest with pricing plans, FAQ and student reviews" did not get a testimonials section because the training data never used the wording "student reviews" (testimonials score 0.15 against a 0.45 threshold when listed beside pricing and FAQ). Nine more phrasings of reviews/testimonials/feedback were added to the training generator only (not copied from `eval_prompts.csv`), the data was regenerated and the models retrained; the prompt now gets testimonials (score 0.96). Regenerating changes the whole random draw, so every number moved: previous run -> this run: held-out test site-type accuracy 98.3% -> 98.9%; eval site-type accuracy 63.9% -> 63.1%; eval sections micro F1 0.836 -> 0.822; eval low-confidence share 44.3% -> 49.2%; threshold 0.4665 -> 0.4282. Differences of this size are within the noise of a small templated test set and are not an improvement or a regression.

### Low-confidence check

A site is flagged when the maximum site-type probability is below **0.4282** (5th percentile of validation-split confidence, chosen on validation data only), or the prompt has fewer than 2 words, or fewer than 50% of its words occur in the training vocabulary. The Builder and Editor then show a warning with the reasons and the site is treated as a guess the user should check. Measured: flagged 5.0% of held-out test prompts, 49.2% of `eval_prompts.csv` (36 of the 45 wrongly classified eval prompts, and 24 correctly classified ones), and all 31 hand-written probes (nonsense such as `asdf qwerty`, unrelated questions such as `what is the capital of France`, one-word inputs, non-English text, code). **What the check cannot catch:** fluent English that mentions a supported topic (for example "what is the best bakery in France") passes as a confident bakery site; partly relevant or adversarial text is not detected; and good prompts with unusual wording are flagged too (the 49.2% figure). Non-English prompts are caught mainly because their words are unseen, not because language is detected. A test records the known false negative.

## Tests

```bash
source .venv/bin/activate && python -m pytest        # 150+ tests, about 3 s
```

Unit tests (slots, theme contrast, assembler, renderer, store), security tests (escaping of `<script>`, event attributes, tag injection through prompt and edit; fixed JavaScript), API tests for every route including empty, over-long and invalid input and unknown project ids, ML tests (artifact formats, missing-artifact startup error, low-confidence probes, data-file schemas and held-out checks), page tests (no external URLs, no hard-coded measurements on the About page) and docs-vs-code consistency checks (port 5050, confidence threshold, measured accuracy quoted here). `docs/Requirements Traceability.md` maps every objective and functional requirement to modules and tests. Real-browser verification is done with `scripts/capture_screenshots.py` (see Screenshots; it also checks that a live text edit shows in the preview and that the exported site shows the same text). `docs/test-evidence/` holds the saved run outputs.

## Deviations from the paper and the specification (Change Control)

Approved in the specification:
- scikit-learn TF-IDF classifiers instead of transformer models, spaCy and Hugging Face downloads.
- A template library with rule-based theme and layout selection instead of generative design models and reinforcement learning (no reinforcement-learning component).
- A local Flask app with ZIP export instead of Flask or Django on Vercel.
- SQLite and files instead of separate Template and Content databases.
- The paper's 83% accuracy, 81% satisfaction and 7.8-second figures are not claimed; this project's own measurements replace them.

Decided during this build (architect decisions, document-only changes to the supplied inputs):
- The team-labelled training and evaluation prompts were missing, so they were authored as templated, seeded data (see Data); measured accuracy is optimistic.
- Models are trained with the team's ML-Training-App (generic, no project names in it), which gained an optional multi-label function; the app depends only on the artifacts.
- The site-type head is restricted to logistic regression (probabilities are needed for the confidence check), and neither model is refit on train+validation so that the validation-chosen thresholds describe exactly the saved models.
- Navbar, hero and footer are constant labels (always positive), so section metrics are reported over the 7 learnable sections (all-10 micro F1 is in `metrics.json`).

## Known limitations

- The system selects, fills and styles pre-built templates; it does not invent layouts or write free-form code. Six site types, ten sections. Copy is team-written placeholder text until edited.
- Accuracy is measured on team-authored prompts (see above); other languages, very long prompts and requests outside the six types are handled poorly. Slot extraction can miss unusual phrasings of a name or color.
- The contact form in generated sites is static (it opens the visitor's mail client). The live preview iframe is sandboxed and does not submit forms.
- No hosting, accounts, e-commerce, CMS, image generation or in-app retraining (out of scope).
- Ratings come from whoever tests the app; the About page shows how many there are. Deleting a project deletes its rating.
- Python: the pinned packages (numpy 2.4, pandas 3, scikit-learn 1.9) need **Python 3.11+**, although the specification says 3.10+; on 3.10 the pins would have to be relaxed and the models retrained. Tested only on macOS (Python 3.11.6); Windows and Linux scripts are untested.
- Dependencies in `requirements.txt` are the full frozen set of the tested environment (pytest and matplotlib are included for tests and `evaluate.py`).
