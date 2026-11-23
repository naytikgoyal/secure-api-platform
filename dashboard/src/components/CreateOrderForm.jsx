import { useState } from "react";

// Parent only mounts this component at all when the token has orders:write
// (see OrdersView.jsx) -- same "structurally absent" principle as the delete
// button in OrderList.jsx.
export default function CreateOrderForm({ onCreate, creating }) {
  const [item, setItem] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    if (!item.trim()) {
      setError("Item name is required.");
      return;
    }
    try {
      await onCreate(item.trim(), Number(quantity));
      setItem("");
      setQuantity(1);
    } catch (err) {
      // Surfaces REAL backend validation errors -- e.g. try quantity 0 or a
      // 300-character item name and you'll see the actual 422 message from
      // resource-service/main.py's Pydantic model, not a fake client-side check.
      setError(err.message);
    }
  }

  return (
    <form className="create-order-form" onSubmit={handleSubmit}>
      <input
        value={item}
        onChange={(e) => setItem(e.target.value)}
        placeholder="Item name"
        disabled={creating}
      />
      <input
        type="number"
        min="1"
        max="1000"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        disabled={creating}
      />
      <button type="submit" disabled={creating}>
        {creating ? "Creating..." : "Create Order"}
      </button>
      {error && <div className="login-error">{error}</div>}
    </form>
  );
}
