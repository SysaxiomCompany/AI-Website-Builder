import pytest

from app.assembler import assemble
from app.store import NotFound, Store
from ml.predictor import SECTIONS


@pytest.fixture()
def store(tmp_path):
    return Store(str(tmp_path / "s.sqlite3"))


def make_model(name="X"):
    return assemble({"site_type": "blog", "sections": SECTIONS,
                     "slots": {"name": name, "tagline": "", "email": "", "phone": "", "location": "",
                               "colors": [], "tones": []}}, prompt="p")


def test_save_reopen_duplicate_delete(store):
    p = store.create("One", "prompt", make_model("One"))
    assert store.get(p["id"])["model"]["slots"]["name"] == "One"
    assert [x["id"] for x in store.list()] == [p["id"]]
    d = store.duplicate(p["id"])
    assert d["id"] != p["id"] and d["name"] == "One (copy)" and d["model"] == p["model"]
    store.delete(p["id"])
    assert [x["id"] for x in store.list()] == [d["id"]]
    with pytest.raises(NotFound):
        store.get(p["id"])
    with pytest.raises(NotFound):
        store.delete(p["id"])


def test_update_logs_edits(store):
    p = store.create("One", "prompt", make_model())
    store.update(p["id"], "Two", "prompt", make_model("Two"), "site name")
    assert store.get(p["id"])["name"] == "Two"
    assert [e["summary"] for e in store.edits(p["id"])][:2] == ["site name", "created from prompt"]
    with pytest.raises(NotFound):
        store.update(999, "x", "p", make_model(), "s")


def test_feedback_upsert_summary_and_cascade(store):
    a = store.create("A", "p", make_model())
    b = store.create("B", "p", make_model())
    assert store.feedback_summary()["count"] == 0 and store.feedback_summary()["average"] is None
    store.set_feedback(a["id"], 5, "great")
    store.set_feedback(b["id"], 2, "")
    store.set_feedback(b["id"], 3, "better")          # replaces, not a second rating
    s = store.feedback_summary()
    assert s["count"] == 2 and s["average"] == 4.0 and s["distribution"]["5"] == 1 and s["distribution"]["3"] == 1
    assert store.get_feedback(b["id"])["comment"] == "better"
    store.delete(a["id"])
    assert store.feedback_summary()["count"] == 1
    with pytest.raises(NotFound):
        store.set_feedback(12345, 4, "")
