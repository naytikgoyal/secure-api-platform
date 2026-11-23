import { useCallback, useEffect, useState } from "react";
import OrderList from "./OrderList.jsx";
import CreateOrderForm from "./CreateOrderForm.jsx";
import { fetchMyOrders, createOrder, deleteOrder } from "../api.js";

// The customer-facing view (as opposed to the admin Security Dashboard).
// canWrite comes from the DECODED TOKEN (see jwt.js) -- Rishi's token simply
// does not contain "orders:write", so `canWrite` is false for him and the
// create form + delete buttons never render. This is what makes Naytik's and
// Rishi's screens visibly different for the exact same login page, without any
// separate "Rishi mode" hardcoded anywhere -- it's a direct reflection of his
// actual, real, backend-issued permissions.
export default function OrdersView({ token, scopes, username }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);

  const canWrite = scopes.includes("orders:write");

  const loadOrders = useCallback(() => {
    setLoading(true);
    fetchMyOrders(token)
      .then((data) => {
        setOrders(data);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  async function handleCreate(item, quantity) {
    setCreating(true);
    try {
      await createOrder(token, item, quantity);
      await loadOrders(); // re-fetch rather than optimistically append -- shows the REAL server state
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(orderId) {
    setDeletingId(orderId);
    try {
      await deleteOrder(token, orderId);
      await loadOrders();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="app">
      <div className="header">
        <div>
          <h1>My Orders</h1>
          <div className="subtitle">
            Signed in as {username} &middot; scopes: {scopes.join(", ") || "none"}
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: "1rem" }}>
        <h2>{canWrite ? "Create a New Order" : "Read-only Account"}</h2>
        {canWrite ? (
          <CreateOrderForm onCreate={handleCreate} creating={creating} />
        ) : (
          <p className="hint">
            Your account doesn't have the <code>orders:write</code> scope, so order creation and
            deletion aren't available to you -- this isn't a UI restriction, your token genuinely
            can't perform those actions against the API. Try it yourself with curl and you'll get
            the same 403 the button would have triggered.
          </p>
        )}
      </div>

      <div className="panel" style={{ marginTop: "1rem" }}>
        <h2>Your Orders</h2>
        {loading && <p className="hint">Loading...</p>}
        {error && <div className="login-error">{error}</div>}
        {!loading && !error && (
          <OrderList orders={orders} canWrite={canWrite} onDelete={handleDelete} deletingId={deletingId} />
        )}
      </div>
    </div>
  );
}
