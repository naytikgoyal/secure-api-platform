// Holds the most recent attacker-toolkit report (see
// attacker-toolkit/run_all.py, which POSTs here after each run). Same
// "in-memory, single-instance, demo-scoped" tradeoff as auditEvents.js's
// ring buffer -- if the Gateway restarts, this resets to null, which is
// fine: the toolkit can just be run again. A durable store (a real database,
// or even just writing to Vault/a file) would be the obvious next step in
// a system that needed this to survive restarts.
let latestReport = null;

export function setLatestReport(report) {
  latestReport = report;
}

export function getLatestReport() {
  return latestReport;
}
