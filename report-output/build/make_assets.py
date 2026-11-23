"""Report-ready screenshots (credential footer cropped out) and terminal-style renderings of captured logs."""
import html, sys
from pathlib import Path
from PIL import Image
HERE = Path(__file__).parent; ROOT = HERE.parent
EV = ROOT / "evidence"; OUT = ROOT / "assets" / "screens"; OUT.mkdir(parents=True, exist_ok=True)

# 1) screenshots: copy unchanged, except the two login screenshots which are cropped above the demo-credential footer
for f in sorted((EV / "screenshots").glob("S0*.png")):
    im = Image.open(f).convert("RGB")
    if f.name.startswith(("S01", "S02")) and im.width > 1500:   # evidence copies are already cropped (credential footer removed)
        im = im.crop((660, 190, 1500, 760))
    im.save(OUT / f.name, optimize=True)

AFS = EV / "after-fixes" / "screenshots"
if AFS.exists():
    for f in sorted(AFS.glob("*.png")):
        Image.open(f).convert("RGB").save(OUT / f.name, optimize=True)
    a, b = Image.open(AFS / "S04b-attack-history-runA-skips.png").convert("RGB"), Image.open(AFS / "S04c-attack-history-runB-all-pass.png").convert("RGB")
    w = max(a.width, b.width); sheet = Image.new("RGB", (w, a.height + b.height + 24), "#ffffff")
    sheet.paste(a, (0, 0)); sheet.paste(b, (0, a.height + 24)); sheet.save(OUT / "S04bc-attack-history-after-fix.png", optimize=True)

# 2) terminal renderings of real captured text
def lines_of(path, a=None, b=None):
    t = Path(path).read_text().splitlines()
    return t[(a or 1) - 1:(b or len(t))]

JOBS = {
 "T1-functional-a": ("functional-flows.log", 1, 25, "evidence/functional-flows.log (excerpt: health, TLS, mTLS, logins)"),
 "T2-functional-b": ("functional-flows.log", 26, 56, "evidence/functional-flows.log (excerpt: orders, scopes, BOLA, admin API)"),
 "T3-functional-c": ("functional-flows.log", 57, 76, "evidence/functional-flows.log (excerpt: signature, injection data, validation)"),
 "T3b-functional-d": ("functional-flows.log", 77, 96, "evidence/functional-flows.log (excerpt: refresh, headers, TLS)"),
 "T5-tls-probe": ("tls-version-check.log", 1, 20, "evidence/tls-version-check.log"),
 "T7-pytest": ("pytest-resource-service.log", 1, 40, "evidence/pytest-resource-service.log"),
 "T8-loki": ("grafana-loki-diagnosis.log", 1, 60, "evidence/grafana-loki-diagnosis.log"),
 "T9-environment": ("environment.txt", 1, 22, "evidence/environment.txt (excerpt: host, containers, runtime versions)"),
 "T10-node-tests": ("after-fixes/node-tests-auth-server.log", 1, 40, "evidence/after-fixes/node-tests-auth-server.log"),
 "T11-lockout-retest": ("after-fixes/lockout-retest.log", 1, 40, "evidence/after-fixes/lockout-retest.log"),
 "T13-timing-retest": ("after-fixes/login-timing-retest.log", 1, 45, "evidence/after-fixes/login-timing-retest.log"),
}
WRAP = {"T5-tls-probe", "T6-timing-lockout", "T7-pytest", "T8-loki", "T9-environment", "T10-node-tests", "T11-lockout-retest", "T13-timing-retest", "T12-toolkit-retest"}

def term(name, path, a, b, title):
    ls = lines_of(EV / path, a, b)
    if name in WRAP:
        return name, title, ls
    return name, title, [l if len(l) <= 84 else l[:81] + "..." for l in ls]

import re as _re

def tidy(line):
    """Figures only: replace local scratch-folder paths with a neutral label. The raw evidence logs are not changed."""
    line = _re.sub(r"/private/tmp/claude-501/\S*?/scratchpad/run-copy", "<test copy>", line)
    return _re.sub(r"/private/tmp/claude-501/\S*?/scratchpad", "<scratch>", line)


def page(title, ls):
    ls = [tidy(l) for l in ls]
    body = html.escape("\n".join(ls))
    return f"""<html><body style="margin:0;background:#fff"><div style="width:690px;font-family:Menlo,Consolas,monospace;border:1px solid #888;border-radius:8px;overflow:hidden">
<div style="background:#e8e8e8;padding:7px 12px;font:12px Arial;color:#333;border-bottom:1px solid #bbb">{html.escape(title)}</div>
<pre style="margin:0;padding:10px 12px;background:#14171c;color:#d7dde5;font-size:12.4px;line-height:1.35;white-space:pre-wrap;word-break:break-all">{body}</pre></div></body></html>"""

if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    # extra composite logs
    comb = []
    comb += ["$ python3 run_all.py   # stock runner, as shipped"] + [l for l in lines_of(EV / "attacker-toolkit-run1.log") if "COMBINED" in l or l.strip().startswith(("PASS", "FAIL", "SOME", "ERROR", "NOTE", "Report"))][:20]
    (EV / "_tmp_stock.txt").write_text("\n".join(comb))
    jobs = [term(n, *v) for n, v in JOBS.items()]
    jobs.append(("T4-stock-runner", "evidence/attacker-toolkit-run1.log (excerpt: combined result of the stock run_all.py)", [l if len(l) <= 84 else l[:81] + "..." for l in comb]))
    # excerpt of the two re-run toolkit logs (lines copied unchanged)
    keep = lambda t: [l for l in t if any(k in l for k in ("NOTE:", "[SKIPPED", "(HMAC key obtained", "(public key obtained", "COMBINED RESULTS", "  PASS  ", "  SKIP  ", "  FAIL  ", "ALL ATTACKS", "NO ATTACK", "SOME ATTACKS", "exit code", "Report uploaded", "attacks blocked"))]
    t12 = ["$ python3 run_all.py            # RUN A: no key files, no VAULT_TOKEN"] + keep(lines_of(EV / "after-fixes/attacker-toolkit-runA-no-keys.log")) + ["", "$ VAULT_TOKEN=<read token> python3 run_all.py   # RUN B"] + keep(lines_of(EV / "after-fixes/attacker-toolkit-runB-with-vault-token.log"))
    jobs_extra = [("T12-toolkit-retest", "evidence/after-fixes/attacker-toolkit-runA-no-keys.log and ...runB-with-vault-token.log (excerpts)", t12)]
    t6 = lines_of(EV / "login-timing.log") + [""] + lines_of(EV / "lockout-after-bruteforce.log")
    jobs += jobs_extra
    jobs.append(("T6-timing-lockout", "evidence/login-timing.log and lockout-after-bruteforce.log", t6))
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, title, ls in jobs:
            ctx = b.new_context(viewport={"width": 720, "height": 400}, device_scale_factor=2.4)
            pg = ctx.new_page(); pg.set_content(page(title, ls))
            el = pg.query_selector("div"); el.screenshot(path=str(OUT / f"{name}.png")); ctx.close()
        b.close()
    (EV / "_tmp_stock.txt").unlink()
    print("assets:", len(list(OUT.glob("*.png"))))
