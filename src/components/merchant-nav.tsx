import { Link, useRouterState } from "@tanstack/react-router";
import { LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

interface MerchantNavProps {
  navItems: NavItem[];
  onSignOut: () => void;
  onLinkClick?: () => void;
}

export function MerchantNav({ navItems, onSignOut, onLinkClick }: MerchantNavProps) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="flex h-full flex-col gap-1 p-4">
      {/* Logo */}
      <Link
        to="/"
        className="mb-4 flex items-center px-2 py-1 font-display text-2xl text-ink"
        onClick={onLinkClick}
      >
        zentro<span className="text-ember">.</span>
      </Link>

      {/* Nav links */}
      <nav className="flex flex-1 flex-col gap-1">
        {navItems.map(({ to, label, icon: Icon }) => {
          const isActive =
            to === "/merchant/"
              ? pathname === "/merchant" || pathname === "/merchant/"
              : pathname.startsWith(to);

          return (
            <Link
              key={to}
              to={to as any}
              onClick={onLinkClick}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-ink text-primary-foreground"
                  : "text-muted-foreground hover:bg-mist hover:text-ink"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Sign out */}
      <button
        onClick={onSignOut}
        className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-mist hover:text-ink"
      >
        <LogOut className="h-4 w-4 shrink-0" />
        Sign out
      </button>
    </div>
  );
}