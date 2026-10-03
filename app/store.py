"""Project Store: projects, edits and feedback in SQLite (stdlib sqlite3)."""
import json
import os
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    site_type TEXT NOT NULL,
    model_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS edits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class NotFound(LookupError):
    pass


class Store:
    def __init__(self, path):
        self.path = path
        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _project(row, with_model=True):
        d = {"id": row["id"], "name": row["name"], "prompt": row["prompt"], "site_type": row["site_type"],
             "created_at": row["created_at"], "updated_at": row["updated_at"]}
        if with_model:
            d["model"] = json.loads(row["model_json"])
        return d

    def create(self, name, prompt, model):
        now = _now()
        with self._conn() as c:
            cur = c.execute("INSERT INTO projects(name,prompt,site_type,model_json,created_at,updated_at) "
                            "VALUES (?,?,?,?,?,?)",
                            (name, prompt, model["site_type"], json.dumps(model), now, now))
            pid = cur.lastrowid
            c.execute("INSERT INTO edits(project_id,summary,created_at) VALUES (?,?,?)",
                      (pid, "created from prompt", now))
        return self.get(pid)

    def get(self, pid):
        with self._conn() as c:
            row = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if row is None:
            raise NotFound(pid)
        return self._project(row)

    def list(self):
        with self._conn() as c:
            rows = c.execute("SELECT p.*, f.rating AS rating FROM projects p "
                             "LEFT JOIN feedback f ON f.project_id = p.id "
                             "ORDER BY p.updated_at DESC, p.id DESC").fetchall()
        out = []
        for r in rows:
            d = self._project(r, with_model=False)
            d["rating"] = r["rating"]
            out.append(d)
        return out

    def update(self, pid, name, prompt, model, summary):
        now = _now()
        with self._conn() as c:
            cur = c.execute("UPDATE projects SET name=?, prompt=?, site_type=?, model_json=?, updated_at=? "
                            "WHERE id=?", (name, prompt, model["site_type"], json.dumps(model), now, pid))
            if cur.rowcount == 0:
                raise NotFound(pid)
            c.execute("INSERT INTO edits(project_id,summary,created_at) VALUES (?,?,?)", (pid, summary, now))
        return self.get(pid)

    def duplicate(self, pid):
        src = self.get(pid)
        out = self.create(src["name"][:70] + " (copy)", src["prompt"], src["model"])
        self.add_edit(out["id"], f"duplicated from project {pid}")
        return out

    def delete(self, pid):
        with self._conn() as c:
            cur = c.execute("DELETE FROM projects WHERE id=?", (pid,))
            if cur.rowcount == 0:
                raise NotFound(pid)

    def add_edit(self, pid, summary):
        with self._conn() as c:
            c.execute("INSERT INTO edits(project_id,summary,created_at) VALUES (?,?,?)", (pid, summary, _now()))

    def edits(self, pid):
        with self._conn() as c:
            rows = c.execute("SELECT summary, created_at FROM edits WHERE project_id=? ORDER BY id DESC",
                             (pid,)).fetchall()
        return [dict(r) for r in rows]

    def set_feedback(self, pid, rating, comment):
        self.get(pid)  # raises NotFound
        now = _now()
        with self._conn() as c:
            c.execute("INSERT INTO feedback(project_id,rating,comment,created_at) VALUES (?,?,?,?) "
                      "ON CONFLICT(project_id) DO UPDATE SET rating=excluded.rating, "
                      "comment=excluded.comment, created_at=excluded.created_at",
                      (pid, rating, comment, now))
        return self.get_feedback(pid)

    def get_feedback(self, pid):
        with self._conn() as c:
            row = c.execute("SELECT rating, comment, created_at FROM feedback WHERE project_id=?",
                            (pid,)).fetchone()
        return dict(row) if row else None

    def feedback_summary(self):
        with self._conn() as c:
            row = c.execute("SELECT COUNT(*) AS n, AVG(rating) AS avg FROM feedback").fetchone()
            dist = c.execute("SELECT rating, COUNT(*) AS n FROM feedback GROUP BY rating").fetchall()
        return {"count": row["n"], "average": round(row["avg"], 2) if row["n"] else None,
                "distribution": {str(i): 0 for i in range(1, 6)} | {str(r["rating"]): r["n"] for r in dist}}
