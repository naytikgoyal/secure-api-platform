"""Charts drawn from measured data (evidence/*.log) and from the verified reference list."""
from collections import Counter
from svgkit import Canvas
from refs_data import REFS


def hbars(c, x0, y0, rows, scale, bar_h=26, gap=14, label_w=210, maxw=None, colors=None, size=14, value_fmt="{:g}"):
    for i, (lab, val) in enumerate(rows):
        y = y0 + i * (bar_h + gap)
        c.text(x0 + label_w - 10, y + bar_h / 2, lab, size, anchor="end")
        col = (colors or {}).get(lab, "blue")
        c.box(x0 + label_w, y, max(val * scale, 3), bar_h, "", col, rx=3, lw=1.3)
        c.text(x0 + label_w + val * scale + 8, y + bar_h / 2, value_fmt.format(val), size, anchor="start", bold=True)


def chart_timing():
    c = Canvas(820, 430)
    c.text(410, 22, "Time to answer a wrong-password login (milliseconds)", 17, bold=True)
    ex = [132.9, 121.8, 128.9, 142.3]
    un = [7.4, 8.3, 10.8, 16.3]
    x0, y0, h = 140, 50, 280  # plot: y for 0 at y0+h, 160 ms at y0
    sc = h / 160.0
    for v in range(0, 161, 40):
        y = y0 + h - v * sc
        c.line([(x0, y), (780, y)], None, arrow=False, color="#dddddd", lw=1)
        c.text(x0 - 8, y, str(v), 13, anchor="end")
    c.line([(x0, y0), (x0, y0 + h)], None, arrow=False, lw=1.6)
    c.line([(x0, y0 + h), (780, y0 + h)], None, arrow=False, lw=1.6)
    for cx, vals, lab, col in ((330, ex, "Existing user\n(rishi)", "orange"), (590, un, "Unknown user\n(no-such-user-N)", "green")):
        m = sum(vals) / len(vals)
        c.box(cx - 55, y0 + h - m * sc, 110, m * sc, "", col, rx=3)
        c.text(cx, y0 + h - max(m, max(vals)) * sc - 26, f"mean {m:.1f} ms", 14, bold=True)
        for k, v in enumerate(vals):
            c.circle(cx - 33 + k * 22, y0 + h - v * sc, 5, "", "white")
        c.text(cx, y0 + h + 32, lab, 14, lh=17)
    c.text(410, 414, "Four samples per username, alternating; dots are individual requests (evidence/login-timing.log)", 12, italic=True)
    return c


def chart_ratelimit():
    c = Canvas(820, 250)
    c.text(410, 22, "130 authenticated requests from one user inside one minute", 17, bold=True)
    x0, w = 30, 760
    c.box(x0, 70, w * 100 / 130, 56, "100 x HTTP 200", "green", size=17, bold=True, rx=3)
    c.box(x0 + w * 100 / 130, 70, w * 30 / 130, 56, "30 x HTTP 429", "red", size=17, bold=True, rx=3)
    xm = x0 + w * 100 / 130
    c.line([(xm, 62), (xm, 146)], None, arrow=False, color="#222", dashed=True, lw=2)
    c.text(xm, 164, "configured limit: 100 requests per minute", 14, bold=True)
    c.text(410, 220, "Observed with 130 consecutive GET /orders calls (evidence/functional-flows.log and Loki query log)", 12, italic=True)
    return c


def chart_results():
    c = Canvas(820, 500)
    c.text(410, 22, "Checks executed against the running system, by stage (all passed)", 17, bold=True)
    rows = [
        ("Unit tests: Resource Service", 17), ("Unit tests: Auth Server", 9), ("Live functional flows", 19),
        ("Replay script", 2), ("Token-forgery script", 3), ("Brute-force script", 2),
        ("Injection script", 18), ("TLS-downgrade script", 3),
    ]
    cols = {"Unit tests: Resource Service": "blue", "Unit tests: Auth Server": "blue", "Live functional flows": "yellow"}
    for r in rows[3:]:
        cols[r[0]] = "red"
    hbars(c, 20, 50, rows, 28, colors=cols, label_w=230)
    c.box(20, 362, 780, 118, "", "grey", lw=1.2)
    c.text(34, 384, "Stock run_all.py before the fixes: 3 scripts passed, 2 reported FAIL (missing key file, lockout).", 13.5, anchor="start", bold=True)
    c.text(34, 408, "After the fixes it fetches the keys from Vault with a read token, runs brute force last and", 13, anchor="start")
    c.text(34, 428, "reports an unavailable key as SKIP. With only a Vault token: 28 of 28 attacker checks pass, exit code 0.", 13, anchor="start")
    c.text(34, 456, "Unit tests: 17 existing + 9 new for the Auth Server = 26.", 13, anchor="start")
    return c


def chart_lit_type():
    names = {"rfc": "IETF RFCs", "nist": "NIST publications", "owasp": "OWASP", "cwe": "MITRE CWE entries", "journal": "Journal articles", "conf": "Conference papers", "book": "Books and chapters", "web": "Vendor, agency, web"}
    cnt = Counter(r["type"] for r in REFS)
    rows = sorted(((names[k], v) for k, v in cnt.items()), key=lambda t: -t[1])
    assert sum(v for _, v in rows) == len(REFS)
    c = Canvas(820, 100 + len(rows) * 40)
    c.text(410, 22, "Verified sources by type (n = 37)", 17, bold=True)
    hbars(c, 30, 50, rows, 50, label_w=210)
    return c


def chart_lit_year():
    def bucket(y):
        if y is None:
            return "undated web page"
        if y <= 1999:
            return "up to 1999"
        if y <= 2009:
            return "2000-2009"
        if y <= 2014:
            return "2010-2014"
        if y <= 2019:
            return "2015-2019"
        if y <= 2023:
            return "2020-2023"
        return "2024-2026"
    order = ["up to 1999", "2000-2009", "2010-2014", "2015-2019", "2020-2023", "2024-2026", "undated web page"]
    cnt = Counter(bucket(r["year"]) for r in REFS)
    assert sum(cnt.values()) == len(REFS)
    c = Canvas(820, 380)
    c.text(410, 22, "Verified sources by publication period (n = 37)", 17, bold=True)
    x0, y0, h = 60, 50, 250
    sc = h / 10.0
    for v in range(0, 11, 2):
        y = y0 + h - v * sc
        c.line([(x0, y), (790, y)], None, arrow=False, color="#dddddd", lw=1)
        c.text(x0 - 8, y, str(v), 13, anchor="end")
    c.line([(x0, y0 + h), (790, y0 + h)], None, arrow=False, lw=1.6)
    bw = 70
    for i, k in enumerate(order):
        v = cnt.get(k, 0)
        cx = x0 + 55 + i * 100
        c.box(cx - bw / 2, y0 + h - v * sc, bw, v * sc, "", "grey" if k.startswith("undated") else "blue", rx=3)
        c.text(cx, y0 + h - v * sc - 12, str(v), 15, bold=True)
        c.text(cx, y0 + h + 22, k.replace(" web page", "\nweb page") if k.startswith("undated") else k, 12.5, lh=15)
    return c


def chart_timing_fix():
    c = Canvas(820, 450)
    c.text(410, 22, "Wrong-password login time, before and after the fix (milliseconds)", 17, bold=True)
    groups = [
        (170, "Before the fix", "(4 samples each, means)", [("Existing user", 131.5, [132.9, 121.8, 128.9, 142.3], "orange"), ("Unknown user", 10.7, [7.4, 8.3, 10.8, 16.3], "green")]),
        (560, "After the fix", "(8 samples each, medians)", [("Existing user", 56.5, [54, 55, 56, 56, 57, 60, 95, 95], "orange"), ("Unknown user", 56.0, [54, 55, 55, 56, 56, 57, 58, 59], "green")]),
    ]
    x0, y0, h = 80, 50, 290
    sc = h / 160.0
    for v in range(0, 161, 40):
        y = y0 + h - v * sc
        c.line([(x0, y), (790, y)], None, arrow=False, color="#dddddd", lw=1)
        c.text(x0 - 8, y, str(v), 13, anchor="end")
    c.line([(x0, y0), (x0, y0 + h)], None, arrow=False, lw=1.6)
    c.line([(x0, y0 + h), (790, y0 + h)], None, arrow=False, lw=1.6)
    for gx, title, sub, bars in groups:
        for k, (lab, val, pts, col) in enumerate(bars):
            cx = gx - 70 + k * 140
            c.box(cx - 45, y0 + h - val * sc, 90, val * sc, "", col, rx=3)
            for j, v in enumerate(pts):
                c.circle(cx - 36 + j * (72 / max(len(pts) - 1, 1)), y0 + h - v * sc, 4.5, "", "white")
            c.text(cx, y0 + h - max(val, max(pts)) * sc - 18, f"{val:g} ms", 14, bold=True)
            c.text(cx, y0 + h + 20, lab, 13.5)
        c.text(gx, y0 + h + 52, title, 15, bold=True)
        c.text(gx, y0 + h + 72, sub, 12.5, color="#444")
    c.text(410, 438, "Dots are individual requests. The two 95 ms samples were each the first request of a round, after a minute idle.", 12, italic=True)
    return c


JOBS = {
    "fig-chart-timing": chart_timing,
    "fig-chart-timing-fix": chart_timing_fix,
    "fig-chart-ratelimit": chart_ratelimit,
    "fig-chart-results": chart_results,
    "fig-chart-lit-type": chart_lit_type,
    "fig-chart-lit-year": chart_lit_year,
}
