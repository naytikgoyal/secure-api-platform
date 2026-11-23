// Panel 4 (PRD Section 8.1): "buttons to fire the attacker toolkit scripts
// directly from the UI and watch Panel 1/2 react live -- this is the single
// best interview demo moment in the whole project."
//
// These call gateway/src/routes/admin.js's /admin/simulate-attack/:type
// endpoints, which make REAL self-requests through the Gateway's actual
// middleware (not fabricated log entries) -- see that file's comments for
// why. The event you'll see appear in LiveFeed/SecurityEvents a moment after
// clicking is a genuine deny produced by the real requireAuth/rate-limiter
// code, tagged (simulated) only because ITS OWN metadata says so, not
// because the dashboard is faking anything.
import { useState } from "react";
import { triggerSimulatedAttack } from "../api.js";

const ATTACKS = [
  { type: "bad-token", label: "🔓 Forge a JWT" },
  { type: "insufficient-scope", label: "🚫 Tamper with a valid token" },
  { type: "rate-limit", label: "🌊 Flood with rapid requests" },
];

export default function AttackTriggers({ token }) {
  const [busy, setBusy] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  async function handleClick(type) {
    setBusy(type);
    setLastResult(null);
    try {
      const result = await triggerSimulatedAttack(token, type);
      setLastResult(result);
    } catch (err) {
      setLastResult({ error: err.message });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="panel">
      <h2>Attack Simulation</h2>
      <div className="trigger-buttons">
        {ATTACKS.map((a) => (
          <button key={a.type} className="trigger-btn" disabled={busy !== null} onClick={() => handleClick(a.type)}>
            {busy === a.type ? "Running..." : a.label}
          </button>
        ))}
      </div>
      {lastResult && (
        <div className="trigger-result">
          {lastResult.error ? `Error: ${lastResult.error}` : lastResult.note}
        </div>
      )}
    </div>
  );
}
