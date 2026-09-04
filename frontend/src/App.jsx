import {
  Activity,
  AlertTriangle,
  Bug,
  CheckCircle2,
  ClipboardList,
  Clock,
  CreditCard,
  Database,
  Package,
  PackagePlus,
  Play,
  ReceiptText,
  RefreshCw,
  ServerCrash,
  Settings,
  ShoppingCart,
  UserPlus,
  Zap,
} from "lucide-react";
import { useMemo, useState } from "react";

const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "/api";

const errorActions = [
  {
    key: "runtime_exception",
    label: "Runtime Exception",
    path: "/test/errors/runtime-exception",
    icon: Bug,
  },
  {
    key: "database_connection_failure",
    label: "DB Connection",
    path: "/test/errors/db-connection",
    icon: Database,
  },
  {
    key: "database_slow_query",
    label: "Slow Query",
    path: "/test/errors/db-slow-query",
    icon: Clock,
  },
  {
    key: "validation_error",
    label: "Validation",
    path: "/test/errors/validation",
    icon: AlertTriangle,
  },
  {
    key: "inventory_mismatch",
    label: "Inventory Mismatch",
    path: "/test/errors/inventory-mismatch",
    icon: Package,
  },
  {
    key: "payment_timeout",
    label: "Payment Timeout",
    path: "/test/errors/payment-timeout",
    icon: CreditCard,
  },
  {
    key: "payment_declined",
    label: "Payment Declined",
    path: "/test/errors/payment-declined",
    icon: CreditCard,
  },
  {
    key: "configuration_error",
    label: "Missing Configuration",
    path: "/test/errors/config-missing",
    icon: Settings,
  },
  {
    key: "background_job_failure",
    label: "Job Failure",
    path: "/test/errors/background-job-failure",
    icon: ServerCrash,
  },
];

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

function statusClass(status) {
  if (!status) return "muted";
  if (status >= 500) return "bad";
  if (status >= 400) return "warn";
  return "good";
}

function responseStatusText(action) {
  if (!action) return "none";
  return action.status || "fetch error";
}

function Button({ icon: Icon, children, onClick, disabled, variant = "secondary" }) {
  return (
    <button className={`button ${variant}`} type="button" onClick={onClick} disabled={disabled}>
      <Icon size={17} aria-hidden="true" />
      <span>{children}</span>
    </button>
  );
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export default function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [latestResponse, setLatestResponse] = useState(null);
  const [recentActions, setRecentActions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [users, setUsers] = useState([]);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [selectedProductId, setSelectedProductId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [paymentAmount, setPaymentAmount] = useState(1299);

  const selectedProduct = useMemo(
    () => products.find((product) => String(product.id) === String(selectedProductId)),
    [products, selectedProductId],
  );

  async function callApi({ label, method = "GET", path, body }) {
    setIsLoading(true);
    const startedAt = performance.now();
    const requestId = `ui-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

    let result;
    try {
      const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}${path}`, {
        method,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-Request-Id": requestId,
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      const text = await response.text();
      let parsedBody = null;
      try {
        parsedBody = text ? JSON.parse(text) : null;
      } catch {
        parsedBody = text;
      }
      result = {
        label,
        method,
        path,
        status: response.status,
        requestId,
        durationMs: Math.round(performance.now() - startedAt),
        body: parsedBody,
      };
    } catch (error) {
      result = {
        label,
        method,
        path,
        status: null,
        requestId,
        durationMs: Math.round(performance.now() - startedAt),
        body: null,
        error: error.message,
      };
    }

    setLatestResponse(result);
    setRecentActions((items) => [result, ...items].slice(0, 12));
    setIsLoading(false);
    return result;
  }

  async function refreshProducts() {
    const result = await callApi({ label: "List products", path: "/products" });
    if (result.status === 200 && Array.isArray(result.body)) {
      setProducts(result.body);
      if (!selectedProductId && result.body.length > 0) {
        setSelectedProductId(String(result.body[0].id));
      }
      return result.body;
    }
    return [];
  }

  async function refreshOrders() {
    const result = await callApi({ label: "List orders", path: "/orders" });
    if (result.status === 200 && Array.isArray(result.body)) {
      setOrders(result.body);
    }
  }

  async function createUser() {
    const suffix = Date.now();
    const result = await callApi({
      label: "Create user",
      method: "POST",
      path: "/users",
      body: {
        email: `ui-user-${suffix}@example.com`,
        name: `UI User ${suffix}`,
      },
    });
    if (result.status === 201 && result.body) {
      setUsers((items) => [result.body, ...items]);
      setSelectedUserId(String(result.body.id));
    }
  }

  async function createProduct() {
    const suffix = Date.now();
    const result = await callApi({
      label: "Create product",
      method: "POST",
      path: "/products",
      body: {
        sku: `SKU-UI-${suffix}`,
        name: `UI Test Product ${suffix}`,
        price_cents: 1599,
        inventory_count: 25,
      },
    });
    if (result.status === 201 && result.body) {
      setProducts((items) => [result.body, ...items]);
      setSelectedProductId(String(result.body.id));
    }
  }

  async function createOrder() {
    let userId = selectedUserId;
    let productId = selectedProductId;

    if (!userId) {
      const result = await callApi({
        label: "Create user for order",
        method: "POST",
        path: "/users",
        body: {
          email: `ui-order-user-${Date.now()}@example.com`,
          name: "UI Order User",
        },
      });
      if (result.status !== 201 || !result.body) return;
      setUsers((items) => [result.body, ...items]);
      userId = String(result.body.id);
      setSelectedUserId(userId);
    }

    if (!productId) {
      const loadedProducts = await refreshProducts();
      if (loadedProducts.length > 0) {
        productId = String(loadedProducts[0].id);
        setSelectedProductId(productId);
      }
    }

    if (!productId) return;

    const result = await callApi({
      label: "Create order",
      method: "POST",
      path: "/orders",
      body: {
        user_id: Number(userId),
        product_id: Number(productId),
        quantity: Number(quantity),
      },
    });
    if (result.status === 201 && result.body) {
      setOrders((items) => [result.body, ...items]);
    }
  }

  async function simulatePayment() {
    await callApi({
      label: "Simulate payment",
      method: "POST",
      path: "/payments/simulate",
      body: {
        amount_cents: Number(paymentAmount),
        outcome: "success",
      },
    });
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Demo Order Service</h1>
          <p>Manual control surface for creating backend logs</p>
        </div>
        <div className="api-target">
          <span>API</span>
          <input
            aria-label="API base URL"
            value={apiBaseUrl}
            onChange={(event) => setApiBaseUrl(event.target.value)}
          />
        </div>
      </header>

      <section className="grid">
        <div className="panel">
          <div className="panel-heading">
            <h2>Service</h2>
            <span className={isLoading ? "pulse" : ""}>{isLoading ? "Running" : "Idle"}</span>
          </div>
          <div className="button-grid two">
            <Button icon={Activity} onClick={() => callApi({ label: "Health", path: "/health" })}>
              Health
            </Button>
            <Button icon={CheckCircle2} onClick={() => callApi({ label: "Ready", path: "/ready" })}>
              Ready
            </Button>
          </div>
        </div>

        <div className="panel wide">
          <div className="panel-heading">
            <h2>Normal Flows</h2>
            <span>INFO logs</span>
          </div>
          <div className="controls">
            <Field label="User">
              <select value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)}>
                <option value="">Auto-create</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    #{user.id} {user.email}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Product">
              <select
                value={selectedProductId}
                onChange={(event) => setSelectedProductId(event.target.value)}
              >
                <option value="">Load products</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    #{product.id} {product.sku}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Quantity">
              <input
                type="number"
                min="1"
                max="5"
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
              />
            </Field>
            <Field label="Payment cents">
              <input
                type="number"
                min="1"
                value={paymentAmount}
                onChange={(event) => setPaymentAmount(event.target.value)}
              />
            </Field>
          </div>
          {selectedProduct ? (
            <p className="hint">
              Selected product inventory: {selectedProduct.inventory_count}, price:{" "}
              {selectedProduct.price_cents} cents
            </p>
          ) : null}
          <div className="button-grid">
            <Button icon={UserPlus} onClick={createUser}>
              Create User
            </Button>
            <Button icon={Package} onClick={refreshProducts}>
              List Products
            </Button>
            <Button icon={PackagePlus} onClick={createProduct}>
              Create Product
            </Button>
            <Button icon={ShoppingCart} onClick={createOrder} variant="primary">
              Create Order
            </Button>
            <Button icon={ReceiptText} onClick={refreshOrders}>
              List Orders
            </Button>
            <Button icon={CreditCard} onClick={simulatePayment}>
              Simulate Payment
            </Button>
          </div>
        </div>

        <div className="panel full">
          <div className="panel-heading">
            <h2>Error Injection</h2>
            <span>ERROR logs</span>
          </div>
          <div className="button-grid errors">
            {errorActions.map((action) => (
              <Button
                key={action.key}
                icon={action.icon}
                onClick={() =>
                  callApi({
                    label: action.label,
                    method: "POST",
                    path: action.path,
                    body: {},
                  })
                }
                variant="danger"
              >
                {action.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="panel response">
          <div className="panel-heading">
            <h2>Latest Response</h2>
            <span className={statusClass(latestResponse?.status)}>
              {responseStatusText(latestResponse)}
            </span>
          </div>
          <pre>{latestResponse ? formatJson(latestResponse) : "No action yet."}</pre>
        </div>

        <div className="panel response">
          <div className="panel-heading">
            <h2>Recent Actions</h2>
            <Button icon={RefreshCw} onClick={() => setRecentActions([])}>
              Clear
            </Button>
          </div>
          <div className="recent-list">
            {recentActions.length === 0 ? (
              <p className="empty">No actions yet.</p>
            ) : (
              recentActions.map((action) => (
                <div className="recent-item" key={`${action.requestId}-${action.path}`}>
                  <div>
                    <strong>{action.label}</strong>
                    <span>
                      {action.method} {action.path}
                    </span>
                    {action.error ? <span className="error-detail">{action.error}</span> : null}
                  </div>
                  <span className={statusClass(action.status)}>{responseStatusText(action)}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="panel full summary">
          <div>
            <ClipboardList size={18} />
            <span>Users cached: {users.length}</span>
          </div>
          <div>
            <Package size={18} />
            <span>Products cached: {products.length}</span>
          </div>
          <div>
            <ShoppingCart size={18} />
            <span>Orders cached: {orders.length}</span>
          </div>
          <div>
            <Zap size={18} />
            <span>Manual calls create backend logs immediately.</span>
          </div>
        </div>
      </section>
    </main>
  );
}
