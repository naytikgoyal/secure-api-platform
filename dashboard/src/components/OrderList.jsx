// Renders the user's orders. The Delete button is only rendered at all if
// the caller's token actually has orders:write -- this is the "structurally
// absent, not just disabled" behavior discussed with the user: Rishi's token
// never contains orders:write, so this component literally never puts a
// delete button in the DOM for him. Compare this to a weaker pattern
// (`disabled={!canWrite}`) which still ships the button and its handler to
// every user's browser -- ours doesn't put the capability in front of the
// user at all if they can't use it.
//
// IMPORTANT: this is a UX nicety, not the security control. Even if someone
// inspected the page and manually added a delete button back with devtools,
// clicking it would still hit the real DELETE /orders/:id endpoint, which
// independently re-checks the scope server-side (see gateway/src/routes/orders.js
// and resource-service/main.py) and would reject it for real. The UI reflects
// the permission; it doesn't grant it.
export default function OrderList({ orders, canWrite, onDelete, deletingId }) {
  if (orders.length === 0) {
    return <p className="hint">No orders yet.</p>;
  }

  return (
    <table className="orders-table">
      <thead>
        <tr>
          <th>Item</th>
          <th>Qty</th>
          <th>Created</th>
          {canWrite && <th></th>}
        </tr>
      </thead>
      <tbody>
        {orders.map((o) => (
          <tr key={o.id}>
            <td>{o.item}</td>
            <td>{o.quantity}</td>
            <td>{new Date(o.created_at).toLocaleString()}</td>
            {canWrite && (
              <td>
                <button
                  className="delete-btn"
                  disabled={deletingId === o.id}
                  onClick={() => onDelete(o.id)}
                >
                  {deletingId === o.id ? "Deleting..." : "Delete"}
                </button>
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
