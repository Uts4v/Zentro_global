import { createFileRoute, Link } from "@tanstack/react-router";
import { type OrderStatus } from "@/lib/store";
import { MobileShell, TopBar } from "@/components/MobileShell";
import { ArrowLeft, Check, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { requireAuth } from "@/lib/auth-guard";
import { orderApi, type Order } from "@/lib/api";

export const Route = createFileRoute("/orders/$id")({
  beforeLoad: requireAuth,
  head: () => ({ meta: [{ title: "Tracking order · Zentro" }] }),
  component: OrderPage,
});

const STEPS: { key: OrderStatus; label: string }[] = [
  { key: "pending", label: "Placed" },
  { key: "confirmed", label: "Accepted" },
  { key: "preparing", label: "Brewing" },
  { key: "ready", label: "Ready" },
  { key: "completed", label: "Picked up" },
];

function OrderPage() {
  const { id } = Route.useParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await orderApi.get(id);
      setOrder(data);
      setError("");
    } catch (e: any) {
      setError(e.message || "Failed to load order");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!order || order.status === "completed" || order.status === "cancelled") return;
    const interval = setInterval(() => {
      orderApi.get(id).then(setOrder).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, [order?.status, id]);

  async function handleRefresh() {
    setRefreshing(true);
    await load();
  }

  if (loading) {
    return (
      <MobileShell>
        <TopBar
          right={
            <Link to="/" className="glass grid h-9 w-9 place-items-center rounded-full">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          }
        />
        <div className="flex justify-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </MobileShell>
    );
  }

  if (error || !order) {
    return (
      <MobileShell>
        <TopBar
          right={
            <Link to="/" className="glass grid h-9 w-9 place-items-center rounded-full">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          }
        />
        <div className="px-5">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error || "Order not found"}
            <button onClick={handleRefresh} className="ml-2 underline">Retry</button>
          </div>
        </div>
      </MobileShell>
    );
  }

  const currentIdx = STEPS.findIndex((s) => s.key === order.status);
  const isCancelled = order.status === "cancelled";
  const merchantName = order.merchant_profiles?.store_name;

  return (
    <MobileShell>
      <TopBar
        title={`Order #${order.id.slice(0, 8)}`}
        right={
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              className="glass grid h-9 w-9 place-items-center rounded-full"
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            </button>
            <Link to="/" className="glass grid h-9 w-9 place-items-center rounded-full">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </div>
        }
      />

      <div className="px-5">
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          Order #{order.id.slice(0, 8)}
        </p>
        <h1 className="font-display mt-1 text-4xl text-ink">
          {isCancelled
            ? "Order cancelled"
            : order.status === "completed"
            ? "Enjoy your order"
            : "We're on it"}
        </h1>
        {merchantName && (
          <p className="mt-1 text-sm text-muted-foreground">from {merchantName}</p>
        )}
      </div>

      {isCancelled ? (
        <div className="mt-6 px-5">
          <div className="glass-strong rounded-3xl p-5 text-center">
            <p className="text-4xl">❌</p>
            <p className="mt-3 text-sm text-muted-foreground">This order was cancelled</p>
          </div>
        </div>
      ) : (
        <div className="mt-6 px-5">
          <div className="glass-strong rounded-3xl p-5">
            <ol className="relative space-y-5">
              {STEPS.map((s, i) => {
                const done = i <= currentIdx;
                const active = i === currentIdx;
                return (
                  <li key={s.key} className="flex items-center gap-4">
                    <div
                      className={`grid h-9 w-9 shrink-0 place-items-center rounded-full transition-all ${
                        done ? "bg-ink text-primary-foreground" : "bg-mist text-muted-foreground"
                      } ${active ? "ring-4 ring-ember/20" : ""}`}
                    >
                      {done ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <span className="text-xs">{i + 1}</span>
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className={`text-sm font-medium ${done ? "text-ink" : "text-muted-foreground"}`}>
                        {s.label}
                      </p>
                      {active && order.status !== "completed" && (
                        <p className="mt-0.5 text-xs text-ember">In progress…</p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      )}

      {/* Items */}
      <div className="mt-6 px-5">
        <h2 className="mb-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">Items</h2>
        <div className="glass space-y-2 rounded-2xl p-4">
          {(order.order_items ?? []).map((item, idx) => (
            <div key={idx} className="flex items-center justify-between">
              <span className="text-sm text-ink">
                {item.quantity}× {item.name}
              </span>
              <span className="text-sm text-muted-foreground">
                NPR {Number(item.subtotal).toLocaleString()}
              </span>
            </div>
          ))}
          <div className="!mt-3 border-t border-border pt-3 flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Total</span>
            <span className="font-display text-xl text-ink">
              NPR {Number(order.total_amount).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-4 px-5 pb-8">
        <div className="flex items-center justify-between rounded-2xl bg-ember-soft px-4 py-3">
          <span className="text-xs text-ink">Earned</span>
          <span className="font-display text-lg text-ember">+{order.points_earned} pts</span>
        </div>
      </div>
    </MobileShell>
  );
}