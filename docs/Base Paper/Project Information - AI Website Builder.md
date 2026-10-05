# Project Information: AI Website Builder

**Project ID:** (to be assigned)

**AI Website Builder - Natural-Language Website Generator**
*A local Python (Flask) web application with two trained classifiers*

## Overview

AI Website Builder adapts the base paper "AI Website Builder" (Reddy, Bodhke, Patil, Gorad, Chavan, Mall; International Journal of Creative Research Thoughts (IJCRT), Vol. 13, Issue 10, October 2025, paper ID IJCRTBH02018; DOI: not provided in the source) into a self-contained local application. A user types a plain-English description of a website. Two classifiers trained by this project's own pipeline predict the site type and the required sections; rule-based extraction reads the site name, tagline, email, phone, location and color or tone words; the page is assembled from responsive section templates and a team-written content bank, themed from a palette and system-font stack, and shown in a live preview at desktop, tablet and mobile widths. The user edits text, sections and theme, saves projects in SQLite, rates the result and exports a ZIP (`index.html`, `style.css`, `script.js`) that works offline. Nothing is downloaded or called at run time, and the app says when its confidence is low.

## Problem Statement

Building a professional website needs coding knowledge, design skill, time and money, so individuals, students and small businesses often cannot create one, and existing builders still demand manual effort and offer limited flexibility. This project lets a user describe the site in a few sentences and get a complete, editable, responsive website in a fraction of a second, with the system showing how it understood the request.

## Core Implementation

### 1. Platform

A Python application (Python 3.11+ with the pinned packages) running a local Flask server with a browser UI on `127.0.0.1:5050`, tested on macOS. The UI is plain HTML, CSS and vanilla JavaScript with a full light and dark theme, generated app icon and favicon, system fonts only and no external request. Single-user and local: no accounts, hosting or cloud.

### 2. Requirement Extraction (what is learned)

`ml/train.py` uses the team's generic ML-Training-App `text_pipeline.py`: `train_text_model(feature_mode="tfidf")` produces the **site-type classifier** (TF-IDF word 1-2-grams and character 2-5-grams, logistic regression, one of six types: portfolio, restaurant, small business, education, blog, non-profit) and a new generic `train_multilabel_text_model` produces the **section predictor** (one-vs-rest logistic regression with one threshold per section chosen on the validation split). Both use seed 42 and five-fold cross-validation on the training split; `ml/evaluate.py` scores the held-out test split and a separate evaluation set. The app loads only `ml/artifacts/` (`site_type.joblib`, `sections.joblib`, `metrics.json`, `model_card.md`, plus `eval_results.json`) with plain scikit-learn and joblib and refuses to start if they are missing.

Measured (team-authored prompts; optimistic): site-type accuracy 98.9% on the held-out test split (180 prompts) and 63.1% on 122 evaluation prompts with unseen wording; five-fold CV accuracy 0.957 +/- 0.014; sections micro F1 0.941 (test) and 0.822 (evaluation). Details and caveats are in `README.md` and `ml/artifacts/model_card.md`.

### 3. Slot Extraction, Theme and Assembly (what is rule-based)

- **Slot Extractor:** regular expressions and word lists find a quoted name or "called/named/name is X", tagline, email, phone, location and color and tone words.
- **Theme Engine:** color words, then tone words, choose one of six palettes (including a dark one) and one of five system font stacks; defaults per site type when none.
- **Component Assembler:** takes the predicted sections plus the always-present navbar, hero and footer, orders them with a per-type layout rule and fills the section templates from the content bank (`content/<site_type>.json`, sample text, editable).
- **Hand-written rules:** the mandatory navbar/hero/footer rule, section order, content selection and the low-confidence heuristics.

### 4. Rendering, Preview and Export

The Renderer is a pure function of a validated site model (JSON: site type, theme, slots, ordered sections with content and visibility). Jinja2 autoescaping escapes all user text, templates never use `safe`, and the JavaScript is always the one fixed `script.js` (mobile menu toggle). Output is checked (balanced HTML, viewport meta, `@media` rules, no external URL) before use. The live preview (a sandboxed iframe) and the ZIP export use the same code, so they match; the ZIP is built with `zipfile`.

### 5. Editor and Projects

The Editor edits any section text, hides or shows sections, reorders them, adds a section that was not generated, switches palette and font, and regenerates from a changed prompt, with a live preview and device-width toggles. Projects are saved, reopened, duplicated and deleted from SQLite (`projects`, `edits`, `feedback` tables); an edits log records what changed on each save.

### 6. Feedback and the About the AI Page

After generating, the user rates the site 1-5 with an optional comment (stored locally; one rating per project). The About page reads `/api/ml/info`, `/api/eval` and `/api/feedback/summary` and shows classifier metrics, cross-validation results, the confusion matrix, per-section precision and recall, generation time (mean 4.23 ms, 95th percentile 4.82 ms over the evaluation prompts, measured) and the average rating with the number of ratings, never hard-coded values.

### 7. Handling Unclear Input (Low Confidence)

A prompt is flagged when the maximum site-type probability is below the validation-chosen threshold **0.4282**, when it has fewer than two words, or when fewer than half of its words occur in the training vocabulary. The Builder and the Editor then show the reasons and the site is presented as a guess to check; the user can correct the type and sections and rebuild. Measured: 5.0% of held-out test prompts flagged, 49.2% of the evaluation prompts, and all 31 hand-written nonsense, unrelated, one-word, non-English and code probes. The check cannot catch fluent English about a supported topic (such as a question about bakeries) and flags some unusual but valid wording.

### 8. Application Structure

```
app/            create_app, routes, preprocess, slots, theme, assembler, renderer, sitemodel, store, engine
app/templates/  Builder, Editor, Projects, About, layout      app/static/ css, js, icons (local only)
site_templates/ section templates, 6 theme files, 5 font files, base.css, fixed script.js
content/        team-written sample copy per site type
ml/             data/ (build_dataset.py, prompts, eval_prompts, ood_probe), train.py, evaluate.py,
                predictor.py (runtime loader), artifacts/ (committed)
tests/          pytest suite        scripts/ icons and screenshot capture
start.sh/.bat   train.sh/.bat       docs/ screenshots, test evidence, traceability, this file
```

### Known Limitations (as documented)

- Selects, fills and styles templates; six site types and ten sections; placeholder-quality copy until edited.
- Accuracy is measured on prompts the team authored from templates (the supplied labelled data did not exist), so it is optimistic; a team review of the labels has not happened. Wording the models have not seen drops site-type accuracy to 63.1% on the evaluation set.
- Other languages, very long prompts and requests outside the six types are handled poorly; slot rules miss unusual phrasings.
- Static contact form (opens the visitor's mail client); no hosting, accounts, e-commerce, CMS or in-app retraining.
- Pinned packages need Python 3.11+ (the specification says 3.10+); only macOS was tested.

### Deviations from the paper and specification (Change Control)

- scikit-learn TF-IDF classifiers instead of transformer models, spaCy and Hugging Face; a template library with rule-based theme and layout instead of generative design models and reinforcement learning (no RL component); a local Flask app with ZIP export instead of Flask or Django on Vercel; SQLite and files instead of separate Template and Content databases; the paper's 83% accuracy, 81% satisfaction and 7.8-second figures are not claimed.
- Team-authored templated training and evaluation prompts because none existed; trained with the team's ML-Training-App extended with an optional multi-label function; site-type head limited to logistic regression for probabilities; models not refit on train+validation; section metrics reported over the seven learnable sections; training vocabulary enlarged once after the first evaluation (59.8% on the evaluation set), and more reviews/testimonials phrasings added after a tester found "student reviews" unrecognised; both disclosed in the README.

### Planned Future Improvements

Team review of labels and prompts collected from real users; more site types and sections; a language check; threshold re-tuning with real prompts; user-defined content banks; HTTPS and accounts if ever served beyond localhost.

## Key Design Principles

- Honest measurement: every figure shown in the app comes from measured files with caveats displayed; none is copied from the paper.
- Safe by construction: all user text escaped, fixed JavaScript, a validating gate on every site model.
- Fail loudly: missing artifacts stop the app with instructions; low confidence is shown, never hidden; no silent fallback.
- Simple and local: no CDN, web fonts, external images or hosted API; one SQLite file; the app depends only on plain scikit-learn artifacts.
- Preview equals export: one Renderer for both.

## Tech Stack Summary

| Layer | Technology |
|---|---|
| App | Python 3.11+, Flask, Jinja2, vanilla HTML/CSS/JavaScript |
| ML | scikit-learn (TF-IDF, logistic regression, one-vs-rest), pandas, numpy, joblib; trained with the team's ML-Training-App |
| Rules | regular expressions and word lists (slots, theme) |
| Storage | SQLite (`sqlite3`) |
| Export | `zipfile` |
| Tests | pytest, real-browser captures with Playwright and Chrome (development only) |
