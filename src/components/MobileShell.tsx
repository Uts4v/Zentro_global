// src/MobileShrell.tsx 
import { Link, useRouterState } from "@tanstack/react-router";
import { Home, ScanLine, Trophy, Gift, User, Bell } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useQuery } from "@tanstack/react-query";
import { notificationApi } from "@/lib/api";
import type { ReactNode } from "react";

type NavItem = { to: string; label: string; icon: typeof Home; center?: boolean };
const nav: NavItem[] = [
  { to: "/",            label: "Shop",    icon: Home },
  { to: "/missions",    label: "Missions", icon: ScanLine },
  { to: "/loyalty",     label: "Card",    icon: User, center: true },
  { to: "/rewards",     label: "Rewards", icon: Gift },
  { to: "/leaderboard", label: "Ranks",   icon: Trophy },
];

export function MobileShell({ children }: { children: ReactNode }) {
  const path = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="mx-auto flex min-h-dvh max-w-[480px] flex-col pb-28">
      {children}
      <nav className="fixed inset-x-0 bottom-3 z-50 mx-auto flex max-w-[440px] items-center justify-between px-4">
        <div className="glass-strong flex w-full items-center justify-between rounded-full px-2 py-2">
          {nav.map((n) => {
            const active = path === n.to;
            const Icon = n.icon;
            if (n.center) {
              return (
                <Link
                  key={n.to}
                  to={n.to as any}
                  className="relative -mt-8 grid h-14 w-14 shrink-0 place-items-center rounded-full gradient-ember text-white shadow-ember"
                  aria-label={n.label}
                >
                  <Icon className="h-5 w-5" strokeWidth={2} />
                </Link>
              );
            }
            return (
              <Link
                key={n.to}
                to={n.to as any}
                className={`flex h-11 flex-1 flex-col items-center justify-center gap-0.5 rounded-full text-[10px] font-medium transition-colors ${
                  active ? "text-ink" : "text-muted-foreground"
                }`}
              >
                <Icon className="h-[18px] w-[18px]" strokeWidth={1.6} />
                <span className="tracking-wide">{n.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function getInitial(name: string | null | undefined): string {
  if (!name) return "✦";
  return name.trim().charAt(0).toUpperCase();
}

export function TopBar({ title, right }: { title?: string; right?: ReactNode }) {
  const { user, loading } = useAuth();
  const { data } = useQuery({
    queryKey: ["notifications", "unreadCount"],
    queryFn: () => notificationApi.unreadCount(),
    enabled: Boolean(user),
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: false,
  });

  const unreadCount = data?.unread_count ?? 0;
  const firstName = user?.first_name ?? null;
  const initial   = getInitial(user?.first_name);
  const greeting  = getGreeting();

  return (
    <header className="sticky top-0 z-40 px-5 pb-3 pt-5">
      <div className="flex items-center justify-between">
        {/* Left: logo */}
        <Link to="/" className="font-display text-2xl tracking-tight text-ink">
          zentro<span className="text-ember">.</span>
        </Link>

        {title && (
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
            {title}
          </p>
        )}

        {/* Right: avatar + notifications */}
        <div className="flex items-center gap-2">
          {right}
          <Link
            to={'/notifications' as any}
            aria-label="Notifications"
            className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full border border-border text-muted-foreground hover:bg-mist"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 ? (
              <span className="absolute -top-1 -right-1 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-ember px-1.5 text-[10px] font-semibold text-white">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            ) : null}
          </Link>
          <Link
            to={'/profile' as any}
            aria-label="Profile"
            className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full bg-ink text-xs font-medium text-primary-foreground overflow-hidden"
          >
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={`${user?.first_name} ${user?.last_name}`}
                className="h-full w-full object-cover"
              />
            ) : (
              <span>{initial}</span>
            )}
          </Link>
        </div>
      </div>

      {/* Welcome row — only shown on home page (no title passed) */}
      {!title && (
        <div className="mt-3">
          {loading ? (
            <div className="h-4 w-32 animate-pulse rounded-full bg-mist" />
          ) : (
            <p className="text-sm text-muted-foreground">
              {greeting}
              {firstName ? (
                <>
                  ,{" "}
                  <span className="font-medium text-ink">{firstName}</span>
                </>
              ) : null}{" "}
              👋
            </p>
          )}
        </div>
      )}
    </header>
  );
}