// Centralized error handling (NFR: never leak stack traces or internals to clients).
// This is the ONE place error responses get formatted -- individual routes should
// just `throw` or `next(err)`, never hand-format an error response themselves.

export function notFoundHandler(req, res) {
  res.status(404).json({ error: "not_found", message: "Route not found." });
}

// eslint-disable-next-line no-unused-vars
export function errorHandler(err, req, res, next) {
  // Full error (with stack trace) goes to server-side logs only.
  console.error(`[gateway] ERROR on ${req.method} ${req.originalUrl}:`, err);

  const status = err.status || err.statusCode || 500;

  // Generic message to the client -- specific enough to be useful, never a stack trace.
  const message =
    status === 400
      ? "Invalid request."
      : status === 404
      ? "Resource not found."
      : status === 502
      ? "Upstream service unavailable."
      : "Something went wrong. Please try again.";

  res.status(status).json({ error: "request_failed", message });
}
