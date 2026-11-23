// Panel 1 (PRD Section 8.1): scrolling table of recent requests, color-coded
// green/red for allow/deny. Fed by the SSE stream, with the initial page
// populated from a one-time REST fetch so the panel isn't empty on load.
export default function LiveFeed({ events }) {
  return (
    <div className="panel">
      <h2>Live Request Feed</h2>
      <div className="feed">
        {events.length === 0 && <div className="hint">No events yet -- traffic will appear here as it happens.</div>}
        {events.map((e) => (
          <div key={e.id} className={`feed-row ${e.meta?.simulated ? "simulated" : ""}`}>
            <span className="ts">{new Date(e.ts).toLocaleTimeString()}</span>
            <span className={`badge ${e.type}`}>{e.type.toUpperCase()}</span>
            <span className="msg">{e.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
