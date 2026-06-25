import { createFileRoute, Link } from "@tanstack/react-router";
import { MobileShell, TopBar } from "@/components/MobileShell";
import { Search, Star, MapPin, Loader2 } from "lucide-react";
import { requireAuth } from "@/lib/auth-guard";
import { merchantApi, type MerchantProfile } from "@/lib/api";
import { useState, useEffect } from "react";

export const Route = createFileRoute("/stores")({
  beforeLoad: requireAuth,
  head: () => ({ meta: [{ title: "Discover · Zentro" }] }),
  component: Stores,
});

const GRADIENTS = [
  "from-ember/40 to-ember-soft",
  "from-stone-300 to-stone-100",
  "from-emerald-200 to-emerald-50",
  "from-amber-200 to-amber-50",
  "from-violet-200 to-violet-50",
  "from-sky-200 to-sky-50",
];

function Stores() {
  const [merchants, setMerchants] = useState<MerchantProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await merchantApi.list();
      // Handle paginated response (DRF PageNumberPagination)
      const merchants = Array.isArray(data) ? data : (data as any).results ?? [];
      setMerchants(merchants);
    } catch (e: any) {
      setError(e.message || "Failed to load stores");
    } finally {
      setLoading(false);
    }
  }

const filtered = merchants.filter(
  (m) =>
    m.store_name.toLowerCase().includes(search.toLowerCase()) ||
    (m.business_type ?? "").toLowerCase().includes(search.toLowerCase())
);
  return (
    <MobileShell>
      <TopBar />
      <div className="px-5">
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Nearby</p>
        <h1 className="font-display mt-1 text-4xl text-ink">Find your next favorite</h1>
      </div>

      <div className="mt-5 px-5">
        <div className="glass flex items-center gap-2 rounded-full px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search cafés, bakeries…"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
        </div>
      </div>

      <section className="mt-6 space-y-3 px-5 pb-8">
        {loading ? (
          <div className="flex justify-center py-24">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
            <button onClick={load} className="ml-2 underline">Retry</button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="glass rounded-3xl py-20 text-center">
            <p className="text-4xl">🏪</p>
            <p className="mt-3 text-sm text-muted-foreground">
              {merchants.length === 0 ? "No stores yet — check back soon!" : "No stores match your search"}
            </p>
          </div>
        ) : (
          filtered.map((m, i) => (
            <Link
              key={m.id}
              to="/stores/$id"
              params={{ id: String(m.id) }}
              className="glass-strong block overflow-hidden rounded-3xl"
>
              <div
                className={`h-28 bg-gradient-to-br ${GRADIENTS[i % GRADIENTS.length]} grid place-items-center text-6xl`}
              >
                {m.logo_url ? (
                  <img src={m.logo_url} alt={m.store_name} className="h-16 w-16 rounded-2xl object-cover" />
                ) : (
                  <span>{getEmoji(m.business_type)}</span>
                )}
              </div>
              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="truncate text-base font-semibold text-ink">{m.store_name}</h3>
                    <p className="truncate text-xs text-muted-foreground">{m.business_type || "Café"}</p>
                  </div>
                  <span
                    className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-[11px] font-medium ${
                      m.is_open ? "bg-emerald-100 text-emerald-700" : "bg-mist text-muted-foreground"
                    }`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${m.is_open ? "bg-emerald-500" : "bg-muted-foreground"}`} />
                    {m.is_open ? "Open" : "Closed"}
                  </span>
                </div>
                {m.address && (
                  <div className="mt-3 flex items-center gap-3 text-[11px] text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3 w-3" /> {m.address}
                    </span>
                  </div>
                )}
                {m.description && (
                  <p className="mt-2 line-clamp-1 text-xs text-muted-foreground">{m.description}</p>
                )}
              </div>
            </Link>
          ))
        )}
      </section>
    </MobileShell>
  );
}

function getEmoji(businessType: string): string {
  const t = businessType?.toLowerCase() || "";
  if (t.includes("bakery") || t.includes("pastry")) return "🥐";
  if (t.includes("matcha") || t.includes("tea")) return "🍵";
  if (t.includes("roaster") || t.includes("coffee")) return "🫘";
  return "☕";
}
