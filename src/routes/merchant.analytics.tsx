import { createFileRoute } from "@tanstack/react-router";
import { TrendingUp, TrendingDown, Users, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { analyticsApi } from "@/lib/api";

export const Route = createFileRoute("/merchant/analytics")({
  head: () => ({ meta: [{ title: "Analytics · Merchant · Zentro" }] }),
  component: Analytics,
});

// ── Types ─────────────────────────────────────────────────────────────────────

interface DailyPoint { date: string; revenue: number; orders: number }
interface TopItem    { name: string; total_qty: number; total_revenue: number }
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

// ── Component ─────────────────────────────────────────────────────────────────

function Analytics() {
  const [range, setRange] = useState<14 | 30 | 90>(30);
  const [data, setData]   = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

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

  if (loading) return <div className="flex justify-center py-24"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>;
  if (error)   return <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>;

  const daily  = data?.daily_revenue ?? [];
  const items  = data?.top_items ?? [];
  const customers = data?.top_customers ?? [];

  return (
    <div className="space-y-8">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Last {range} days</p>
        <h1 className="font-display mt-1 text-5xl text-ink">Analytics</h1>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Kpi label="Revenue"     value={`NPR ${Number(data?.total_revenue ?? 0).toLocaleString()}`} />
        <Kpi label="Orders"      value={String(data?.total_orders ?? 0)} />
        <Kpi label="Avg order"   value={`NPR ${Number(data?.avg_order_value ?? 0).toLocaleString()}`} />
      </div>

      {/* Revenue chart */}
      <section className="glass-strong rounded-3xl p-6">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Revenue trend</p>
            <h2 className="font-display mt-1 text-3xl text-ink">
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
          <h3 className="font-display mt-1 text-2xl text-ink">Best sellers</h3>
          {items.length === 0 ? (
            <p className="mt-5 text-sm text-muted-foreground">No orders yet.</p>
          ) : (
            <ul className="mt-5 space-y-3">
              {items.map((item, i) => (
                <li key={i} className="flex items-center gap-3">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-mist text-xs font-medium text-ink">
                    {i + 1}
                  </span>
                  <span className="flex-1 truncate text-sm text-ink">{item.name}</span>
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
              <h3 className="font-display mt-1 text-2xl text-ink">Top customers</h3>
            </div>
            <Users className="h-5 w-5 text-muted-foreground" />
          </div>
          {customers.length === 0 ? (
            <p className="mt-5 text-sm text-muted-foreground">No completed orders yet.</p>
          ) : (
            <ul className="mt-5 space-y-3">
              {customers.map((c, i) => (
                <li key={i} className="flex items-center gap-3">
                  <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-medium ${
                    i === 0 ? "bg-amber-100 text-amber-700" : i === 1 ? "bg-slate-100 text-slate-600" : i === 2 ? "bg-orange-100 text-orange-700" : "bg-mist text-muted-foreground"
                  }`}>{i + 1}</span>
                  <span className="flex-1 truncate text-sm text-ink">{c.name}</span>
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
          <h3 className="font-display mt-1 text-2xl text-ink">Breakdown</h3>
          <div className="mt-4 grid grid-cols-3 gap-3 sm:grid-cols-6">
            {Object.entries(data.orders_by_status).map(([status, count]) => (
              <div key={status} className="rounded-2xl bg-mist p-3 text-center">
                <p className="font-display text-2xl text-ink">{count}</p>
                <p className="mt-1 text-[10px] capitalize text-muted-foreground">{status}</p>
              </div>
            ))}
          </div>
        </section>
      )}
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
      <p className="font-display mt-2 text-3xl text-ink">{value}</p>
    </div>
  );
}
