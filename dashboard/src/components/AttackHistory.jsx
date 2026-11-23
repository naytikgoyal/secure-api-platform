import { useEffect, useState } from "react";
import { fetchAttackReport } from "../api.js";

// Shows the results of the last attacker-toolkit run (attacker-toolkit/run_all.py),
// polled the same way MetricsCards.jsx does -- this is genuinely the LAST
// real run's data, not a live feed; the toolkit only reports once, at the
// end of a full run, not per-check.
export default function AttackHistory({ token }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      fetchAttackReport(token)
        .then((r) => {
          if (!cancelled) {
            setReport(r);
            setError(null);
          }
        })
        .catch((err) => !cancelled && setError(err.message));
    };
    poll();
    const interval = setInterval(poll, 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token]);

  return (
    <div className="panel">
      <h2>Attack History</h2>
      {error && <div className="login-error">{error}</div>}
      {!error && !report && (
        <p className="hint">
          No report yet. Run <code>attacker-toolkit/run_all.py</code> and it'll appear here
          automatically within 10 seconds.
        </p>
      )}
      {report && (
        <div>
          <p className="hint" style={{ marginTop: 0 }}>
            Last run: {new Date(report.ran_at).toLocaleString()} &middot;{" "}
            {/* any_failed / any_skipped exist in reports from the current toolkit; older reports only have all_passed */}
            <span style={{ color: report.all_passed ? "var(--green)" : report.any_failed === false ? "var(--text-dim)" : "var(--red)" }}>
              {report.all_passed
                ? "ALL ATTACKS BLOCKED"
                : report.any_failed === false
                ? "NO ATTACK SUCCEEDED · SOME CHECKS COULD NOT RUN"
                : "SOME ATTACKS SUCCEEDED"}
            </span>
          </p>
          {report.scripts.map((s) => (
            <div key={s.name} style={{ marginBottom: "0.4rem" }}>
              <div
                className="feed-row"
                style={{ cursor: "pointer" }}
                onClick={() => setExpanded(expanded === s.name ? null : s.name)}
              >
                {s.status === "skip" ? (
                  <span className="badge" style={{ background: "#2a3340", color: "var(--text-dim)" }}>SKIP</span>
                ) : (
                  <span className={`badge ${s.passed ? "allow" : "deny"}`}>{s.passed ? "PASS" : "FAIL"}</span>
                )}
                <span className="msg">{s.name} {expanded === s.name ? "\u25b2" : "\u25bc"}</span>
              </div>
              {expanded === s.name && (
                <pre
                  style={{
                    background: "#0a0e13",
                    padding: "0.6rem",
                    borderRadius: "6px",
                    fontSize: "0.68rem",
                    maxHeight: "220px",
                    overflow: "auto",
                    color: "var(--text-dim)",
                  }}
                >
                  {s.output_tail}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
