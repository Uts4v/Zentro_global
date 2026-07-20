// src/components/MobileShell.tsx
import { Link, useRouterState } from "@tanstack/react-router";
import { Home, Map, ScanLine, Gift, User, Bell, Sun, Moon } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { useQuery } from "@tanstack/react-query";
import { notificationApi } from "@/lib/api";
import type { ReactNode } from "react";

type NavItem = { to: string; label: string; icon: typeof Home; center?: boolean };
const nav: NavItem[] = [
  { to: "/", label: "Home", icon: Home },
  { to: "/map", label: "Discover", icon: Map },
  { to: "/cards", label: "Scan QR", icon: ScanLine, center: true },
  { to: "/rewards", label: "Rewards", icon: Gift },
  { to: "/profile", label: "Profile", icon: User },
];

export function MobileShell({ children }: { children: ReactNode }) {
  const path = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="mx-auto flex min-h-dvh max-w-[430px] flex-col bg-[#FAF8F4] pb-28">
      {children}
      <nav className="fixed inset-x-0 bottom-0 z-50 mx-auto max-w-[430px]">
        <div
          className="mx-3 mb-3 flex items-center justify-between rounded-[22px] bg-white px-2 py-2"
          style={{
            boxShadow:
              "0 1px 3px rgba(0,0,0,0.04), 0 10px 40px -8px rgba(0,0,0,0.08)",
          }}
        >
          {nav.map((n) => {
            const active = n.to === "/" ? path === n.to : path.startsWith(n.to);
            const Icon = n.icon;

            if (n.center) {
              return (
                <Link
                  key={n.to}
                  to={n.to as any}
                  className="relative -mt-7 grid h-[52px] w-[52px] shrink-0 place-items-center rounded-full text-white transition-transform active:scale-90"
                  style={{
                    background: "linear-gradient(135deg, #E85D3A 0%, #D44828 100%)",
                    boxShadow: "0 4px 16px rgba(232,93,58,0.35), 0 1px 4px rgba(232,93,58,0.2)",
                  }}
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
                className={`flex h-12 flex-1 flex-col items-center justify-center gap-0.5 rounded-xl text-[10px] font-medium transition-colors ${
                  active ? "text-[#1A1A1A]" : "text-[#1A1A1A]/35"
                }`}
              >
                <Icon className="h-[18px] w-[18px]" strokeWidth={active ? 2 : 1.4} />
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
  const initial = getInitial(user?.first_name);
  const greeting = getGreeting();
  const { resolved, setTheme, theme } = useTheme();

  function cycleTheme() {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  }

  return (
    <header className="relative z-40 px-5 pb-4 pt-6">
      <div className="flex items-center justify-between">
        {/* Left: branding */}
        <Link to="/" className="font-display text-[26px] tracking-tight text-[#1A1A1A]">
          zentro<span className="text-[#E85D3A]">.</span>
        </Link>

        {title && (
          <p className="text-xs uppercase tracking-[0.18em] text-[#1A1A1A]/40">{title}</p>
        )}

        {/* Right: theme, notifications, avatar */}
        <div className="flex items-center gap-2">
          {right}
          <button
            onClick={cycleTheme}
            aria-label="Toggle theme"
            className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#F5F3EF] text-[#1A1A1A]/50 transition-colors hover:bg-[#EDEBE7]"
          >
            {resolved === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </button>
          <Link
            to={"/notifications" as any}
            aria-label="Notifications"
            className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#F5F3EF] text-[#1A1A1A]/50 transition-colors hover:bg-[#EDEBE7]"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 ? (
              <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-[#E85D3A] px-1 text-[9px] font-bold text-white">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            ) : null}
          </Link>
          <Link
            to={"/profile" as any}
            aria-label="Profile"
            className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#1A1A1A] text-xs font-medium text-white overflow-hidden"
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

      {/* Greeting */}
      {!title && (
        <div className="mt-3">
          {loading ? (
            <div className="h-4 w-32 animate-pulse rounded-full bg-[#F5F3EF]" />
          ) : (
            <p className="text-[13px] text-[#1A1A1A]/50">
              {greeting},{" "}
              <span className="font-semibold text-[#1A1A1A]">{firstName || "there"}</span> 👋
            </p>
          )}
        </div>
      )}
    </header>
  );
}
