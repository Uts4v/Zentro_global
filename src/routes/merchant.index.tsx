// C:\Users\ACER\Desktop\NTE Loyalty\zentro-glow-loyalty\src\routes\merchant.index.tsx
import { createFileRoute } from "@tanstack/react-router";
import {
  TrendingUp,
  Users,
  Coffee,
  Loader2,
  Activity,
  ShoppingBag,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { analyticsApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/merchant/")({
  head: () => ({ meta: [{ title: "Overview · Merchant · Zentro" }] }),
  component: Overview,
});

interface TopItem {
  id: string;
  name: string;
  emoji: string;
  sold: number;
}

interface OverviewStats {
  hourly_velocity: { hour: string; count: number }[];
  velocity_change: number;
  active_members: number;
  today: { orders: number; revenue: number };
}

// Build a today-centric OverviewStats from the Django analytics response
function buildOverviewStats(data: any): OverviewStats {
  const daily: any[] = data.daily_revenue ?? [];
  const todayStr = new Date().toISOString().slice(0, 10);
  const todayRow = daily.find((d: any) => d.date === todayStr);

  // Hourly velocity: use daily_revenue as a proxy (last 12 entries → last 12 days)
  // Django doesn't yet expose hourly granularity — we use daily points as bars.
  const velocity = daily.slice(-12).map((d: any) => ({
    hour: d.date,
    count: Number(d.orders ?? 0),
  }));

  const prev = daily.length >= 2 ? Number(daily[daily.length - 2]?.revenue ?? 0) : 0;
  const curr = todayRow ? Number(todayRow.revenue ?? 0) : 0;
  const velocityChange = prev > 0 ? Math.round(((curr - prev) / prev) * 100) : 0;

  return {
    hourly_velocity: velocity,
    velocity_change: velocityChange,
    active_members: data.top_customers?.length ?? 0,
    today: {
      orders: todayRow ? Number(todayRow.orders ?? 0) : 0,
      revenue: todayRow ? Number(todayRow.revenue ?? 0) : 0,
    },
  };
}

function formatMoney(value: number | string | null | undefined) {
  return `NPR ${Number(value ?? 0).toLocaleString()}`;
}

function getGreeting() {
  const hour = new Date().getHours();

  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";

  return "Good evening";
}

function Overview() {
  const { merchantProfile } = useAuth();

  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [topItems, setTopItems] = useState<TopItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!merchantProfile?.id) return;

    let cancelled = false;

    async function loadOverview() {
      setLoading(true);
      setError("");

      try {
        const data = await analyticsApi.merchant(30);
        if (cancelled) return;

        setStats(buildOverviewStats(data));

        // Top items from Django analytics
        const rankedItems = (data.top_items ?? [])
          .slice(0, 4)
          .map((item: any, index: number) => ({
            id: `${index}-${item.name}`,
            name: item.name,
            emoji: "☕",
            sold: item.total_qty ?? 0,
          }));
        setTopItems(rankedItems);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load merchant overview");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadOverview();

    return () => {
      cancelled = true;
    };
  }, [merchantProfile?.id]);

  const today = stats?.today ?? {
    orders: 0,
    revenue: 0,
  };

  const activeMembers = stats?.active_members ?? 0;
  const velocity = stats?.hourly_velocity ?? [];
  const velocityChange = stats?.velocity_change ?? 0;

  const averageOrderValue =
    today.orders > 0 ? Number(today.revenue ?? 0) / today.orders : 0;

  const maxVelocity = Math.max(...velocity.map((item) => item.count), 1);

  const statCards = useMemo(
    () => [
      {
        label: "Today's revenue",
        value: formatMoney(today.revenue),
        icon: TrendingUp,
      },
      {
        label: "Orders today",
        value: String(today.orders),
        icon: Coffee,
      },
      {
        label: "Active members",
        value: String(activeMembers),
        icon: Users,
      },
      {
        label: "Average order",
        value: formatMoney(averageOrderValue),
        icon: ShoppingBag,
      },
    ],
    [today.orders, today.revenue, activeMembers, averageOrderValue],
  );

  if (!merchantProfile || loading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-700">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="glass-strong rounded-[2rem] p-6 sm:p-8">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              {new Date().toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}
            </p>

            <h1 className="font-display mt-3 text-4xl leading-tight text-ink sm:text-5xl">
              {getGreeting()}, {(merchantProfile.business_name ?? "there").split(" ")[0]}.
            </h1>

            <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
              Your store has received{" "}
              <span className="font-medium text-ink">{today.orders}</span>{" "}
              orders today with{" "}
              <span className="font-medium text-ink">
                {formatMoney(today.revenue)}
              </span>{" "}
              in revenue.
            </p>
          </div>

          <div className="inline-flex w-fit items-center gap-2 rounded-full bg-mist px-4 py-2">
            <Activity className="h-4 w-4 text-ink" />
            <span className="text-xs font-medium text-ink">
              {velocityChange >= 0 ? "+" : ""}
              {velocityChange}% order velocity
            </span>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {statCards.map((card) => {
          const Icon = card.icon;

          return (
            <div key={card.label} className="glass-strong rounded-3xl p-5">
              <div className="grid h-10 w-10 place-items-center rounded-full bg-mist">
                <Icon className="h-4 w-4 text-ink" />
              </div>

              <p className="mt-5 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {card.label}
              </p>

              <p className="font-display mt-1 truncate text-2xl text-ink sm:text-3xl">
                {card.value}
              </p>
            </div>
          );
        })}
      </section>

      <section className="grid gap-3 lg:grid-cols-3">
        <div className="glass-strong rounded-3xl p-6 lg:col-span-2">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                Last 12 days
              </p>
              <h2 className="font-display mt-1 text-2xl text-ink">
                Order trend
              </h2>
            </div>

            <span
              className={`font-display text-3xl ${
                velocityChange >= 0 ? "text-ember" : "text-muted-foreground"
              }`}
            >
              {velocityChange >= 0 ? "+" : ""}
              {velocityChange}%
            </span>
          </div>

          {velocity.length === 0 || velocity.every((item) => item.count === 0) ? (
            <div className="mt-6 flex h-44 items-center justify-center rounded-3xl bg-mist/50 text-sm text-muted-foreground">
              No orders in the last 12 hours
            </div>
          ) : (
            <div className="mt-6 flex h-44 items-end gap-2 rounded-3xl bg-mist/40 px-4 py-4">
              {velocity.map((item, index) => {
                const height =
                  item.count > 0
                    ? Math.max((item.count / maxVelocity) * 100, 10)
                    : 3;

                const hourLabel = new Date(item.hour).toLocaleDateString(
                  "en-US",
                  { month: "short", day: "numeric" },
                );

                return (
                  <div
                    key={item.hour}
                    className="group flex flex-1 flex-col items-center justify-end gap-2"
                    title={`${item.count} order${
                      item.count === 1 ? "" : "s"
                    } at ${hourLabel}`}
                  >
                    <div
                      className="w-full rounded-t-xl gradient-ember transition-all duration-300 group-hover:opacity-90"
                      style={{
                        height: `${height}%`,
                        opacity: 0.35 + (index / velocity.length) * 0.65,
                      }}
                    />

                    <span className="hidden text-[10px] text-muted-foreground sm:block">
                      {hourLabel}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="glass-strong rounded-3xl p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                Menu performance
              </p>
              <h2 className="font-display mt-1 text-2xl text-ink">
                Top sellers
              </h2>
            </div>
          </div>

          <ul className="mt-5 space-y-3">
            {topItems.map((item, index) => (
              <li key={item.id} className="flex items-center gap-3">
                <span className="font-display w-5 text-sm text-muted-foreground">
                  {index + 1}
                </span>

                <div className="grid h-10 w-10 place-items-center rounded-2xl bg-mist text-xl">
                  {item.emoji}
                </div>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">
                    {item.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {item.sold} sold
                  </p>
                </div>
              </li>
            ))}

            {topItems.length === 0 && (
              <li className="rounded-3xl bg-mist/50 px-4 py-6 text-center text-sm text-muted-foreground">
                No top sellers yet
              </li>
            )}
          </ul>
        </div>
      </section>
    </div>
  );
}