// routes/index.tsx 
import { createFileRoute, Link } from "@tanstack/react-router";
import { useStore, cartTotal, type MenuItem } from "@/lib/store";
import { merchantApi, menuApi, customerApi, specialApi, punchCardApi, missionApi, type TodaySpecial, type CustomerPunchCard, type MissionView } from "@/lib/api";
import { MobileShell, TopBar } from "@/components/MobileShell";
import { Plus, ShoppingBag, Flame, Search, X as XIcon, ArrowLeftRight, QrCode, SendHorizontal, UserPlus, Loader2 } from "lucide-react";
import { requireAuth } from "@/lib/auth-guard";
import { lazy, Suspense, useState, useEffect, useMemo } from "react";
import { TodaySpecialPopup } from "@/features/merchant-management/components/TodaySpecialPopup";
import { TransferForm } from "@/features/transfers/components/TransferForm";
import { PremiumPunchCard } from "@/components/PremiumPunchCard";
import { PunchCardProofModal } from "@/components/PunchCardProofModal";
import { useMerchantTheme, withAlpha } from "@/lib/merchant-theme";

const PersonalQR = lazy(() => import("@/features/transfers/components/PersonalQR").then(m => ({ default: m.PersonalQR })));

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
        <h3 className="text-sm font-semibold text-foreground">{item.name}</h3>
        <p className="mt-0.5 line-clamp-2 text-[11px] text-muted-foreground">{item.description}</p>
        <div className="mt-3 flex items-center justify-between">
          <span className="font-display text-xl text-foreground">
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
  const [showTransfer, setShowTransfer] = useState(false);
  const [transferMode, setTransferMode] = useState<"send" | "receive">("send");
  const [punchCards, setPunchCards] = useState<{ active: CustomerPunchCard[]; completed: CustomerPunchCard[] }>({ active: [], completed: [] });
  const [punchRedeeming, setPunchRedeeming] = useState<string | null>(null);
  const [proofCard, setProofCard] = useState<CustomerPunchCard | null>(null);
  const [merchantThemeColor, setMerchantThemeColor] = useState("");
  const [joined, setJoined] = useState(false);
  const [joining, setJoining] = useState(false);
  const [missions, setMissions] = useState<MissionView[]>([]);

  useEffect(() => {
    if (!selectedMerchantId) {
      setLoading(false);
      setJoined(false);
      setMissions([]);
      return;
    }
    setLoading(true);
    setJoined(false);
    setMissions([]);
    Promise.all([
      menuApi.forMerchant(selectedMerchantId)
        .then((items) => setMenuItems(items.map((i) => ({ ...i, price: parseFloat(i.price as any) }))))
        .catch(() => setMenuItems([])),
      merchantApi.get(selectedMerchantId)
        .then((m) => {
          setMerchantName(m.business_name);
          setMerchantSlug(m.slug ?? null);
          setMerchantThemeColor(m.store_theme_color || "");
        })
        .catch(() => setSelectedMerchant(null)),
      customerApi.getWallet(selectedMerchantId)
        .then((w) => {
          setPoints(w?.points_balance ?? 0);
          setStreak(w?.streak_days ?? 0);
          setJoined(true);
        })
        .catch(() => setJoined(false)),
      punchCardApi.customerList(selectedMerchantId)
        .then((data) => setPunchCards(data))
        .catch(() => setPunchCards({ active: [], completed: [] })),
      missionApi.myMissions(selectedMerchantId)
        .then((m) => setMissions(m))
        .catch(() => setMissions([])),
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

  function handleRedeemPunch(cardId: string) {
    const card = punchCards.active.find(c => c.id === cardId) || punchCards.completed.find(c => c.id === cardId);
    if (card) setProofCard(card);
  }

  async function handleJoin() {
    if (!merchantSlug || joining) return;
    setJoining(true);
    try {
      const { wallet: w } = await customerApi.joinMerchant(merchantSlug);
      setJoined(true);
      setPoints(w?.points_balance ?? 0);
      setStreak(w?.streak_days ?? 0);
    } catch {}
    setJoining(false);
  }

  const allPunchCards = [...punchCards.completed, ...punchCards.active];

  // Apply merchant theme color as CSS custom properties for the whole page
  useEffect(() => {
    const root = document.documentElement;
    if (merchantThemeColor && merchantThemeColor.startsWith("#")) {
      root.style.setProperty("--merchant-color", merchantThemeColor);
      const alpha = (a: number) => {
        const r = parseInt(merchantThemeColor.slice(1, 3), 16);
        const g = parseInt(merchantThemeColor.slice(3, 5), 16);
        const b = parseInt(merchantThemeColor.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${a})`;
      };
      root.style.setProperty("--merchant-light", alpha(0.1));
      root.style.setProperty("--merchant-mid", alpha(0.2));
    } else {
      root.style.removeProperty("--merchant-color");
      root.style.removeProperty("--merchant-light");
      root.style.removeProperty("--merchant-mid");
    }
    return () => {
      root.style.removeProperty("--merchant-color");
      root.style.removeProperty("--merchant-light");
      root.style.removeProperty("--merchant-mid");
    };
  }, [merchantThemeColor]);

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
          <div
            className="absolute -right-10 -top-10 h-40 w-40 rounded-full opacity-30 blur-3xl transition-colors duration-500"
            style={{ background: merchantThemeColor || undefined }}
          />
          <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            {selectedMerchantId ? "Now open" : "Select a store to start"}
          </p>
          <h1 className="font-display mt-2 text-[44px] leading-[1] text-foreground">{merchantName}</h1>
          {selectedMerchantId && (
            <div className="mt-5 flex items-center gap-2">
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors duration-300"
                style={merchantThemeColor ? { background: `var(--merchant-light, rgba(255,100,50,0.1))`, color: merchantThemeColor } : { background: "rgba(255,100,50,0.1)", color: "var(--ember)" }}
              >
                <Flame className="h-3 w-3" /> {streak}-day streak
              </span>
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors duration-300"
                style={merchantThemeColor ? { background: `var(--merchant-light, rgba(255,100,50,0.1))`, color: merchantThemeColor } : { background: "rgba(255,100,50,0.1)", color: "var(--ember)" }}
              >
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

      {/* Join merchant banner */}
      {selectedMerchantId && merchantSlug && !joined && !loading && (
        <section className="px-5 mt-4">
          <div className="glass-strong relative overflow-hidden rounded-[28px] border border-dashed p-6 text-center" style={{ borderColor: merchantThemeColor || "var(--ember)" }}>
            <div
              className="absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-20 blur-3xl"
              style={{ background: merchantThemeColor || "var(--ember)" }}
            />
            <p className="font-display text-lg text-foreground">Join {merchantName}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Join this store to earn points, track orders, and redeem rewards.
            </p>
            <button
              onClick={handleJoin}
              disabled={joining}
              className="mt-4 inline-flex items-center gap-2 rounded-full px-6 py-2.5 text-sm font-medium text-white transition-all active:scale-95 disabled:opacity-60"
              style={{
                background: merchantThemeColor || "var(--ink)",
                boxShadow: merchantThemeColor ? `0 4px 14px ${merchantThemeColor}50` : undefined,
              }}
            >
              {joining ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <UserPlus className="h-4 w-4" />
              )}
              {joining ? "Joining…" : "Join & Start Earning"}
            </button>
          </div>
        </section>
      )}

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
                <h3 className="font-display mt-2 text-xl text-foreground leading-tight truncate">
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

      {/* Transfer section */}
      {selectedMerchantId && (
        <section className="px-5 mt-4">
          {!showTransfer ? (
            <button
              onClick={() => setShowTransfer(true)}
              className="glass-strong w-full rounded-[20px] p-4 flex items-center justify-between transition-transform active:scale-[0.98]"
            >
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400">
                  <ArrowLeftRight className="h-5 w-5" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground">Transfer points</p>
                  <p className="text-xs text-muted-foreground">
                    Send or receive at <span className="font-medium text-foreground">{merchantName}</span>
                  </p>
                </div>
              </div>
              <span className="text-xs text-muted-foreground">{points} pts available</span>
            </button>
          ) : (
            <div className="glass-strong rounded-[28px] p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-display text-xl text-foreground">Transfer points</h3>
                <button
                  onClick={() => setShowTransfer(false)}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Close
                </button>
              </div>
              <div className="flex gap-2 bg-mist rounded-xl p-1">
                <button
                  onClick={() => setTransferMode("send")}
                  className={`flex-1 flex items-center justify-center gap-2 rounded-[10px] py-2 text-xs font-medium transition-all ${
                    transferMode === "send"
                      ? "bg-background text-foreground shadow-soft"
                      : "text-muted-foreground"
                  }`}
                >
                  <SendHorizontal className="h-4 w-4" /> Send
                </button>
                <button
                  onClick={() => setTransferMode("receive")}
                  className={`flex-1 flex items-center justify-center gap-2 rounded-[10px] py-2 text-xs font-medium transition-all ${
                    transferMode === "receive"
                      ? "bg-background text-foreground shadow-soft"
                      : "text-muted-foreground"
                  }`}
                >
                  <QrCode className="h-4 w-4" /> Receive
                </button>
              </div>

              {transferMode === "send" ? (
                <TransferForm
                  preselectedMerchantId={selectedMerchantId}
                  onSuccess={() => {
                    customerApi.getWallet(selectedMerchantId).then((w) => {
                      if (w) setPoints(w.points_balance);
                    }).catch(() => {});
                  }}
                />
              ) : (
                <div className="py-2">
                  <Suspense fallback={
                    <div className="flex justify-center py-6">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  }>
                    <PersonalQR />
                  </Suspense>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* Punch Cards */}
      {selectedMerchantId && allPunchCards.length > 0 && (
        <section className="px-5 mt-4">
          {allPunchCards.map((card) => (
            <PremiumPunchCard
              key={card.id}
              card={card}
              onRedeem={handleRedeemPunch}
              redeeming={punchRedeeming === card.id}
            />
          ))}
        </section>
      )}

      {/* Missions */}
      {selectedMerchantId && joined && missions.length > 0 && (
        <section className="px-5 mt-4">
          <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground mb-3">Missions</p>
          <div className="space-y-3">
            {missions.map((m) => (
              <div key={m.id} className="glass-strong rounded-2xl p-4">
                <div className="flex items-start gap-3">
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-ember-soft text-lg">
                    {m.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-foreground truncate">{m.title}</p>
                      {m.is_completed ? (
                        <span className="shrink-0 text-[10px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">Done ✓</span>
                      ) : (
                        <span className="shrink-0 text-[10px] font-medium text-ember bg-ember-soft px-2 py-0.5 rounded-full">+{m.reward_points} pts</span>
                      )}
                    </div>
                    {m.description && (
                      <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-1">{m.description}</p>
                    )}
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
                        <span>{m.current_count} / {m.target_count}</span>
                        <span>{m.mission_type.replace(/_/g, " ")}</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-mist overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.min(100, (m.current_count / m.target_count) * 100)}%`,
                            background: m.is_completed ? "var(--ink)" : "var(--ember)",
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
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
              className="h-11 w-full rounded-2xl bg-mist pl-10 pr-10 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-ink/20"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
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
          {cats.map((c) => {
            const isActive = cat === c;
            return (
              <button
                key={c}
                onClick={() => setCat(c)}
                className="shrink-0 rounded-full px-4 py-2 text-xs font-medium transition-all"
                style={
                  isActive && merchantThemeColor
                    ? { background: merchantThemeColor, color: "#fff", boxShadow: `0 4px 14px ${merchantThemeColor}40` }
                    : isActive
                    ? { background: "var(--ink)", color: "var(--primary-foreground)" }
                    : { background: "var(--glass-bg)", color: "var(--muted-foreground)", border: "1px solid var(--border)" }
                }
              >
                {c}
              </button>
            );
          })}
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
          className="fixed inset-x-0 bottom-24 z-40 mx-auto flex max-w-[440px] items-center justify-between rounded-full px-5 py-3 text-white shadow-lg transition-colors duration-300"
          style={{
            background: merchantThemeColor || "var(--ink)",
            boxShadow: merchantThemeColor ? `0 8px 24px ${merchantThemeColor}50` : undefined,
            marginLeft: "auto",
            marginRight: "auto",
            width: "calc(100% - 32px)",
          }}
        >
          <span className="flex items-center gap-2 text-sm font-medium">
            <ShoppingBag className="h-4 w-4" /> {count} {count === 1 ? "item" : "items"}
          </span>
          <span className="font-display text-lg">NPR {total.toLocaleString()} →</span>
        </Link>
      )}

      {proofCard && (
        <PunchCardProofModal
          card={proofCard}
          onClose={() => setProofCard(null)}
          onRedeemed={() => {
            setProofCard(null);
            if (selectedMerchantId) {
              punchCardApi.customerList(selectedMerchantId)
                .then((data) => setPunchCards(data))
                .catch(() => {});
            }
          }}
        />
      )}
    </MobileShell>
  );
}
