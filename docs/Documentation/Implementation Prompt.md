<!-- ============================================================
     IMPLEMENTATION PROMPT
     This file is not a report chapter - it's meant to be copy-
     pasted whole into an AI coding assistant (Claude Code, Cursor,
     etc.) to scaffold and build the actual project. Source paper:
     "AI Website Builder", Reddy, Bodhke, Patil, Gorad, Chavan,
     Mall, International Journal of Creative Research Thoughts
     (IJCRT), Vol. 13, Issue 10, October 2025 (IJCRTBH02018).
     Platform decision: a Python application (local Flask web app),
     not Android. Project ID: (fill in when assigned)
     ============================================================ -->

You are building **AI Website Builder** from scratch, a CSE final-year project. Read this entire specification before writing any code - it is the complete, authoritative handoff. Build exactly what is described below.

## Requirement Priority

When interpreting this specification, use the following priority order:

1. Explicit mandatory requirements (Objectives, Functional Requirements).
2. Explicit technical constraints (Technology Stack, Dependencies).
3. Defined architecture and module contracts (System Architecture, Software Modules).
4. Functional workflow.
5. Non-functional requirements.
6. Implementation guidance and examples (Build Plan, Development Environment).
7. Agent-selected implementation details.

If two statements conflict, follow the higher-priority statement and report the conflict rather than guessing.

## Consistency Rules

- Build only the objectives, functional requirements, and architecture defined in this specification.
- Do not add user-facing features, modules, or capabilities that are not required.
- Do not silently remove, reinterpret, or replace a stated requirement.
- Use the mandatory technology choices specified in the Technical Constraints section.
- Supporting libraries may be introduced when necessary to implement the mandatory technology choices, provided they do not change the architecture or project scope.
- If an instruction is ambiguous, first determine whether it can be resolved from another part of this specification.
- If the ambiguity materially affects the architecture, functionality, or technology choice, stop and request clarification rather than making a major assumption.
- Keep the scope appropriate for a single-semester final-year project.
- Prefer the simplest complete implementation over a more complex implementation that provides unrequested capabilities.

## Assumptions & Implementation Freedom

The requirements explicitly identified as mandatory below must be implemented as specified.

Where an implementation detail is not explicitly specified, choose the simplest implementation that satisfies the stated requirements and remains consistent with the defined architecture and technology constraints.

Do not introduce new user-facing features, modules, services, or architectural components unless they are required to satisfy an existing requirement.

Clearly distinguish between:
- **Mandatory requirements** that must be followed exactly - everything under Functional Requirements, Technical Constraints, and Objectives below.
- **Confirmed technical decisions** that should not be changed without justification - the architecture and module boundaries below.
- **Project assumptions** that may need validation - anything in Known Limitations or drawn from an unverified paper/source.
- **Implementation details** that may be chosen by the coding agent - anything this specification leaves unstated (exact file layout, naming, minor UI styling, etc.).

Do not treat an assumption as a confirmed requirement unless this specification explicitly states it as mandatory.

## Agent Operating Rules

- Read and understand this entire specification before writing code.
- Inspect the existing repository and project structure before creating or modifying files.
- Implement the smallest complete solution that satisfies the specification.
- Reuse existing project structure and dependencies where appropriate.
- Do not add features, screens, modules, services, or dependencies that are not required.
- Do not create placeholder implementations for functionality that is marked as required.
- Do not silently substitute a different technology, framework, library, model, or architecture.
- Do not claim that a feature is complete unless it has been implemented and appropriately tested.
- Keep the implementation understandable and appropriate for a final-year student project.
- Prefer simple, maintainable solutions over unnecessary abstractions or production-scale architecture.
- If a requirement cannot be implemented as specified, stop at that point and report the issue rather than silently changing the requirement (see Change Control below).
- Load nothing from the internet at run time: no CDN scripts, no web fonts, no external images, in the builder UI or in generated websites.

## Project brief

**Problem statement:** Building a professional website needs coding knowledge, design skill, time and money, so individuals, students and small businesses often cannot create a site of their own, and existing website builders still demand manual effort and offer limited flexibility.

**Proposed solution:** A Python application that turns a plain-English description of a website ("a modern website for my bakery called Sweet Crumbs with a menu, gallery and contact form") into a complete, responsive, multi-section website made of HTML, CSS and a little JavaScript. Custom machine-learning models, trained by this project's own pipeline, read the description and decide what kind of site it is and which sections it needs; rule-based extraction pulls out names, contact details and colors; the site is assembled from a library of reusable section templates and content banks, shown in a live preview, edited in the app, and exported as a ZIP.

**Expected outcome:** A working local Python web application in which a user types a description, gets a generated responsive website in seconds, previews it at desktop, tablet and mobile widths, edits text, sections and theme, saves it, and downloads it as a static site, with the models' measured accuracy and the generation time shown on an "About the AI" page.

**Abstract:** The source paper proposes an AI Website Builder that uses natural language processing, machine learning and pre-trained design models to generate responsive, customizable websites from simple text input. Its methodology collects website-template datasets and HTML/CSS libraries, preprocesses user input with NLP to extract requirements, maps them to structured components with transformer models, produces layouts with generative design models and reinforcement learning, assembles HTML, CSS and JavaScript into responsive pages, and deploys through Flask or Django backends on Vercel. It reports 83% requirement-to-website mapping accuracy, 81% survey-based satisfaction and a generation time of about 7.8 seconds, without describing the dataset or protocol. This project implements the same pipeline as a self-contained Python application with no downloaded models or external services. A requirement-extraction stage combines two classifiers trained by the project's own pipeline (site type and required sections, with five-fold cross-validation as in the paper) with rule-based slot extraction. A component-assembly stage fills a library of responsive section templates and content banks, a theme engine applies a palette and typography chosen from the description, and an editor lets the user adjust the result. Results are measured on the project's own held-out prompts rather than copied from the paper.

## Objectives (mandatory - all must be met)

- To accept a natural-language description of a website and extract its requirements: the site type and the list of required sections, predicted by custom classifiers trained by this project's own pipeline, plus the site name, tagline, contact details and color preferences extracted by rules.
- To assemble a complete, responsive website (HTML, CSS and JavaScript) from a library of section templates, content banks and a theme engine, using only the extracted requirements, and to show it in a live preview at desktop, tablet and mobile widths.
- To let the user customize the generated site (edit text, add, remove and reorder sections, switch theme and fonts), save projects, and export a site as a ZIP that opens offline.
- To measure and display the system's performance: component-prediction accuracy with five-fold cross-validation and held-out test scores, average generation time, and user ratings collected in the app.

## Functional Requirements

What the system must allow the user or system to do. Only the objectives above and the features below are functional requirements - do not treat examples or illustrative wording elsewhere in this document as additional requirements.

- Prompt-to-website generation — enter a description, generate a site, and show the extracted requirements (site type, sections, name, colors) so the user can see how the prompt was understood
- Requirement extraction — site-type classifier and multi-label section predictor trained by the project's pipeline, plus rule-based extraction of name, tagline, email, phone, location and color or tone words
- Component assembly — build the page from section templates (navigation bar, hero, about, features or services, gallery, pricing, testimonials, FAQ, contact, footer) and content banks for at least five site types (for example portfolio, restaurant, small business, education, blog)
- Theme engine — color palettes and font stacks (system fonts only) chosen from the description, switchable in the editor
- Live preview — render the generated site in the browser with device-width toggles (desktop, tablet, mobile)
- Editor — edit text of any section, show or hide sections, reorder sections, change theme, and regenerate from a changed prompt
- Projects — save, reopen, duplicate and delete projects in a local database
- Export — download the site as a ZIP containing `index.html`, `style.css` and `script.js` that works offline
- Safe output — all user-supplied text is escaped in the generated site, and generated JavaScript comes only from fixed templates
- Feedback and evaluation view — a 1-5 rating with optional comment per generated site, and an "About the AI" page showing classifier metrics, cross-validation results, generation time and the average user rating with the number of ratings

## Non-Functional Requirements

Measurable or observable qualities the system must exhibit (performance, reliability, offline/online behavior, usability), drawn from this project's own documented performance discussion and requirements summary below. Where this section reads thin or unspecific, that is a signal the source material didn't fix a hard number - default to "the simplest workable behavior consistent with Scope and Complexity Control" rather than inventing a specific target (a latency budget, a concurrency limit, etc.) that was never actually required.

The decision to replace the paper's transformer models, generative design models and reinforcement learning with small trained classifiers plus a template library is expected to remain reliable for a student demo because website requirements in a short prompt are largely categorical (what kind of site, which sections), which linear models on TF-IDF features learn well from a few hundred labeled prompts, and because assembling known-good templates guarantees valid, responsive output. Generation therefore takes well under a second on a laptop CPU, runs offline, and cannot produce broken markup. The cost is less creative freedom than a generative model; the system selects, fills and styles templates, and it must say so.

The paper's reported 83% mapping accuracy, 81% satisfaction and 7.8-second generation time describe the authors' own system and an undescribed dataset. This project must not reuse them; it measures its own accuracy on its own held-out prompts, its own generation time, and the ratings actually collected in the app.

The application is single-user and local, so no scaling, containerization or cloud deployment is required. It must run with no internet access after the one-time installation of Python packages, on Windows, macOS and Linux.

## Technical Constraints (mandatory)

Platforms, languages, frameworks, libraries, and models below are mandatory. Do not replace any of them without following Change Control.

| **Category** | **Technology** |
| --- | --- |
| Platform | Python 3.10+ application: local Flask web server with a browser UI (Windows, macOS, Linux) |
| Programming Language | Python (application, ML), HTML/CSS/vanilla JavaScript (builder UI and generated sites) |
| Web Framework | Flask with Jinja2 templating |
| Site Generation | Jinja2 section templates and CSS theme files authored in the project; no external CSS or JS frameworks |
| Requirement Classifiers | scikit-learn: TF-IDF features with a linear model for site type and a one-vs-rest linear model for sections, trained by the project's own pipeline |
| Slot Extraction | Rule-based (regular expressions and word lists) |
| Model Persistence | joblib artifacts, plus `model_card.md` and `metrics.json` |
| Storage | SQLite (Python `sqlite3`) for projects, edits and feedback |
| Export | Python `zipfile` |
| Test Frameworks | pytest |

**Why each choice** (for context, not for you to re-justify or reconsider):

| **Technology** | **Reason** |
| --- | --- |
| Local Flask web app | Cross-platform, pure Python, gives a real browser preview of generated HTML, and avoids desktop GUI toolkits that cannot render web pages well. |
| Jinja2 templates | Deterministic, safe (auto-escaping) assembly of valid HTML from components. |
| scikit-learn classifiers | The paper's NLP step as a real, trainable, evaluable ML component with no model downloads; supports the paper's five-fold cross-validation. |
| Rule-based slot extraction | Names, emails, phones and colors follow patterns that rules extract reliably and explainably. |
| SQLite | Single-file local storage for projects and feedback, no server. |
| ZIP export | Replaces the paper's Vercel deployment with a portable offline result. |

**Dependencies:**

| **Dependency** | **Required** |
| --- | --- |
| Python 3.10+ | ✅ |
| Flask, Jinja2, scikit-learn, pandas, numpy, joblib (installed once, then offline) | ✅ |
| Team-labeled prompt data in `ml/data/` | ✅ |
| A modern browser (Chrome, Edge, Firefox, Safari) | ✅ |
| Transformer or generative models, spaCy, Hugging Face downloads, hosted LLM APIs, reinforcement-learning libraries | ❌ Not used |
| Vercel, Docker, cloud hosting | ❌ Not used |
| Internet (only to install packages once) | ✅ |

## Preflight Validation

Before beginning implementation, review this specification for technical consistency and feasibility. Validate, where applicable:

- The required technologies above are compatible with each other.
- The required frameworks and libraries support the functionality described in Functional Requirements.
- Any required model can be used with the specified runtime (all models are scikit-learn artifacts trained locally).
- Required APIs and dependencies are available for the target platform (Python 3.10+ on Windows, macOS and Linux).
- The module interfaces defined below are compatible with each module's expected inputs and outputs.
- Any performance or resource expectations in Non-Functional Requirements are reasonably achievable on the specified stack.
- The architecture below can support every mandatory feature.
- The labeled data files exist and follow the schemas below. If they are missing, stop and report it; do not invent labels to make training run.

If a significant feasibility issue is discovered, do not silently change the architecture or replace a required technology, and do not begin building around an unverified assumption - follow Change Control instead. If no blocking issue is found, proceed with implementation.

## System architecture

The source paper's figure shows: User -> Frontend -> AI Engine, connected to a Backend, a Template Database and a Content Database, with Data Storage behind them. This build keeps that structure.

```
Offline preparation                                  (run once, locally)
  ml/data/prompts.csv  (team-labeled prompts: text, site_type, sections)
        -> train site-type + section classifiers (5-fold CV) -> evaluate
        -> ml/artifacts/ {site_type.joblib, sections.joblib, metrics.json, model_card.md}

Browser UI (HTML/CSS/JS)  <--HTTP-->  Flask backend (localhost)
  Builder page (prompt box)              AI Engine
  Editor + live preview                    1. Requirement Extractor  (classifiers + slot rules)
   (desktop/tablet/mobile)                 2. Component Assembler    (section templates + content banks)
  Projects page                            3. Theme Engine           (palettes, fonts)
  About the AI page                        4. Renderer / Exporter    (index.html, style.css, script.js, ZIP)
                                         Template Library  (site_templates/: sections, themes)
                                         Content Bank      (content/: copy per site type)
                                         SQLite            (projects, edits, feedback)
```

## Functional workflow

1. The user opens the app in a browser and sees the Builder page with a prompt box and a few example prompts.
2. The user enters a description and presses Generate. The Requirement Extractor predicts the site type and the section list, and rule-based extraction finds the site name, tagline, email, phone, location and color or tone words. The page shows these as an editable "How I understood your request" panel.
3. The Component Assembler selects the section templates in a sensible order for the site type, fills them from the extracted slots and the content bank for that type, and the Theme Engine picks a palette and font stack from the color and tone words (defaults when none).
4. The Renderer produces `index.html`, `style.css` and `script.js` with all user text escaped, and the app opens the Editor with a live preview in an iframe. The user can switch the preview between desktop, tablet and mobile widths.
5. In the Editor the user edits section text, hides or shows sections, reorders them, changes the theme and fonts, or edits the prompt and regenerates. Each change re-renders the preview.
6. The user saves the project (stored in SQLite), can reopen, duplicate or delete it from the Projects page, and downloads it as a ZIP that opens offline.
7. After generating, the user can rate the result 1-5 with an optional comment; ratings are stored locally.
8. The About page shows the classifiers' held-out and cross-validation metrics, the measured average generation time on the evaluation prompts, the average user rating with the number of ratings, and the list of supported site types and sections.

## Software modules (build each of these as a distinct, identifiable unit)

| **Module** | **Responsibility** | **Inputs -> Outputs** |
| --- | --- | --- |
| Prompt Preprocessor | Clean and normalise the prompt text | raw prompt -> normalised text |
| Site-Type Classifier (`ml/`) | Predict one of the supported site types | text -> site type + confidence |
| Section Predictor (`ml/`) | Predict the required sections (multi-label) | text -> section list + scores |
| Slot Extractor | Extract name, tagline, email, phone, location, colors, tone words | text -> slots |
| Component Assembler | Choose and order section templates, fill slots and content bank | requirements -> site model (ordered sections with content) |
| Theme Engine | Map color and tone words to a palette and font stack | slots -> theme |
| Renderer / Exporter | Render HTML/CSS/JS with escaping and build the ZIP | site model + theme -> files / ZIP |
| Project Store | Save, load, duplicate, delete projects and feedback | project data -> SQLite rows |
| Evaluator | Measure classifier metrics and generation time on held-out prompts | `eval_prompts.csv` -> `eval_results.json` |
| Flask API and pages | Serve the UI, preview routes and JSON endpoints | HTTP requests -> pages / JSON |
| Browser UI | Builder, Editor with preview, Projects, About | user actions -> API calls |

**Training and evaluation data (team-supplied, schemas fixed):**
- `ml/data/prompts.csv`: `text,site_type,sections` where `sections` is a pipe-separated list from the fixed section vocabulary (`navbar|hero|about|features|gallery|pricing|testimonials|faq|contact|footer`). At least 500 team-written prompts across at least 5 site types, varied in wording and length, with a saved train/validation/test split. Document how prompts and labels were produced.
- `ml/data/eval_prompts.csv`: same schema, at least 80 held-out prompts never used for training or for tuning any threshold.
- `content/<site_type>.json`: team-written placeholder copy for each section of each site type (headlines, paragraphs, feature lists, FAQ items). It is sample content, editable in the app, and must be presented as such.

**ML pipeline contract:**
- `ml/train.py` fits both models on TF-IDF features with fixed seeds and pinned requirements and runs five-fold cross-validation on the training split; `ml/evaluate.py` reports site-type accuracy and macro F1 with a confusion matrix, section micro and macro F1, per-section precision and recall, and exact-set-match rate on the held-out test split, writing `ml/artifacts/metrics.json` and a plot under `docs/`.
- `train.sh` and `train.bat` are the single commands that create the venv, install requirements, train and evaluate.
- The application loads artifacts only from `ml/artifacts/`. Any tool used to produce those files (including the team's own local ML training application, if used) must write the same files in the same formats; the application does not depend on how they were produced. If artifacts are missing the app fails with clear instructions, never silently falling back to another method.
- Section decision thresholds are chosen on the validation split and recorded in the model card. A site must always contain navbar, hero and footer regardless of predictions (documented rule).

**Rule-based parts (state this plainly in the docs):** slot extraction, theme selection from color and tone words, section ordering, the mandatory navbar/hero/footer rule, and content-bank selection. **Learned parts:** site type and section prediction only.

## Build plan (follow this order)

1. Project skeleton: Flask app factory, folders (`app/`, `site_templates/`, `content/`, `ml/`, `tests/`), `start.sh` and `start.bat` (create venv, install, run on port 5050), `.env.example`, pytest setup.
2. Template Library: section templates and at least 4 theme files with responsive CSS (flexbox/grid, media queries, viewport meta), plus the fixed script template (mobile menu toggle). Verify each section renders on its own.
3. Content bank for at least 5 site types.
4. Slot Extractor, Theme Engine and Component Assembler with unit tests.
5. Renderer / Exporter with escaping, validity checks and ZIP export.
6. ML pipeline: labeled prompts, `train.py`, `evaluate.py`, `train.sh`/`train.bat`, model card; integrate the classifiers into the Requirement Extractor.
7. Project Store and Flask routes (generate, preview, update, save, list, duplicate, delete, export, feedback, ml-info, eval).
8. Browser UI: Builder, Editor with live preview and device toggles, Projects, About the AI.
9. Evaluator and the About page wiring.
10. Polish pass, browser verification with screenshots, documentation.

## Development environment and tools

- Python 3.10+, one venv, pinned `requirements.txt`; `start.sh` (macOS/Linux) and `start.bat` (Windows) create the venv if missing, install, copy `.env.example`, and run the app on port 5050 (the app must also work with `python -m flask run` or `python app.py`).
- Suggested layout: `app/` (routes, modules), `app/templates/` (builder UI pages), `app/static/` (builder CSS/JS, local only), `site_templates/` (section and theme templates for generated sites), `content/`, `ml/`, `tests/`, `docs/`.
- Builder UI standard: a clean, modern, responsive interface with a full light and dark theme, a real app icon/favicon generated by the team, consistent type scale, and clear empty, loading and error states. System font stacks only. At least 4 pages: Builder, Editor with preview, Projects, About the AI.
- Generated-site quality standard: semantic HTML, a viewport meta tag, mobile-first CSS with breakpoints, accessible contrast in every palette, labelled form fields, alt text on any image placeholder, no external requests. Use CSS gradients or inline SVG shapes instead of external images.
- `.gitignore`: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.env`, `*.pyc`, the runtime SQLite file and exported ZIPs. Keep `ml/artifacts/` committed so the demo runs without retraining.

## Integration

- The builder UI talks to Flask routes in the same app; the live preview is served from a route that renders the current site model, so preview and export are produced by the same Renderer.
- A site model is a plain JSON structure (site type, theme, slots, ordered sections with content and visibility). The Editor edits this model and the Renderer is a pure function of it, which keeps saved projects reproducible.
- All user-supplied text is escaped by Jinja2 autoescaping; section templates must never use the `safe` filter on user data.
- The About page reads `/api/ml/info` and `/api/eval` and shows only measured values, never hardcoded numbers.

## Testing

- ML: run `train.sh` for real; confirm metrics, cross-validation scores and the evaluation are produced and recorded honestly in the model card.
- Slot Extractor: tests for names (quoted, "called X", "named X"), emails, phones, colors, tone words, and prompts that contain none.
- Assembler and Renderer: every site type renders with every section; output parses as valid HTML (use Python's `html.parser` or a similar local check), contains a viewport meta tag, `@media` rules and no external URLs; navbar, hero and footer are always present; hidden sections are absent; reordering is respected.
- Security: a prompt or edit containing `<script>alert(1)</script>` or HTML attributes appears escaped in the output and never executes; generated JavaScript equals the fixed template.
- Persistence and export: save, reopen, duplicate and delete a project; the exported ZIP contains the three files and renders offline.
- Performance: the Evaluator measures mean and 95th-percentile generation time over the held-out prompts.
- UI: drive the app in a real browser, read screenshots of Builder, Editor at desktop, tablet and mobile widths, Projects and About, and check that the preview matches the exported site.
- API: pytest tests with Flask's test client for every route, including error cases (empty prompt, over-long prompt, unknown project id).

Write and run tests appropriate to this stack as you build each module, not only at the end.

## Requirements Traceability

Every objective and functional requirement above must map to:

1. One or more implementation components or modules.
2. A defined verification or testing method.

Before considering the project complete, verify that every objective and functional requirement has:
- A corresponding implementation.
- A corresponding test or demonstrable verification method.
- An end-to-end path where applicable.

Do not mark an objective as complete merely because the related code or module exists - the required behavior must be demonstrably functional.

## Change Control

If implementation reveals that a requirement, technical decision, dependency, model, API, or architectural choice from this specification is technically infeasible:

1. Do not silently modify the requirement.
2. Identify the exact requirement or decision affected.
3. Explain the technical problem clearly.
4. Explain the impact on the current architecture or implementation.
5. Propose the smallest viable alternative, if one exists.
6. Clearly identify what would need to change.
7. Do not proceed with the alternative as though it were part of the original specification.

Preserve the original requirement until an approved change is made.

Recorded deviations from the source paper (already approved, document them in the README and Project Information doc): scikit-learn TF-IDF classifiers instead of transformer models, spaCy and Hugging Face; a template library with rule-based theme and layout selection instead of generative design models and reinforcement learning, so there is no reinforcement-learning component; a local Flask app with ZIP export instead of Flask or Django deployed on Vercel; SQLite and files instead of separate Template and Content databases; the paper's 83% accuracy, 81% satisfaction and 7.8-second figures are not claimed and are replaced by this project's own measurements.

## Known limitations to design around

The system selects, fills and styles pre-built templates; it does not invent new layouts or write free-form code, so the range of sites is limited to the supported site types and sections. Page copy comes from the team-written content bank and the user's own text, and is placeholder-quality until edited.

The classifiers are trained on team-written prompts, so measured accuracy reflects that style of prompt and is not general accuracy; prompts in other languages, very long prompts or requests outside the supported site types will be handled poorly, and the app should say when confidence is low. Rule-based slot extraction can miss unusual phrasings of a name or color.

The contact form in generated sites is static (it opens the visitor's mail client) because generated sites have no backend. There is no hosting, user account system, e-commerce or CMS. User ratings come from whoever tests the app, usually a small number of people, and the About page must show how many ratings the average rests on.

## Explicitly out of scope for this build

- Transformer, generative or reinforcement-learning models, and any hosted LLM or code-generation API.
- Multilingual prompts, e-commerce and CMS modules, third-party API and database integrations (listed as future work in the paper).
- Hosting or deploying generated sites (Vercel, Docker, cloud), custom domains, and user accounts.
- Image generation, stock photo search and any external asset loading.
- An in-app screen for retraining the models.

These are documented future enhancements, not part of this build - do not implement them now.

## Scope and Complexity Control

This is a final-year student project, not a production enterprise system. Prefer the simplest implementation that completely satisfies the requirements above.

Do not introduce, unless explicitly required by a Technical Constraint or Functional Requirement above:
- Microservices
- Message queues
- Separate backend services
- Authentication systems
- Databases beyond SQLite
- Cloud infrastructure
- Complex design patterns
- Additional abstraction layers
- Third-party services
- Advanced monitoring or deployment infrastructure

A smaller, complete, tested implementation is preferable to a larger implementation with unnecessary complexity or incomplete functionality.

## Definition of Done

The project is considered complete only when all of the following are true:

**Requirements**
- Every stated objective is implemented.
- Every functional requirement is implemented.
- No required feature is merely scaffolded or represented by a placeholder.
- No required functionality has been silently removed or substituted.

**Integration**
- The complete primary workflow (Functional Workflow above) works end-to-end.
- All required modules communicate correctly per their defined interfaces.
- Expected success and failure paths have been handled, including empty prompts, low-confidence predictions and the missing-artifact startup error.

**Testing**
- Appropriate unit tests exist for testable modules.
- Integration or end-to-end testing has been performed where applicable.
- Important error and edge cases have been tested.
- Tests pass in the final project state.

**Build & Execution**
- The project runs from a clean checkout with `start.sh` or `start.bat` on macOS, Linux and Windows without manual code patching, and with no internet access after installation.
- Required dependencies and configuration are documented.
- The project can be demonstrated using its intended workflow.

**Scope**
- No unnecessary features have been added.
- Explicitly out-of-scope functionality (above) has not been implemented.
- No generated or builder page makes any request to an external host.

**Documentation**
- Setup instructions are available (README with the start script first and manual steps second, Windows / macOS / Linux notes, and how to retrain with `train.sh` / `train.bat`).
- A screenshots table built from real browser captures under `docs/screenshots/` (Builder, Editor at three widths, Projects, About).
- A `Project Information - AI Website Builder.md` in the house template (Overview, Problem Statement, Core Implementation 1-8, Key Design Principles, Tech Stack Summary), honest about what is learned (the two classifiers), what is rule-based and what is template assembly, and listing every deviation under Change Control.
- Required configuration is documented.
- Important implementation limitations (Known Limitations above) are documented.
- `docs/architecture-briefing.html` regenerated after a clean review pass.
