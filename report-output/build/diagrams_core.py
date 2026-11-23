"""Core architecture diagrams (original drawings based on the verified repository architecture)."""
from svgkit import Canvas, sequence


def num(c, x, y, n):
    c.circle(x, y, 11, str(n), "white", size=13)


def architecture():
    c = Canvas(820, 640)
    c.zone(160, 40, 250, 330, "DMZ (internet-facing)", "yellow")
    c.zone(450, 40, 360, 430, "Internal zone (zero trust)", "green")
    c.box(10, 170, 115, 80, "Clients", "white", bold=True, sub="browser, curl,\nPostman")
    c.box(10, 310, 115, 64, "Attacker\ntoolkit", "red", size=15)
    c.box(180, 78, 210, 64, "Auth Server", "yellow", bold=True, sub="Node.js / Express")
    c.box(180, 215, 210, 84, "API Gateway", "yellow", bold=True, sub="Node.js / Express")
    c.box(470, 215, 150, 84, "Resource Service", "green", bold=True, sub="Python / FastAPI")
    c.cylinder(680, 205, 110, 104, "PostgreSQL", "blue", sub="orders table")
    c.cylinder(470, 345, 120, 90, "Redis", "blue", sub="limits, nonces")
    c.cylinder(480, 78, 150, 72, "Vault", "purple", sub="JWT, HMAC, DB creds")
    c.box(180, 432, 210, 56, "Loki · Promtail · Grafana", "grey", size=15)
    # flows
    c.line([(125, 195), (152, 195), (152, 110), (180, 110)])
    num(c, 152, 152, 1)
    c.line([(125, 225), (152, 225), (152, 247), (180, 247)])
    num(c, 152, 236, 2)
    c.line([(125, 342), (152, 342), (152, 275), (180, 275)], dashed=True, color="#b3261e")
    c.text(10, 396, "only reaches the system\nthrough the Gateway", 12, anchor="start", color="#b3261e")
    c.line([(390, 257), (470, 257)])
    num(c, 430, 257, 3)
    c.line([(620, 257), (680, 257)])
    num(c, 650, 257, 4)
    c.line([(230, 299), (230, 390), (470, 390)])
    num(c, 420, 390, 5)
    c.line([(545, 299), (545, 345)])
    num(c, 545, 322, 6)
    c.line([(390, 112), (480, 112)], dashed=True)
    num(c, 435, 112, 7)
    c.line([(390, 235), (432, 235), (432, 168), (520, 168), (520, 152)], dashed=True)
    c.line([(570, 215), (570, 152)], dashed=True)
    c.line([(330, 370), (330, 432)], dashed=True)
    num(c, 330, 414, 8)
    leg = [
        "1  Login over HTTPS (username, password)",
        "2  API call over HTTPS with Bearer JWT",
        "3  mTLS + HMAC signature + nonce + timestamp",
        "4  Parameterised SQL as the least-privilege role",
        "5  Rate-limit counters (Gateway, Auth Server)",
        "6  Nonce reservation (SET NX EX 300)",
        "7  Secrets read once at start-up (dashed)",
        "8  Structured JSON logs scraped by Promtail",
    ]
    for i, t in enumerate(leg):
        c.text(440 if i % 2 else 30, 520 + (i // 2) * 28, t, 14, anchor="start")
    c.items[-8:] = c.items[-8:]  # no-op, keeps order explicit
    return c


def trust_boundaries():
    c = Canvas(820, 430)
    c.box(8, 80, 150, 170, "", "red", dashed=True)
    c.text(83, 100, "Untrusted", 16, bold=True, color="#b3261e")
    c.text(83, 170, "Browser, curl,\nPostman,\nattacker toolkit", 15)
    c.box(236, 80, 180, 170, "", "yellow", dashed=True)
    c.text(326, 100, "Gateway zone", 16, bold=True, color="#a67c00")
    c.text(326, 170, "API Gateway\nAuth Server\nDashboard", 15)
    c.box(494, 80, 170, 170, "", "green", dashed=True)
    c.text(579, 100, "Internal zone", 16, bold=True, color="#2f7d3a")
    c.text(579, 170, "Resource Service\nPostgreSQL\nRedis", 15)
    c.box(722, 80, 90, 170, "", "purple", dashed=True)
    c.text(767, 100, "Secrets", 16, bold=True, color="#6a3d9a")
    c.text(767, 170, "Vault", 15)
    for x, n in ((197, "TB-1"), (455, "TB-2"), (693, "TB-3")):
        c.line([(x, 62), (x, 268)], None, dashed=True, color="#b3261e", arrow=False, lw=2.6)
        c.text(x, 46, n, 17, bold=True, color="#b3261e")
    c.line([(158, 215), (236, 215)])
    c.line([(416, 215), (494, 215)])
    c.line([(664, 150), (722, 150)], dashed=True)
    c.text(197, 330, "TB-1  Internet to Gateway\nTLS 1.2+, JWT (RS256, iss,\naud, exp), scope check,\nrate limit, security headers", 13)
    c.text(455, 330, "TB-2  Gateway to Resource Service\nmutual TLS, HMAC-SHA256\nsignature, nonce, 60 s window,\nJWT verified again", 13)
    c.text(700, 330, "TB-3  Services to Vault\nstart-up token\nauthentication", 13)
    for x in (197, 455, 693):
        c.line([(x, 268), (x, 296)], None, arrow=False, color="#b3261e", lw=1.4)
    return c


def login_sequence():
    c = Canvas(820, 560)
    parts = [("Client", "white"), ("Auth Server", "yellow"), ("Redis", "blue")]
    msgs = [
        (0, 1, "POST /auth/login {username, password}", ""),
        (1, 2, "count request per IP (limit 10 / minute)", ""),
        (2, 1, "allowed", "dash"),
        (1, 1, "lockout check (user + address), one bcrypt compare", "self"),
        (1, 0, "401 identical message (wrong user or password)", "bad"),
        (1, 1, "success: issue RS256 access JWT (15 min) + opaque refresh token (7 days)", "self"),
        (1, 0, "200 {access_token, refresh_token, scopes}", "dash"),
        (0, 1, "POST /auth/refresh {refresh_token}", ""),
        (1, 1, "delete old refresh token, issue new pair (rotation)", "self"),
        (1, 0, "200 new tokens  |  401 if token reused", "dash"),
    ]
    b = sequence(c, parts, msgs, top=15, step=46, x0=120, x1=700)
    c.h = int(b + 15)
    return c


def request_sequence():
    c = Canvas(820, 800)
    parts = [("Client", "white"), ("API Gateway", "yellow"), ("Redis", "blue"), ("Resource\nService", "green"), ("PostgreSQL", "blue")]
    msgs = [
        (0, 1, "GET /orders  + Bearer JWT", ""),
        (1, 1, "verify RS256, iss, aud, exp", "self"),
        (1, 2, "rate limit (100 / min / user)", ""),
        (1, 1, "scope check: orders:read", "self"),
        (1, 3, "mTLS call + X-Signature, X-Timestamp, X-Nonce", ""),
        (3, 3, "verify HMAC and 60 s window", "self"),
        (3, 2, "SET nonce NX EX 300", ""),
        (3, 3, "re-verify JWT, scope, ownership", "self"),
        (3, 4, "SELECT ... WHERE owner_id = %s", ""),
        (4, 3, "rows", "dash"),
        (3, 1, "200 JSON", "dash"),
        (1, 0, "200 JSON", "dash"),
    ]
    b = sequence(c, parts, msgs, top=12, head_h=52, step=54, x0=95, x1=725, size=14)
    c.h = int(b + 12)
    return c


JOBS = {
    "fig-architecture": architecture,
    "fig-trust-boundaries": trust_boundaries,
    "fig-login-sequence": login_sequence,
    "fig-request-sequence": request_sequence,
}
