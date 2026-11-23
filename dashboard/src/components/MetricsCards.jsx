// Panel 3 (PRD Section 8.1): requests/min, error rate, rate-limited clients,
// token issuance count. Polled from GET /admin/metrics (not SSE -- these are
// aggregates over a rolling window, cheaper to recompute on demand than to
// push on every single event).
export default function MetricsCards({ metrics }) {
  if (!metrics) {
    return (
      <div className="panel">
        <h2>Metrics</h2>
        <div className="hint">Loading...</div>
      </div>
    );
  }

  const cards = [
    { label: "Requests / min", value: metrics.requestsPerMinute },
    { label: "Deny rate", value: `${metrics.denyRate}%` },
    { label: "Rate-limited (1m)", value: metrics.rateLimitedCount },
    { label: "Total tracked", value: metrics.totalTracked },
  ];

  return (
    <div className="panel">
      <h2>Metrics</h2>
      <div className="metrics-cards">
        {cards.map((c) => (
          <div className="metric-card" key={c.label}>
            <div className="value">{c.value}</div>
            <div className="label">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
