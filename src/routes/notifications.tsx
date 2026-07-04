// routes/notification.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { requireCustomer } from "@/lib/auth-guard";
import { notificationApi, type Notification } from "@/lib/api";
import {
  Bell,
  ShoppingBag,
  Target,
  Gift,
  Stamp,
  Sparkles,
  CheckCheck,
} from "lucide-react";
import type { ComponentType } from "react";

const TYPE_ICON: Record<string, ComponentType<{ className?: string }>> = {
  new_order: ShoppingBag,
  order_status: ShoppingBag,
  mission_completed: Target,
  reward_redeemed: Gift,
  redemption_confirmed: Gift,
  punch_card_completed: Stamp,
  special_offer: Sparkles,
  generic: Bell,
};

function formatWhen(iso: string): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function NotificationsPage() {
  const { data, isLoading, isError, refetch } = useQuery<Notification[]>({
    queryKey: ["notifications", "list"],
    queryFn: notificationApi.list,
    staleTime: 30_000,
    retry: false,
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationApi.markAllRead(),
    onSuccess: () => refetch(),
  });

  const markRead = useMutation({
    mutationFn: (id: string) => notificationApi.markRead(id),
    onSuccess: () => refetch(),
  });

  const unreadCount = data?.filter((n) => !n.is_read).length ?? 0;

  return (
    <div className="mx-auto max-w-3xl px-4 pb-20 pt-6 sm:px-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
            Notifications
          </p>
          <h1 className="font-display mt-2 text-3xl text-ink">
            Activity & updates
          </h1>
        </div>
        {unreadCount > 0 && (
          <button
            type="button"
            onClick={() => markAllRead.mutate()}
            disabled={markAllRead.isPending}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-white px-4 py-2 text-sm font-medium text-ink transition hover:bg-mist disabled:cursor-not-allowed disabled:opacity-50"
          >
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all read
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, index) => (
            <div key={index} className="h-24 animate-pulse rounded-3xl bg-mist" />
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-3xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          Unable to load notifications. Please refresh.
        </div>
      ) : !data || data.length === 0 ? (
        <div className="glass rounded-3xl p-12 text-center">
          <Bell className="mx-auto h-8 w-8 text-muted-foreground" strokeWidth={1.5} />
          <p className="mt-4 text-sm text-muted-foreground">
            Nothing yet — orders, missions, and rewards will show up here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((notification) => {
            const Icon = TYPE_ICON[notification.notification_type] ?? Bell;
            return (
              <div
                key={notification.id}
                className={`rounded-3xl border px-4 py-4 shadow-sm transition ${
                  notification.is_read
                    ? "border-border bg-white"
                    : "border-ember/20 bg-ember/5"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${
                      notification.is_read ? "bg-mist text-muted-foreground" : "gradient-ember text-white"
                    }`}
                  >
                    <Icon className="h-4 w-4" strokeWidth={2} />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-ink">
                        {notification.title}
                      </p>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {formatWhen(notification.created_at)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">
                      {notification.message}
                    </p>

                    <div className="mt-3 flex flex-wrap items-center gap-3">
                      {notification.merchant_name ? (
                        <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                          {notification.merchant_name}
                        </span>
                      ) : null}

                      {notification.context_url ? (
                        
                         <a href={notification.context_url}
                          className="text-xs font-semibold text-ember underline-offset-4 hover:underline"
                        >
                          View details →
                        </a>
                      ) : null}

                      {!notification.is_read ? (
                        <button
                          type="button"
                          onClick={() => markRead.mutate(notification.id)}
                          disabled={markRead.isPending}
                          className="ml-auto rounded-full border border-border bg-white px-3 py-1 text-xs font-semibold text-ink transition hover:bg-mist disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Mark read
                        </button>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export const Route = createFileRoute("/notifications")({
  beforeLoad: requireCustomer,
  head: () => ({ meta: [{ title: "Notifications · Zentro" }] }),
  component: NotificationsPage,
});