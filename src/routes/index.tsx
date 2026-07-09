// routes/index.tsx 
import { createFileRoute, Link } from "@tanstack/react-router";
import { useStore, cartTotal, type MenuItem } from "@/lib/store";
import { merchantApi, menuApi, customerApi, specialApi, type TodaySpecial } from "@/lib/api";
import { MobileShell, TopBar } from "@/components/MobileShell";
import { Plus, ShoppingBag, Flame, Search, X as XIcon } from "lucide-react";
import { requireAuth } from "@/lib/auth-guard";
import { useState, useEffect, useMemo } from "react";
import { TodaySpecialPopup } from "@/features/merchant-management/components/TodaySpecialPopup";

export const Route = createFileRoute("/")({
  beforeLoad: requireAuth,
  head: () => ({
    meta: [
      { title: "Zentro — Order" },
      { name: "description", content: "Browse the menu, order, and collect points." },
    ],
  }),
  component: Index,
});

function MenuItemCard({
  item,
  onAdd,
  disabled,
}: {
  item: MenuItem;
  onAdd: () => void;
  disabled: boolean;
}) {
  const [imgError, setImgError] = useState(false);
  const hasImage = !!item.image_url && !imgError;
  const price = parseFloat(item.price as any);

  return (
    <article className="glass group relative flex flex-col rounded-3xl overflow-hidden">
      {hasImage ? (
        <img
          src={item.image_url ?? undefined}
          alt={item.name}
          className="h-32 w-full object-cover"
          onError={() => setImgError(true)}
          loading="lazy"
        />
      ) : (
        <div className="mb-0 grid h-24 place-items-center rounded-t-3xl bg-mist text-5xl">
          {item.emoji || "☕"}
        </div>
      )}
      <div className="flex flex-1 flex-col p-4">
        <h3 className="text-sm font-semibold text-ink">{item.name}</h3>
        <p className="mt-0.5 line-clamp-2 text-[11px] text-muted-foreground">{item.description}</p>
        <div className="mt-3 flex items-center justify-between">
          <span className="font-display text-xl text-ink">
            NPR {price.toLocaleString()}
          </span>
          <button
            onClick={onAdd}
            disabled={disabled}
            className="grid h-9 w-9 place-items-center rounded-full bg-ink text-primary-foreground transition-transform active:scale-90 disabled:opacity-40"
            aria-label={`Add ${item.name}`}
          >
            <Plus className="h-4 w-4" strokeWidth={2.4} />
          </button>
        </div>
      </div>
    </article>
  );
}

function Index() {
  const { cart, add, selectedMerchantId, setSelectedMerchant } = useStore();
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [merchantName, setMerchantName] = useState("Select a store");
  const [merchantSlug, setMerchantSlug] = useState<string | null>(null);
  const [points, setPoints] = useState(0);
  const [streak, setStreak] = useState(0);
  const [loading, setLoading] = useState(true);
  const [cat, setCat] = useState<string>("All");
  const [search, setSearch] = useState("");
  const [todaySpecial, setTodaySpecial] = useState<TodaySpecial | null>(null);

  useEffect(() => {
    if (!selectedMerchantId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([
      menuApi.forMerchant(selectedMerchantId)
        .then((items) => setMenuItems(items.map((i) => ({ ...i, price: parseFloat(i.price as any) }))))
        .catch(() => setMenuItems([])),
      merchantApi.get(selectedMerchantId)
        .then((m) => {
          setMerchantName(m.business_name);
          setMerchantSlug(m.slug ?? null);
        })
        .catch(() => setSelectedMerchant(null)),
      customerApi.getWallet(selectedMerchantId)
        .then((w) => {
          setPoints(w?.points_balance ?? 0);
          setStreak(w?.streak_days ?? 0);
        })
        .catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [selectedMerchantId]);

  useEffect(() => {
    if (!merchantSlug) {
      setTodaySpecial(null);
      return;
    }
    specialApi.forSlug(merchantSlug)
      .then((s) => setTodaySpecial(s))
      .catch(() => setTodaySpecial(null));
  }, [merchantSlug]);

  const cats = useMemo(() => (
    ["All", ...Array.from(new Set(menuItems.map((m) => m.category).filter(Boolean)))]
  ), [menuItems]);

  const filteredItems = useMemo(() => {
    let result = cat === "All" ? menuItems : menuItems.filter((m) => m.category === cat);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(
        (m) =>
          m.name.toLowerCase().includes(q) ||
          (m.description ?? "").toLowerCase().includes(q)
      );
    }
    return result;
  }, [menuItems, cat, search]);

  const count = cart.reduce((s, c) => s + c.qty, 0);
  const storeItems = menuItems.map((m) => ({ ...m, price: parseFloat(m.price as any) }));
  const total = cartTotal(cart, storeItems);

  return (
    <MobileShell>
      <TopBar />

      {/* Today's Special popup — shown once per session when merchant has an active special */}
      {merchantSlug && (
        <TodaySpecialPopup slug={merchantSlug} />
      )}

      {/* Merchant hero */}
      <section className="px-5">
        <div className="glass-strong relative overflow-hidden rounded-[28px] p-6">
          <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full gradient-ember opacity-30 blur-3xl" />
          <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            {selectedMerchantId ? "Now open" : "Select a store to start"}
          </p>
          <h1 className="font-display mt-2 text-[44px] leading-[1] text-ink">{merchantName}</h1>
          {selectedMerchantId && (
            <div className="mt-5 flex items-center gap-2">
              <span className="glass inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs">
                <Flame className="h-3 w-3 stroke-ember" /> {streak}-day streak
              </span>
              <span className="glass inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs">
                ✦ {points} pts
              </span>
            </div>
          )}
          {!selectedMerchantId && (
            <p className="mt-2 text-sm text-muted-foreground">
              <Link to="/map" className="text-ember underline">Browse stores</Link> to start ordering.
            </p>
          )}
        </div>
      </section>

      {/* Today's Special Banner */}
      {selectedMerchantId && todaySpecial && (
        <section className="px-5 mt-4">
          <div className="glass-strong relative overflow-hidden rounded-[28px] border border-ember/20 p-5 bg-gradient-to-br from-amber-500/10 to-ember/5">
            <div className="flex gap-4">
              {todaySpecial.image_url && (
                <img
                  src={todaySpecial.image_url}
                  alt={todaySpecial.title}
                  className="h-20 w-20 rounded-2xl object-cover shrink-0"
                />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[9px] uppercase tracking-[0.2em] text-ember font-semibold bg-ember-soft px-2 py-0.5 rounded-full">
                    🔥 Today's Special
                  </span>
                </div>
                <h3 className="font-display mt-2 text-xl text-ink leading-tight truncate">
                  {todaySpecial.title}
                </h3>
                {todaySpecial.description && (
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                    {todaySpecial.description}
                  </p>
                )}
                {(todaySpecial.linked_menu_item_name || todaySpecial.linked_reward_name) && (
                  <span className="mt-2 inline-flex items-center gap-1 text-[10px] text-ember font-medium">
                    ✨ Linked: {todaySpecial.linked_menu_item_name ?? todaySpecial.linked_reward_name}
                  </span>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Search bar */}
      {selectedMerchantId && menuItems.length > 0 && (
        <div className="mt-4 px-5">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search menu…"
              className="h-11 w-full rounded-2xl bg-mist pl-10 pr-10 text-sm text-ink placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-ink/20"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-ink"
              >
                <XIcon className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Category filter */}
      {menuItems.length > 0 && !search && (
        <div className="no-scrollbar mt-4 flex gap-2 overflow-x-auto px-5 pb-1">
          {cats.map((c) => (
            <button
              key={c}
              onClick={() => setCat(c)}
              className={`shrink-0 rounded-full px-4 py-2 text-xs font-medium transition-all ${
                cat === c
                  ? "bg-ink text-primary-foreground shadow-soft"
                  : "glass text-muted-foreground"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      {/* Search result count */}
      {search && (
        <p className="mt-2 px-5 text-xs text-muted-foreground">
          {filteredItems.length} result{filteredItems.length !== 1 ? "s" : ""} for &quot;{search}&quot;
        </p>
      )}

      {/* Menu */}
      <section className="mt-3 grid grid-cols-2 gap-3 px-5 pb-32">
        {loading && selectedMerchantId && (
          <p className="col-span-2 text-center text-sm text-muted-foreground">Loading menu…</p>
        )}
        {!loading && menuItems.length === 0 && selectedMerchantId && (
          <p className="col-span-2 text-center text-sm text-muted-foreground">No menu items available.</p>
        )}
        {!selectedMerchantId && (
          <p className="col-span-2 text-center text-sm text-muted-foreground">
            Select a store to see the menu.
          </p>
        )}
        {search && filteredItems.length === 0 && (
          <p className="col-span-2 text-center text-sm text-muted-foreground">
            No items match &quot;{search}&quot;
          </p>
        )}
        {filteredItems.map((m) => (
          <MenuItemCard
            key={m.id}
            item={m}
            onAdd={() => add(m.id)}
            disabled={!selectedMerchantId}
          />
        ))}
      </section>

      {/* Floating cart bar */}
      {count > 0 && (
        <Link
          to="/cart"
          className="fixed inset-x-0 bottom-24 z-40 mx-auto flex max-w-[440px] items-center justify-between rounded-full bg-ink px-5 py-3 text-primary-foreground shadow-ember"
          style={{ marginLeft: "auto", marginRight: "auto", width: "calc(100% - 32px)" }}
        >
          <span className="flex items-center gap-2 text-sm font-medium">
            <ShoppingBag className="h-4 w-4" /> {count} {count === 1 ? "item" : "items"}
          </span>
          <span className="font-display text-lg">NPR {total.toLocaleString()} →</span>
        </Link>
      )}
    </MobileShell>
  );
}