import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app  # noqa: E402
from ml.predictor import ModelBundle  # noqa: E402


@pytest.fixture(scope="session")
def models():
    return ModelBundle.load()


@pytest.fixture()
def app(tmp_path):
    return create_app({"DATABASE": str(tmp_path / "test.sqlite3"), "TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def project(client):
    r = client.post("/api/generate", json={"prompt": "A modern website for my bakery called Sweet Crumbs with a "
                                                     "menu, gallery and contact form"})
    assert r.status_code == 201
    return r.get_json()["project"]
