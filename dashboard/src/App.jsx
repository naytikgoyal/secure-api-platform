import { useEffect, useState, useCallback } from "react";
import LoginScreen from "./components/LoginScreen.jsx";
import LiveFeed from "./components/LiveFeed.jsx";
import SecurityEvents from "./components/SecurityEvents.jsx";
import MetricsCards from "./components/MetricsCards.jsx";
import AttackTriggers from "./components/AttackTriggers.jsx";
import AttackHistory from "./components/AttackHistory.jsx";
import OrdersView from "./components/OrdersView.jsx";
import { fetchAuditLogs, fetchMetrics, subscribeToAuditStream } from "./api.js";
import { decodeJwtPayload } from "./jwt.js";

const MAX_FEED_LENGTH = 100;

export default function App() {
  const [token, setToken] = useState(null);
  const [claims, setClaims] = useState(null); // { sub, scopes } decoded from the token -- UI routing only, see jwt.js
  const [events, setEvents] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [connected, setConnected] = useState(false);

  function handleLogin(newToken) {
    const decoded = decodeJwtPayload(newToken);
    setClaims({ sub: decoded?.sub || "unknown", scopes: decoded?.scopes || [] });
    setToken(newToken);
  }

  function handleLogout() {
    setToken(null);
    setClaims(null);
    setEvents([]);
    setMetrics(null);
  }

  const isAdmin = claims?.scopes?.includes("admin");

  const addEvent = useCallback((event) => {
    setEvents((prev) => [event, ...prev].slice(0, MAX_FEED_LENGTH));
  }, []);

  // Admin-only data feeds (audit log history + live SSE stream) -- only ever
  // requested when the signed-in user is actually an admin. Requesting these
  // as Naytik or Rishi would just get a real 403 from the Gateway anyway (see
  // gateway/src/routes/admin.js), so there's no point trying.
  useEffect(() => {
    if (!token || !isAdmin) return;

    let cancelled = false;

    fetchAuditLogs(token, 100)
      .then((initial) => {
        if (!cancelled) setEvents(initial);
      })
      .catch((err) => console.error("Failed to load initial audit logs:", err));

    setConnected(true);
    const unsubscribe = subscribeToAuditStream(token, addEvent);

    return () => {
      cancelled = true;
      setConnected(false);
      unsubscribe();
    };
  }, [token, isAdmin, addEvent]);

  useEffect(() => {
    if (!token || !isAdmin) return;

    let cancelled = false;
    const poll = () => {
      fetchMetrics(token)
        .then((m) => {
          if (!cancelled) setMetrics(m);
        })
        .catch((err) => console.error("Failed to fetch metrics:", err));
    };

    poll();
    const interval = setInterval(poll, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token, isAdmin]);

  if (!token || !claims) {
    return (
      <div className="app">
        <LoginScreen onLoggedIn={handleLogin} />
      </div>
    );
  }

  // Non-admin users (Naytik, Rishi, or anyone without the admin scope) get the
  // customer-facing Orders view instead of the Security Dashboard. Same
  // login screen, same token mechanism -- the ONLY thing that changed is
  // what's inside the JWT's scopes claim, which the backend issued and
  // signed, not something this page decided on its own.
  if (!isAdmin) {
    return (
      <>
        <OrdersView token={token} scopes={claims.scopes} username={claims.sub} />
        <div style={{ textAlign: "center", padding: "1rem" }}>
          <button className="trigger-btn" style={{ maxWidth: "200px", margin: "0 auto" }} onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </>
    );
  }

  return (
    <div className="app">
      <div className="header">
        <div>
          <h1>Security Operations Dashboard</h1>
          <div className="subtitle">Secure API Communication Platform &middot; {claims.sub}</div>
        </div>
        <div>
          <span className={`connection-dot ${connected ? "connected" : "disconnected"}`} />
          <span className="subtitle">{connected ? "Live" : "Disconnected"}</span>
          <button className="trigger-btn" style={{ marginLeft: "1rem", display: "inline-block", width: "auto" }} onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </div>

      <MetricsCards metrics={metrics} />

      <div className="grid" style={{ marginTop: "1rem" }}>
        <LiveFeed events={events} />
        <SecurityEvents events={events} />
        <AttackTriggers token={token} />
        <AttackHistory token={token} />
      </div>
    </div>
  );
}
