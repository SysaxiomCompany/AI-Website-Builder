"""Capture real browser screenshots of the running app into docs/screenshots/ (development helper).

Needs the app running (python app.py) and:  pip install playwright   (uses the installed Google Chrome,
no browser download).  Usage:  python scripts/capture_screenshots.py [base_url]
Start from an empty database so the empty states are captured too.
"""
import io
import os
import re
import sys
import tempfile
import zipfile

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5050"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots")
PROMPTS = [
    "A modern website for my bakery called Sweet Crumbs with a menu, gallery and contact form. Email "
    "hello@sweetcrumbs.example, based in Austin. Use warm orange colors.",
    "Portfolio for a freelance photographer named Maya Lin with a photo gallery and pricing, in dark colors",
    "A friendly site for a coding bootcamp with course listings, FAQ and student reviews",
]


def goto(page, path, theme):
    page.goto(BASE + path)
    page.evaluate("t => { localStorage.setItem('aiwb-theme', t); document.documentElement.setAttribute('data-theme', t); }", theme)
    page.wait_for_load_state("networkidle")


def shot(page, name, full=False):
    page.wait_for_timeout(400)
    if full:   # grow the viewport instead of full_page so the sticky header is not drawn mid-page
        h = page.evaluate("document.documentElement.scrollHeight")
        w = page.viewport_size["width"]
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(OUT, name))
        page.set_viewport_size({"width": w, "height": 900})
    else:
        page.screenshot(path=os.path.join(OUT, name))
    print("saved", name)


def main():
    os.makedirs(OUT, exist_ok=True)
    external = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("request", lambda r: external.append(r.url) if not r.url.startswith((BASE, "data:", "about:", "blob:", "file://")) else None)

        for theme, suffix in (("light", ""), ("dark", "-dark")):
            page.set_viewport_size({"width": 1440, "height": 900})
            goto(page, "/projects", theme)
            if not suffix:
                shot(page, "projects-empty.png")
            goto(page, "/", theme)
            if not suffix:
                shot(page, "builder-empty.png")
            # first generation: the good bakery prompt
            page.fill("#prompt", PROMPTS[0])
            page.click("#generate-btn")
            page.wait_for_selector("#result:not([hidden])")
            shot(page, f"builder-result{suffix}.png", full=True)
            if not suffix:
                page.fill("#prompt", "asdf qwerty")
                page.click("#generate-btn")
                page.wait_for_selector("#low-conf:not([hidden])")
                shot(page, "builder-low-confidence.png", full=True)
                # the other two projects
                for text in PROMPTS[1:]:
                    page.fill("#prompt", text)
                    page.click("#generate-btn")
                    page.wait_for_timeout(500)
            goto(page, "/projects", theme)
            page.wait_for_selector(".project-card")
            shot(page, f"projects{suffix}.png")
            goto(page, "/about", theme)
            page.wait_for_selector("#score-table tbody tr")
            shot(page, f"about{suffix}.png", full=True)

        ids = page.evaluate("fetch('/api/projects').then(r => r.json()).then(d => d.projects.map(p => [p.id, p.name, p.prompt]))")
        bakery = [i for i, n, pr in ids if pr.startswith("A modern website for my bakery")][0]

        # editor at three viewport widths (desktop, tablet, mobile)
        for theme, suffix in (("light", ""), ("dark", "-dark")):
            for label, w, h in (("desktop", 1440, 900), ("tablet", 820, 1100), ("mobile", 390, 844)):
                if suffix and label != "desktop":
                    continue
                page.set_viewport_size({"width": w, "height": h})
                goto(page, f"/editor/{bakery}", theme)
                page.wait_for_selector("#section-list .section-item")
                if label != "desktop":
                    shot(page, f"editor-{label}-edit.png")
                    page.click("#tab-preview")
                page.wait_for_selector("#preview")
                page.wait_for_function("document.getElementById('frame-loading').hidden === true")
                if label == "desktop":
                    page.click("#section-list .section-item:nth-child(3) .name")      # open the hero editor
                shot(page, f"editor-{label}{suffix}.png")

        # device toggles inside the desktop editor
        page.set_viewport_size({"width": 1440, "height": 900})
        goto(page, f"/editor/{bakery}", "light")
        page.wait_for_function("document.getElementById('frame-loading').hidden === true")
        for dev in ("tablet", "mobile"):
            page.click(f'.device-toggle button[data-w="{dev}"]')
            shot(page, f"editor-preview-{dev}.png")
        page.click('.device-toggle button[data-w="desktop"]')

        # a text edit shows up in the live preview, theme switch, then save
        page.click("#section-list .section-item:nth-child(3) .name")
        page.fill("#section-list .section-item:nth-child(3) input[type=text]", "Edited headline from the editor")
        page.wait_for_timeout(700)
        txt = page.frame_locator("#preview").locator("h1").inner_text()
        assert txt == "Edited headline from the editor", txt
        page.click("#save-btn")
        page.wait_for_selector("#dirty-badge", state="hidden")
        print("live edit visible in preview and saved")

        # export: preview vs exported site opened from file://
        resp = ctx.request.get(f"{BASE}/api/projects/{bakery}/export")
        z = zipfile.ZipFile(io.BytesIO(resp.body()))
        tmp = tempfile.mkdtemp()
        z.extractall(tmp)
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto("file://" + os.path.join(tmp, "index.html"))
        shot(page, "exported-site-desktop.png")
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto("file://" + os.path.join(tmp, "index.html"))
        shot(page, "exported-site-mobile.png")
        page.click(".nav-toggle")
        shot(page, "exported-site-mobile-menu.png")
        exported_h1 = page.locator("h1").inner_text()
        assert exported_h1 == "Edited headline from the editor", exported_h1
        browser.close()
    print("external requests seen:", external or "none")
    with open(os.path.join(os.path.dirname(OUT), "test-evidence", "browser-external-requests.txt"), "w") as f:
        f.write("External (non-localhost, non-data) requests observed while capturing screenshots of all pages "
                "and the exported site:\n" + ("\n".join(external) if external else "none") + "\n")


if __name__ == "__main__":
    main()
