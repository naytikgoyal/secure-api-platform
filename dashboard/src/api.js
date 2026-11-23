// All calls go through the Gateway's real HTTPS API -- this dashboard has no
// special backdoor access. It authenticates with a real admin-scoped JWT and
// hits the same /admin/* endpoints documented in gateway/src/routes/admin.js.
//
// NOTE on self-signed certs: since this project uses a locally-generated CA
// (infra/scripts/gen-certs.sh) rather than a publicly-trusted one, your
// browser will show a certificate warning the first time it talks to
// https://localhost:3000. You need to either import infra/certs/ca.crt into
// your browser/OS trust store, or click through the browser's warning once
// (visit https://localhost:3000/health directly and accept the risk) before
// this dashboard's fetch() calls will succeed. This is expected -- it's the
// same "self-signed cert" reality any local HTTPS dev environment has.
const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || "https://localhost:3000";
const AUTH_URL = import.meta.env.VITE_AUTH_URL || "https://localhost:4000";

export async function login(username, password) {
  const res = await fetch(`${AUTH_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || "Login failed");
  }
  return res.json(); // { access_token, refresh_token, scopes, ... }
}

export async function fetchAuditLogs(token, limit = 100) {
  const res = await fetch(`${GATEWAY_URL}/admin/audit-logs?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`audit-logs fetch failed: HTTP ${res.status}`);
  const body = await res.json();
  return body.events;
}

export async function fetchMetrics(token) {
  const res = await fetch(`${GATEWAY_URL}/admin/metrics`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`metrics fetch failed: HTTP ${res.status}`);
  return res.json();
}

// Sprint 9: reads whatever attacker-toolkit/run_all.py most recently POSTed.
// Returns null if no report has been submitted yet (a real, expected state --
// not every dashboard session will have just run the toolkit), rather than
// throwing, so the panel can render a helpful empty state instead of an error.
export async function fetchAttackReport(token) {
  const res = await fetch(`${GATEWAY_URL}/admin/attack-report`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`attack report fetch failed: HTTP ${res.status}`);
  return res.json();
}

export async function triggerSimulatedAttack(token, type) {
  const res = await fetch(`${GATEWAY_URL}/admin/simulate-attack/${type}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}

// --- Orders API (customer-facing) ---
// These hit the exact same /orders routes as curl/Postman always have --
// see gateway/src/routes/orders.js. The UI adds nothing new on the backend
// side; it's a visual client for the API that already existed since Week 2.

export async function fetchMyOrders(token) {
  const res = await fetch(`${GATEWAY_URL}/orders`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || `Failed to fetch orders (HTTP ${res.status})`);
  }
  return res.json();
}

export async function createOrder(token, item, quantity) {
  const res = await fetch(`${GATEWAY_URL}/orders`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ item, quantity }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.message || `Failed to create order (HTTP ${res.status})`);
  }
  return body;
}

export async function deleteOrder(token, orderId) {
  const res = await fetch(`${GATEWAY_URL}/orders/${encodeURIComponent(orderId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || `Failed to delete order (HTTP ${res.status})`);
  }
}

/**
 * Subscribes to the live audit event stream. Uses fetch() + a manual
 * ReadableStream reader instead of the browser's native EventSource API,
 * because EventSource cannot send custom headers -- it has no way to carry
 * our Authorization: Bearer token. Putting the token in the URL instead
 * (a common EventSource workaround) would leak it into server access logs
 * and browser history, which is a real security downgrade we're avoiding.
 *
 * @param {string} token
 * @param {(event: object) => void} onEvent
 * @returns {() => void} unsubscribe function (aborts the underlying fetch)
 */
export function subscribeToAuditStream(token, onEvent) {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${GATEWAY_URL}/admin/audit-stream`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        console.error("audit-stream connection failed:", res.status);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || ""; // keep any incomplete trailing chunk

        for (const chunk of lines) {
          const dataLine = chunk.split("\n").find((l) => l.startsWith("data: "));
          if (dataLine) {
            try {
              onEvent(JSON.parse(dataLine.slice(6)));
            } catch {
              // malformed chunk -- skip rather than crash the stream
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        console.error("audit-stream error:", err);
      }
    }
  })();

  return () => controller.abort();
}
