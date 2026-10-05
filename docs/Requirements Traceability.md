# Requirements Traceability

Every objective and functional requirement of the specification, the module that implements it, and the verification. Tests are in `tests/`; browser checks are `scripts/capture_screenshots.py` with its output in `docs/screenshots/`.

| Requirement | Implementation | Verification |
|---|---|---|
| **O1** Accept a description; extract site type and sections (trained classifiers) plus name, tagline, contact, colors (rules) | `app/preprocess.py`, `ml/predictor.py`, `ml/train.py`, `app/slots.py`, `app/extractor.py`, `app/engine.py` | `test_ml_and_data.py` (artifacts, predictions, section requests), `test_preprocess_slots.py`, `test_api.py::test_generate_returns_requirements_and_project` |
| **O2** Assemble a complete responsive site from templates, content banks and themes; live preview at three widths | `app/assembler.py`, `site_templates/`, `content/`, `app/renderer.py`, `app/templates/editor.html`, `editor.js` | `test_assembler_renderer.py` (every type x every section, viewport, `@media`, no external URL), `test_theme.py` (contrast), screenshots `editor-*`, `editor-preview-*` |
| **O3** Customize (text, sections, theme, fonts), save projects, export an offline ZIP | `app/routes.py`, `app/store.py`, `app/sitemodel.py`, `editor.js` | `test_api.py` (CRUD, export zip, add-section), `test_store.py`, capture script (live edit shows in preview, exported site shows the edit from `file://`) |
| **O4** Measure and display accuracy (5-fold CV, held-out), generation time, user ratings | `ml/evaluate.py`, `ml/artifacts/*`, `/api/ml/info`, `/api/eval`, `/api/feedback/summary`, `about.js` | `test_ml_and_data.py::test_metrics_json_has_every_spec_metric`, `test_api.py::test_meta_ml_info_and_eval`, `test_pages_and_docs.py::test_about_page_has_no_hardcoded_measurements`, `about.png` |
| **F1** Prompt-to-website generation showing extracted requirements | `/api/generate`, `builder.js` ("How I understood your request") | `test_api.py` generate tests, `builder-result.png` |
| **F2** Requirement extraction: classifiers + rules, low-confidence statement | `ml/predictor.py`, `app/slots.py`, `app/extractor.py` | `test_preprocess_slots.py`, `test_api.py::test_low_confidence_prompts_are_flagged_not_silent`, `test_ml_and_data.py::test_out_of_distribution_inputs_are_flagged`, `builder-low-confidence.png` |
| **F3** Component assembly: 10 section templates, >= 5 site types | `site_templates/sections/*`, `content/*.json`, `app/assembler.py` | `test_assembler_renderer.py` |
| **F4** Theme engine: palettes and system font stacks, switchable | `app/theme.py`, `site_templates/themes`, `fonts` | `test_theme.py`, editor Theme tab |
| **F5** Live preview with device toggles | `/api/preview`, `/preview/<id>`, sandboxed iframe | `test_api.py::test_preview_post_and_get`, `editor-preview-tablet.png`, `editor-preview-mobile.png` |
| **F6** Editor: edit text, show/hide, reorder, theme, regenerate | `editor.js`, `/api/projects/<id>` PUT, `/regenerate`, `/api/model/add-section` | `test_assembler_renderer.py` (hidden, reorder), `test_api.py` (update, regenerate, add-section), capture script |
| **F7** Projects: save, reopen, duplicate, delete in a local database | `app/store.py`, `projects.js` | `test_store.py`, `test_api.py`, `projects.png`, `projects-empty.png` |
| **F8** Export a ZIP with `index.html`, `style.css`, `script.js` that works offline | `app/renderer.py::build_zip` | `test_api.py::test_export_zip_contents_and_offline_rendering`, `exported-site-*.png` |
| **F9** Safe output: escaped user text, fixed JavaScript | Jinja2 autoescape, `app/sitemodel.py`, fixed `script.js` | `test_security.py`, `test_assembler_renderer.py::test_templates_never_use_safe_filter` |
| **F10** Feedback and the About page | `/api/projects/<id>/feedback`, `/api/feedback/summary`, `about.js` | `test_api.py::test_feedback_flow`, `test_feedback_validation`, `about.png` |
| Missing artifacts -> clear startup error, no fallback | `ml/predictor.py::ModelBundle.load`, `app.py` | `test_ml_and_data.py::test_missing_artifacts_fail_loudly_with_instructions` and two related tests |
| No external requests (builder and generated sites) | local assets only | `test_pages_and_docs.py::test_no_external_urls_*`, `test_assembler_renderer.py`, `docs/test-evidence/browser-external-requests.txt` |
| Docs match code (port, threshold, measured values) | README, Project Information | `test_pages_and_docs.py::test_docs_match_code_defaults` |
