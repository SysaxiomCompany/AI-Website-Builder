"""JS-level test of the editor's move logic (runs the real functions from editor.js under node)."""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def run(order, hidden, i, d):
    src = open(os.path.join(ROOT, "app/static/js/editor.js"), encoding="utf-8").read()
    a = src.index("  function move(i, d) {")
    b = src.index("  function addSection")
    code = ("var state={model:{sections:%s}};function renderSections(){}function changed(){}\n%s\n"
            "move(%d,%d);console.log(JSON.stringify(state.model.sections.map(function(s){return s.type})));"
            % (json.dumps([{"type": t, "visible": t not in hidden} for t in order]), src[a:b], i, d))
    return json.loads(subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout)


ORDER = ["navbar", "hero", "about", "features", "gallery", "faq", "footer"]


def test_move_skips_hidden_neighbour():
    # gallery is hidden: moving faq up swaps with features (the nearest visible), not with gallery
    out = run(ORDER, {"gallery"}, 5, -1)
    assert out.index("faq") < out.index("features") and out[0] == "navbar" and out[-1] == "footer"
    assert out.index("faq") == out.index("features") - 1


def test_move_down_skips_hidden_and_visible_order_changes():
    out = run(ORDER, {"features"}, 2, 1)           # about down: skips hidden features, passes gallery
    visible = [t for t in out if t != "features"]
    assert visible == ["navbar", "hero", "gallery", "about", "faq", "footer"]


def test_move_never_passes_navbar_or_footer_or_nothing_visible():
    assert run(ORDER, {"about", "features", "gallery", "faq"}, 1, 1) == ORDER      # nothing visible to swap with
    assert run(ORDER, set(), 1, -1) == ORDER                                       # hero cannot go above navbar
    assert run(ORDER, set(), 5, 1) == ORDER                                        # faq cannot go below footer
