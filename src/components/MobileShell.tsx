import { Link, useRouterState } from "@tanstack/react-router";
import { Home, ScanLine, Trophy, Gift, User } from "lucide-react";
import type { ReactNode } from "react";

type NavItem = { to: string; label: string; icon: typeof Home; center?: boolean };
const nav: NavItem[] = [
  { to: "/", label: "Shop", icon: Home },
  { to: "/missions", label: "Missions", icon: ScanLine },
  { to: "/loyalty", label: "Card", icon: User, center: true },
  { to: "/rewards", label: "Rewards", icon: Gift },
  { to: "/leaderboard", label: "Ranks", icon: Trophy },
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

export function TopBar({ title, right }: { title?: string; right?: ReactNode }) {
  return (
    <header className="sticky top-0 z-40 flex items-center justify-between px-5 pb-3 pt-5">
      <Link to="/" className="font-display text-2xl tracking-tight text-ink">
        zentro<span className="text-ember">.</span>
      </Link>
      {title && <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{title}</p>}
      <div className="flex items-center gap-2">
        {right}
        <Link
          to={"/profile" as any}
          className="grid h-9 w-9 place-items-center rounded-full bg-ink text-xs font-medium text-primary-foreground"
          aria-label="Profile"
        >
          ✦
        </Link>
      </div>
    </header>
  );
}

