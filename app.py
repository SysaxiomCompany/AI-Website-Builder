"""Run the AI Website Builder:  python app.py   (default http://127.0.0.1:5050)."""
import os
import sys

from app import create_app, load_dotenv
from ml.predictor import ArtifactError

if __name__ == "__main__":
    load_dotenv()
    try:
        application = create_app()
    except ArtifactError as exc:
        print(f"\nCannot start: {exc}\n", file=sys.stderr)
        raise SystemExit(1)
    application.run(host=os.environ.get("AIWB_HOST", "127.0.0.1"),
                    port=int(os.environ.get("AIWB_PORT", "5050")), debug=False)
