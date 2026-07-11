import { TrendingUp, TrendingDown, Users, Loader2, Search, X, Clock } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { analyticsApi, orderApi, type Order, type OrderStatus } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DailyPoint { date: string; revenue: number; orders: number }
interface TopItem { name: string; total_qty: number; total_revenue: number }
interface TopCustomer { name: string; order_count: number; total_spent: number }

interface AnalyticsData {
  period_days: number;
  total_revenue: number;
  total_orders: number;
  avg_order_value: number;
  daily_revenue: DailyPoint[];
  top_items: TopItem[];
  top_customers: TopCustomer[];
  orders_by_status: Record<string, number>;
}

const STATUS_COLOR: Record<OrderStatus, string> = {
  pending: "bg-amber-100 text-amber-700",
  confirmed: "bg-sky-100 text-sky-700",
  preparing: "bg-violet-100 text-violet-700",
  ready: "bg-emerald-100 text-emerald-700",
  completed: "bg-mist text-muted-foreground",
  cancelled: "bg-rose-100 text-rose-500",
};

const MAX_HISTORY_DAYS = 60;

function toLocalDateStr(d: Date): string {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MerchantAnalyticsPage() {
  const [range, setRange] = useState<14 | 30 | 90>(30);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Order history state
  const [historyOrders, setHistoryOrders] = useState<Order[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [historyPage, setHistoryPage] = useState(1);
  const perPage = 10;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    analyticsApi
      .merchant(range)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e: any) => { if (!cancelled) setError(e.message ?? "Failed to load analytics"); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [range]);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const orders = await orderApi.merchantHistory({
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      setHistoryOrders(orders);
      setHistoryPage(1);
    } catch (e: any) {
      setHistoryError(e.message ?? "Failed to load order history");
    } finally {
      setHistoryLoading(false);
    }
  }, [searchQuery, statusFilter, dateFrom, dateTo]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  if (loading) return <div className="flex justify-center py-24"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>;
  if (error) return <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>;

  const daily = data?.daily_revenue ?? [];
  const items = data?.top_items ?? [];
  const customers = data?.top_customers ?? [];

  // Pagination for order history
  const totalPages = Math.ceil(historyOrders.length / perPage);
  const pagedOrders = historyOrders.slice((historyPage - 1) * perPage, historyPage * perPage);

  return (
    <div className="space-y-8">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Last {range} days</p>
        <h1 className="font-display mt-1 text-5xl text-foreground">Analytics</h1>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Kpi label="Revenue" value={`NPR ${Number(data?.total_revenue ?? 0).toLocaleString()}`} />
        <Kpi label="Orders" value={String(data?.total_orders ?? 0)} />
        <Kpi label="Avg order" value={`NPR ${Number(data?.avg_order_value ?? 0).toLocaleString()}`} />
      </div>

      {/* Revenue chart */}
      <section className="glass-strong rounded-3xl p-6">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Revenue trend</p>
            <h2 className="font-display mt-1 text-3xl text-foreground">
              NPR {Number(data?.total_revenue ?? 0).toLocaleString()}
            </h2>
          </div>
          <div className="flex gap-1">
            {([14, 30, 90] as const).map((p) => (
              <button key={p} onClick={() => setRange(p)}
                className={`rounded-full px-3 py-1.5 text-xs transition-colors ${range === p ? "bg-ink text-primary-foreground" : "glass text-muted-foreground"}`}>
                {p}d
              </button>
            ))}
          </div>
        </div>

        <div className="mt-8 relative h-48">
          {daily.every((d) => d.revenue === 0) ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No completed orders in this period yet
            </div>
          ) : (
            <RevenueChart points={daily} />
          )}
        </div>
      </section>

      {/* Two col: top items + top customers */}
      <div className="grid gap-3 lg:grid-cols-2">
        {/* Top items */}
        <section className="glass-strong rounded-3xl p-6">
          <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Top items</p>
          <h3 className="font-display mt-1 text-2xl text-foreground">Best sellers</h3>
          {items.length === 0 ? (
            <p className="mt-5 text-sm text-muted-foreground">No orders yet.</p>
          ) : (
            <ul className="mt-5 space-y-3">
              {items.map((item, i) => (
                <li key={i} className="flex items-center gap-3">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-mist text-xs font-medium text-foreground">
                    {i + 1}
                  </span>
                  <span className="flex-1 truncate text-sm text-foreground">{item.name}</span>
                  <span className="text-xs text-muted-foreground">{item.total_qty}× sold</span>
                  <span className="font-display text-sm text-ember">
                    NPR {Number(item.total_revenue).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Top customers */}
        <section className="glass-strong rounded-3xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Leaderboard</p>
              <h3 className="font-display mt-1 text-2xl text-foreground">Top customers</h3>
            </div>
            <Users className="h-5 w-5 text-muted-foreground" />
          </div>
          {customers.length === 0 ? (
            <p className="mt-5 text-sm text-muted-foreground">No completed orders yet.</p>
          ) : (
            <ul className="mt-5 space-y-3">
              {customers.map((c, i) => (
                <li key={i} className="flex items-center gap-3">
                  <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-medium ${i === 0 ? "bg-amber-100 text-amber-700" : i === 1 ? "bg-slate-100 text-slate-600" : i === 2 ? "bg-orange-100 text-orange-700" : "bg-mist text-muted-foreground"
                    }`}>{i + 1}</span>
                  <span className="flex-1 truncate text-sm text-foreground">{c.name}</span>
                  <span className="text-xs text-muted-foreground">{c.order_count} order{c.order_count !== 1 ? "s" : ""}</span>
                  <span className="font-display text-sm text-ember">
                    NPR {Number(c.total_spent).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Orders by status */}
      {data?.orders_by_status && Object.keys(data.orders_by_status).length > 0 && (
        <section className="glass-strong rounded-3xl p-6">
          <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Orders by status</p>
          <h3 className="font-display mt-1 text-2xl text-foreground">Breakdown</h3>
          <div className="mt-4 grid grid-cols-3 gap-3 sm:grid-cols-6">
            {Object.entries(data.orders_by_status).map(([status, count]) => (
              <div key={status} className="rounded-2xl bg-mist p-3 text-center">
                <p className="font-display text-2xl text-foreground">{count}</p>
                <p className="mt-1 text-[10px] capitalize text-muted-foreground">{status}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Order History Section ──────────────────────────────────────────── */}
      <section className="glass-strong rounded-3xl p-6 space-y-5">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Order History</p>
          <h3 className="font-display mt-1 text-2xl text-foreground">Past orders (up to 2 months)</h3>
        </div>

        {/* Search & Filters */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center bg-mist/30 p-4 rounded-3xl border border-border/40">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by customer or item..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-10 w-full rounded-2xl bg-mist pl-10 pr-10 text-sm text-foreground outline-none border border-transparent focus:border-border transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-10 rounded-2xl bg-mist px-3 text-sm text-foreground outline-none border border-transparent focus:border-border transition-colors cursor-pointer"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="confirmed">Confirmed</option>
              <option value="preparing">Preparing</option>
              <option value="ready">Ready</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>

            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                const val = e.target.value;
                if (val) {
                  const selected = new Date(val);
                  const minDate = new Date();
                  minDate.setDate(minDate.getDate() - MAX_HISTORY_DAYS);
                  if (selected < minDate) {
                    setDateFrom(toLocalDateStr(minDate));
                    return;
                  }
                }
                setDateFrom(val);
              }}
              max={dateTo || toLocalDateStr(new Date())}
              className="h-10 rounded-2xl bg-mist px-3 text-sm text-foreground outline-none border border-transparent focus:border-border transition-colors cursor-pointer"
            />
            <span className="text-xs text-muted-foreground">to</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              min={dateFrom || undefined}
              max={toLocalDateStr(new Date())}
              className="h-10 rounded-2xl bg-mist px-3 text-sm text-foreground outline-none border border-transparent focus:border-border transition-colors cursor-pointer"
            />
          </div>
        </div>

        {historyError && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {historyError}
          </div>
        )}

        {historyLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : historyOrders.length === 0 ? (
          <div className="rounded-2xl bg-mist/50 py-10 text-center text-sm text-muted-foreground">
            No orders found for the selected filters.
          </div>
        ) : (
          <>
            {/* Order list */}
            <div className="space-y-3">
              {pagedOrders.map((order) => (
                <HistoryOrderCard key={order.id} order={order} />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-2">
                <button
                  onClick={() => setHistoryPage((p) => Math.max(1, p - 1))}
                  disabled={historyPage === 1}
                  className="h-9 rounded-xl bg-mist px-3 text-xs font-medium text-foreground disabled:opacity-40"
                >
                  Prev
                </button>
                <span className="text-xs text-muted-foreground">
                  Page {historyPage} of {totalPages}
                </span>
                <button
                  onClick={() => setHistoryPage((p) => Math.min(totalPages, p + 1))}
                  disabled={historyPage === totalPages}
                  className="h-9 rounded-xl bg-mist px-3 text-xs font-medium text-foreground disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}

// ── History Order Card ────────────────────────────────────────────────────────

function HistoryOrderCard({ order }: { order: Order }) {
  const customerName = order.profiles?.full_name ?? order.customer_name ?? "Customer";
  const mins = Math.floor((Date.now() - new Date(order.created_at).getTime()) / 60_000);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);

  let timeLabel: string;
  if (days > 0) timeLabel = `${days}d ago`;
  else if (hours > 0) timeLabel = `${hours}h ago`;
  else if (mins > 0) timeLabel = `${mins}m ago`;
  else timeLabel = "Just now";

  const isPunchCard = (order as any).order_type === "punch_card_redemption";
  const isReward = (order as any).order_type === "reward_redemption";

  return (
    <div className="glass rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
            #{String(order.id).slice(0, 8)}
          </p>
          <span className={`rounded-full px-2.5 py-0.5 text-[10px] uppercase tracking-widest font-medium ${STATUS_COLOR[order.status]}`}>
            {order.status}
          </span>
          {isPunchCard && (
            <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-medium text-violet-700">Punch Card</span>
          )}
          {isReward && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">Reward</span>
          )}
        </div>
        <p className="mt-1 text-sm font-medium text-foreground truncate">{customerName}</p>
        <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
          {(order.order_items ?? []).slice(0, 3).map((item) => (
            <li key={item.id}>{item.quantity}× {item.name}</li>
          ))}
          {(order.order_items ?? []).length > 3 && (
            <li>+{order.order_items.length - 3} more</li>
          )}
        </ul>
      </div>

      <div className="flex items-center gap-4 sm:text-right shrink-0">
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          {timeLabel}
        </span>
        <span className="font-display text-base text-foreground">
          {Number(order.total_amount) > 0
            ? `NPR ${Number(order.total_amount).toLocaleString()}`
            : "FREE"}
        </span>
      </div>
    </div>
  );
}

// ── Revenue chart ──────────────────────────────────────────────────────────────

function RevenueChart({ points }: { points: DailyPoint[] }) {
  const values = points.map((p) => Number(p.revenue));
  const max = Math.max(...values, 1);
  const coords = values.map(
    (v, i) => `${(i / Math.max(values.length - 1, 1)) * 280},${100 - (v / max) * 90}`
  );
  const line = `M ${coords.join(" L ")}`;
  const area = `${line} L 280,100 L 0,100 Z`;
  return (
    <svg viewBox="0 0 280 100" preserveAspectRatio="none" className="h-full w-full overflow-visible">
      <defs>
        <linearGradient id="rg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="oklch(0.68 0.16 45)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="oklch(0.68 0.16 45)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#rg)" />
      <path d={line} fill="none" stroke="oklch(0.68 0.16 45)" strokeWidth="1.5" />
    </svg>
  );
}

// ── KPI card ───────────────────────────────────────────────────────────────────

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass-strong rounded-3xl p-5">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="font-display mt-2 text-3xl text-foreground">{value}</p>
    </div>
  );
}
