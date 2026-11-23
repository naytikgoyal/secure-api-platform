import { useState } from "react";
import { login } from "../api.js";

export default function LoginScreen({ onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const body = await login(username, password);
      // Any successfully authenticated user gets in now -- what they SEE
      // afterward depends on their scopes (App.jsx routes admin vs. regular
      // users to different views). The backend, not this screen, is what
      // actually enforces who can do what.
      onLoggedIn(body.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-screen">
      <h1>Secure API Communication Platform</h1>
      <p className="hint">Sign in to manage your orders, or as admin for the Security Dashboard.</p>
      <form onSubmit={handleSubmit}>
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" autoComplete="username" />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password"
          autoComplete="current-password"
        />
        <button type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
      {error && <div className="login-error">{error}</div>}
      <p className="hint">
        Demo accounts: naytik / password123 (read+write) &middot; rishi / password123 (read-only) &middot; admin / adminpass456
        <br />
        (see auth-server/src/users.js)
      </p>
    </div>
  );
}
