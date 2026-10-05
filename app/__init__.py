"""AI Website Builder - Flask app factory."""
import os

from flask import Flask

from ml.predictor import ARTIFACT_DIR, ModelBundle

from .engine import Engine
from .store import Store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_dotenv(path=None):
    """Tiny .env reader (KEY=VALUE lines) so no extra dependency is needed. Existing env vars win."""
    path = path or os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def create_app(test_config=None):
    """Create the app. Raises ml.predictor.ArtifactError when the trained model files are missing."""
    load_dotenv()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    db = os.environ.get("AIWB_DB", os.path.join("data", "projects.sqlite3"))
    app.config.update(
        DATABASE=db if os.path.isabs(db) else os.path.join(ROOT, db),
        ARTIFACT_DIR=os.environ.get("AIWB_ARTIFACT_DIR") or ARTIFACT_DIR,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)
    models = ModelBundle.load(app.config["ARTIFACT_DIR"])      # fails loudly, no fallback
    app.extensions["aiwb"] = {"models": models, "engine": Engine(models), "store": Store(app.config["DATABASE"])}
    app.json.sort_keys = False
    from .routes import bp
    app.register_blueprint(bp)
    return app
