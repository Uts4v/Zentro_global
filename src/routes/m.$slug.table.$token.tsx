// routes/m.$slug.table.$token.tsx — Table QR scan entry point
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2, ArrowRight, MapPin, Utensils } from "lucide-react";
import { tableApi, type TableResolution } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useStore } from "@/lib/store";

export const Route = createFileRoute("/m/$slug/table/$token")({
  head: () => ({ meta: [{ title: "Table Order · Zentro" }] }),
  component: TableQRScanPage,
});

function TableQRScanPage() {
  const params = Route.useParams();
  const slug = params.slug;
  const token = params.token;
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const { setActiveTable, setSelectedMerchant, cart, activeTable } = useStore();

  const [resolution, setResolution] = useState<TableResolution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Resolve the table token
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    tableApi
      .resolve(slug, token)
      .then((r) => {
        if (!cancelled) setResolution(r);
      })
      .catch(() => {
        if (!cancelled) setError("Invalid or expired table QR code. Please scan again.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [slug, token]);

  // Once resolved, set context and redirect
  useEffect(() => {
    if (authLoading || loading || !resolution) return;

    const tableCtx = {
      merchantSlug: slug,
      tableToken: token,
      tableId: resolution.table.id,
      tableName: resolution.table.name,
      scannedAt: Date.now(),
    };

    // Set the active table context and merchant
    setActiveTable(tableCtx);
    setSelectedMerchant(String(resolution.merchant.id));

    // If logged in, go directly to merchant menu
    if (user?.role === "customer") {
      navigate({
        to: "/customer/merchant/$slug",
        params: { slug },
        replace: true,
      });
      return;
    }

    // If merchant, redirect away
    if (user?.role === "merchant") {
      navigate({ to: "/merchant", replace: true });
      return;
    }

    // Guest — show the table info page (they can browse menu without login)
  }, [authLoading, loading, resolution, user, slug, token, navigate, setActiveTable, setSelectedMerchant]);

  // Loading state
  if (loading || authLoading) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (error || !resolution) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 px-5 text-center">
        <p className="text-4xl">🪑</p>
        <p className="text-sm text-muted-foreground">{error ?? "Table not found."}</p>
        <Link
          to="/"
          className="text-sm font-medium text-foreground underline-offset-4 hover:underline"
        >
          Back to home
        </Link>
      </div>
    );
  }

  const dashboardPath = `/customer/merchant/${slug}`;
  const merchant = resolution.merchant;
  const table = resolution.table;

  // Guest landing — show table info with login CTA
  return (
    <div className="mx-auto flex min-h-dvh max-w-[480px] flex-col px-5 pb-10 pt-10">
      <Link to="/" className="font-display text-2xl text-foreground">
        zentro<span className="text-ember">.</span>
      </Link>

      <div className="mt-12">
        <div
          className="grid h-16 w-16 place-items-center rounded-3xl text-3xl text-primary-foreground shadow-soft"
          style={{
            ...(merchant.logo
              ? {
                  backgroundImage: `url(${merchant.logo})`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                }
              : { backgroundColor: "var(--ink)" }),
          }}
        >
          {!merchant.logo && <Utensils className="h-7 w-7" />}
        </div>

        <p className="mt-6 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          Dine-in · {table.name}
        </p>
        <h1 className="font-display mt-2 text-5xl leading-[1.05] text-foreground">
          {merchant.name}
        </h1>
        <p className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
          <Utensils className="h-4 w-4 shrink-0" /> Scan to view menu and order
        </p>
      </div>

      <div className="mt-10 glass-strong rounded-3xl p-6">
        <p className="font-display text-2xl text-foreground">Ready to order?</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Sign up or sign in to browse the menu, place orders, and earn loyalty points at {merchant.name}.
        </p>

        {/* Show current table info */}
        <div className="mt-4 rounded-2xl bg-muted/50 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
              <Utensils className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">{table.name}</p>
              <p className="text-xs text-muted-foreground">Your current table</p>
            </div>
          </div>
        </div>

        <Link
          to="/auth"
          search={{ redirect: dashboardPath }}
          className="mt-5 inline-flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-foreground text-sm font-medium text-background"
        >
          Sign up / Sign in <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
