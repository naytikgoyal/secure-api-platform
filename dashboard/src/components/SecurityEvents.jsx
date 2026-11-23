// Panel 2 (PRD Section 8.1): denied auth attempts, replay blocks, rate-limit
// hits, signature failures -- each with a human-readable reason, not just a
// status code. This is the same underlying event stream as LiveFeed, filtered
// to denies only, because the PRD calls these out as a distinct panel with a
// distinct job: "teaching the viewer the control, not just showing red text."
const CATEGORY_LABELS = {
  auth: "Authentication",
  scope: "Authorization (scope)",
  rate_limit: "Rate Limiting",
};

export default function SecurityEvents({ events }) {
  const denies = events.filter((e) => e.type === "deny");

  return (
    <div className="panel">
      <h2>Security Events (denies only)</h2>
      <div className="feed">
        {denies.length === 0 && <div className="hint">No denied requests yet.</div>}
        {denies.map((e) => (
          <div key={e.id} className={`feed-row ${e.meta?.simulated ? "simulated" : ""}`}>
            <span className="ts">{new Date(e.ts).toLocaleTimeString()}</span>
            <span className="badge deny">{CATEGORY_LABELS[e.category] || e.category}</span>
            <span className="msg">{e.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
