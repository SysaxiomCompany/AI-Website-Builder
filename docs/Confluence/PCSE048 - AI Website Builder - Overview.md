# PCSE048 - AI Website Builder

# 📋 Project Information

| **Field** | **Value** |
| --- | --- |
| **Project ID** | PCSE048 |
| **Version** | v1.0 |
| **Project Name** | AI Website Builder |
| **Alternative Names** | Prompt-to-Website Generator; AI-Assisted Site Builder; Smart Website Scaffolder |
| **Department** | CSE |
| **Domain** | Web Development / Natural Language Processing |
| **Category** | Artificial Intelligence |
| **Status** | ✅ Approved |
| **Recommendation** | 👍 Recommended |
| **Overall Score** | 7.8 / 10 |
| **Difficulty** | 🟡 Medium |
| **Student Level** | Beginner – Intermediate |

---

# ⚖️ Simplification Strategy

| **Research Paper** | **Student Project Implementation** | **Reason for the Change** |
| --- | --- | --- |
| Interprets free-text user requirements using transformer-based NLP (spaCy, Hugging Face models) | Two lightweight scikit-learn classifiers (TF-IDF + logistic regression for site type, one-vs-rest logistic regression for sections) | Training and serving transformer models requires GPU resources and large labelled datasets that a student team does not have access to within one semester |
| Generates layouts with generative design models and uses reinforcement learning to optimize content placement and design aesthetics | A fixed library of hand-written responsive section templates selected and ordered by simple per-type rules | Training a generative layout model or an RL policy needs extensive compute and a reward-labelled dataset, neither feasible for an undergraduate in one semester |
| Implies large benchmark/template datasets for training the NLP and layout components | A small, hand-built and hand-labeled training and evaluation prompt set created by the team itself | No public labelled dataset of natural-language-to-website-section mappings exists, so the team must construct its own small-scale equivalent |
| Flask/Django backend containerized and deployed on Vercel | A single local Flask app with SQLite storage and ZIP export, run entirely on localhost | Setting up and maintaining cloud deployment infrastructure is unnecessary overhead for a single-user academic demo and adds no value to the core contribution |

---

# ✅ Why This Project Was Approved

- Fully buildable in one semester using lightweight scikit-learn classifiers and hand-written rule-based templates, with no GPU training or large datasets required
- Produces a strong, interactive live demo: a user types a short description and immediately sees a themed, multi-section responsive website previewed and exportable as a ZIP
- Runs entirely software-only on localhost, with no external hardware, cloud services, or internet dependency at runtime
- Fits naturally as a browser-based AI tool with a genuine, clearly demonstrable user-facing surface

---

# ⚠️ Key Challenges

- Hand-labeling a training and evaluation prompt set large and varied enough for the two classifiers to generalize beyond the exact examples written by the team
- Building a sufficiently broad template/content bank across six site types so generated sites look visually distinct rather than repetitive
- Keeping regex/word-list based slot extraction (name, contact, theme) robust to varied natural-language phrasing without turning it into an unmanageable rule set
- Being transparent in documentation and viva that transformer-based NLP and the generative/RL layout engine from the paper are replaced by simpler classifiers and static templates

---

# 📊 Project Decision Summary

| **Criteria** | **Assessment** |
| --- | --- |
| Research Alignment | ⭐⭐⭐⭐ |
| Ease of Implementation | ⭐⭐⭐⭐ |
| Student Friendly | ⭐⭐⭐⭐ |
| Demonstration Quality | ⭐⭐⭐⭐ |
| Innovation | ⭐⭐⭐ |
| Industry Relevance | ⭐⭐⭐⭐ |
| Current Trend | ⭐⭐⭐⭐ |
| Learning Value | ⭐⭐⭐⭐ |
| Overall Verdict | ✅ Recommended |

---

# 🔎 Search Tags

```
PCSE048, AI Website Builder, CSE, Web Development / Natural Language Processing, Artificial Intelligence, Local Python Flask web application (browser UI, single-user, localhost only), Python 3.11+, Flask, Jinja2, vanilla HTML/CSS/JavaScript, scikit-learn (TF-IDF, logistic regression, one-vs-rest), pandas, numpy, joblib, Python regular expressions and word lists (slot extraction, theme selection), SQLite (sqlite3), zipfile (Python standard library), pytest; Playwright/Chrome for browser capture (development only), Final Year Project
```
