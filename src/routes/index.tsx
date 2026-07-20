// routes/index.tsx — Premium Zentro Home Screen
import { createFileRoute, Link } from "@tanstack/react-router";
import { useStore, cartTotal, type MenuItem } from "@/lib/store";
import {
  merchantApi,
  menuApi,
  customerApi,
  specialApi,
  punchCardApi,
  missionApi,
  membershipCardApi,
  type TodaySpecial,
  type CustomerPunchCard,
  type MissionView,
} from "@/lib/api";
import { MobileShell, TopBar } from "@/components/MobileShell";
import { ShoppingBag, X as XIcon, QrCode, SendHorizontal, Loader2, Plus } from "lucide-react";
import { requireAuth } from "@/lib/auth-guard";
import { lazy, Suspense, useState, useEffect, useMemo } from "react";
import { TodaySpecialPopup } from "@/features/merchant-management/components/TodaySpecialPopup";
import { TransferForm } from "@/features/transfers/components/TransferForm";
import { PremiumPunchCard } from "@/components/PremiumPunchCard";
import { PunchCardProofModal } from "@/components/PunchCardProofModal";
import { resolveMerchantPreset, type MerchantThemePreset } from "@/lib/merchant-theme-presets";

// Home components
import { HeroLoyaltyCard } from "@/components/home/HeroLoyaltyCard";
import { QuickActions } from "@/components/home/QuickActions";
import { SearchBar } from "@/components/home/SearchBar";
import { CategoryChips } from "@/components/home/CategoryChips";

const PersonalQR = lazy(() =>
  import("@/features/transfers/components/PersonalQR").then((m) => ({ default: m.PersonalQR }))
);
const TableQRScanner = lazy(() =>
  import("@/features/pos/screens/TableQRScanner").then((m) => ({ default: m.TableQRScanner }))
);

export const Route = createFileRoute("/")({
  beforeLoad: requireAuth,
  head: () => ({
    meta: [
      { title: "Zentro — Home" },
      { name: "description", content: "Your loyalty dashboard. Earn, redeem, and discover." },
    ],
  }),
  component: Index,
});

function MenuItemCard({
  item,
  onAdd,
  disabled,
  merchantColor,
}: {
  item: MenuItem;
  onAdd: () => void;
  disabled: boolean;
  merchantColor?: string;
}) {
  const [imgError, setImgError] = useState(false);
  const hasImage = !!item.image_url && !imgError;
  const price = parseFloat(item.price as any);

  return (
    <article
      className="group overflow-hidden rounded-[20px] bg-white transition-all active:scale-[0.97]"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      {hasImage ? (
        <div className="relative h-[120px] overflow-hidden bg-[#F5F3EF]">
          <img
            src={item.image_url ?? undefined}
            alt={item.name}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            onError={() => setImgError(true)}
            loading="lazy"
          />
          {item.is_featured && (
            <span className="absolute left-2.5 top-2.5 rounded-full bg-[#E85D3A] px-2.5 py-0.5 text-[9px] font-bold tracking-wide text-white shadow-sm">
              Featured
            </span>
          )}
        </div>
      ) : (
        <div className="relative grid h-24 place-items-center bg-[#F5F3EF] text-4xl">
          {item.emoji || "☕"}
          {item.is_featured && (
            <span className="absolute left-2.5 top-2.5 rounded-full bg-[#E85D3A] px-2.5 py-0.5 text-[9px] font-bold tracking-wide text-white shadow-sm">
              Featured
            </span>
          )}
        </div>
      )}
      <div className="flex flex-col p-3.5">
        <h3 className="text-[13px] font-semibold text-[#1A1A1A] line-clamp-1">{item.name}</h3>
        <p className="mt-0.5 line-clamp-2 text-[11px] text-[#1A1A1A]/40">{item.description}</p>
        <div className="mt-2.5 flex items-center justify-between">
          <span className="font-display text-lg text-[#1A1A1A]">NPR {price.toLocaleString()}</span>
          <button
            onClick={onAdd}
            disabled={disabled}
            className="grid h-8 w-8 place-items-center rounded-full text-white transition-all active:scale-90 disabled:opacity-40"
            style={{
              background: merchantColor || "#1A1A1A",
              boxShadow: merchantColor ? `0 4px 12px ${merchantColor}40` : undefined,
            }}
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

  // Data states
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [merchantName, setMerchantName] = useState("");
  const [merchantSlug, setMerchantSlug] = useState<string | null>(null);
  const [merchantLogo, setMerchantLogo] = useState<string | null>(null);
  const [merchantCategory, setMerchantCategory] = useState<string | null>(null);
  const [merchantThemeColor, setMerchantThemeColor] = useState("");
  const [merchantBusinessType, setMerchantBusinessType] = useState<string | null>(null);
  const [cardTextColor, setCardTextColor] = useState("");
  const [cardBackgroundImage, setCardBackgroundImage] = useState("");
  const [points, setPoints] = useState(0);
  const [streak, setStreak] = useState(0);
  const [ordersCount, setOrdersCount] = useState(0);
  const [tier, setTier] = useState("bronze");
  const [memberName, setMemberName] = useState("Member");
  const [cardNumber, setCardNumber] = useState("•••• 0000");
  const [freeRewards, setFreeRewards] = useState(0);
  const [loading, setLoading] = useState(true);
  const [cat, setCat] = useState<string>("All");
  const [search, setSearch] = useState("");
  const [todaySpecial, setTodaySpecial] = useState<TodaySpecial | null>(null);
  const [showTransfer, setShowTransfer] = useState(false);
  const [transferMode, setTransferMode] = useState<"send" | "receive">("send");
  const [punchCards, setPunchCards] = useState<{
    active: CustomerPunchCard[];
    completed: CustomerPunchCard[];
  }>({ active: [], completed: [] });
  const [punchRedeeming, setPunchRedeeming] = useState<string | null>(null);
  const [proofCard, setProofCard] = useState<CustomerPunchCard | null>(null);
  const [joined, setJoined] = useState(false);
  const [joining, setJoining] = useState(false);
  const [missions, setMissions] = useState<MissionView[]>([]);
  const [showTableScanner, setShowTableScanner] = useState(false);

  // Resolve merchant theme preset
  const themePreset: MerchantThemePreset | null = useMemo(
    () => resolveMerchantPreset(merchantBusinessType),
    [merchantBusinessType]
  );

  // Load merchant data
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
      menuApi
        .forMerchant(selectedMerchantId)
        .then((items) => setMenuItems(items.map((i) => ({
          ...i,
          price: parseFloat(i.price as any),
          is_featured: (i as any).is_featured,
        }))))
        .catch(() => setMenuItems([])),
      merchantApi
        .get(selectedMerchantId)
        .then((m) => {
          setMerchantName(m.business_name);
          setMerchantSlug(m.slug ?? null);
          setMerchantLogo(m.logo_url ?? null);
          setMerchantThemeColor(m.store_theme_color || "");
          setMerchantCategory(m.business_type ?? null);
          setMerchantBusinessType(m.business_type ?? null);
          setCardTextColor(m.card_text_color || "");
          setCardBackgroundImage(m.card_background_image || "");
        })
        .catch(() => setSelectedMerchant(null)),
      customerApi
        .getWallet(selectedMerchantId)
        .then((w) => {
          setPoints(w?.points_balance ?? 0);
          setStreak(w?.streak_days ?? 0);
          setOrdersCount(w?.order_count ?? 0);
          setTier(w?.tier_level ?? "bronze");
          setJoined(true);
        })
        .catch(() => setJoined(false)),
      punchCardApi
        .customerList(selectedMerchantId)
        .then((data) => {
          setPunchCards(data);
          setFreeRewards(data.completed.length);
        })
        .catch(() => setPunchCards({ active: [], completed: [] })),
      missionApi
        .myMissions(selectedMerchantId)
        .then((m) => setMissions(m))
        .catch(() => setMissions([])),
    ]).finally(() => setLoading(false));
  }, [selectedMerchantId]);

  // Load membership card data for member name + card number
  useEffect(() => {
    if (!selectedMerchantId || !joined) return;
    membershipCardApi
      .list()
      .then((cards) => {
        const card = cards.find((c) => c.merchant.slug === merchantSlug);
        if (card) {
          setCardNumber(card.membership.membership_number_masked);
          setTier(card.wallet?.tier ?? tier);
        }
      })
      .catch(() => {});

    customerApi
      .profile()
      .then((p) => {
        if (p?.full_name) setMemberName(p.full_name);
      })
      .catch(() => {});
  }, [selectedMerchantId, joined, merchantSlug]);

  // Load today's special
  useEffect(() => {
    if (!merchantSlug) {
      setTodaySpecial(null);
      return;
    }
    specialApi
      .forSlug(merchantSlug)
      .then((s) => setTodaySpecial(s?.is_active ? s : null))
      .catch(() => setTodaySpecial(null));
  }, [merchantSlug]);

  // Categories
  const cats = useMemo(
    () => ["All", ...Array.from(new Set(menuItems.map((m) => m.category).filter(Boolean)))],
    [menuItems]
  );

  // Filtered items
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

  // Cart
  const count = cart.reduce((s, c) => s + c.qty, 0);
  const storeItems = menuItems.map((m) => ({ ...m, price: parseFloat(m.price as any) }));
  const total = cartTotal(cart, storeItems);

  // Progress to next tier
  const progressPercent = useMemo(() => {
    const tierThresholds: Record<string, number> = {
      bronze: 500,
      silver: 1500,
      gold: 3000,
      platinum: 5000,
    };
    const current = points;
    const nextTier = tier === "bronze" ? "silver" : tier === "silver" ? "gold" : tier === "gold" ? "platinum" : "platinum";
    const target = tierThresholds[nextTier] ?? 5000;
    return (current / target) * 100;
  }, [points, tier]);

  // Handlers
  function handleRedeemPunch(cardId: string) {
    const card =
      punchCards.active.find((c) => c.id === cardId) ||
      punchCards.completed.find((c) => c.id === cardId);
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

  // Apply merchant theme
  useEffect(() => {
    const root = document.documentElement;
    const color = themePreset?.primary || merchantThemeColor;
    if (color && color.startsWith("#")) {
      root.style.setProperty("--merchant-color", color);
      const alpha = (a: number) => {
        const r = parseInt(color.slice(1, 3), 16);
        const g = parseInt(color.slice(3, 5), 16);
        const b = parseInt(color.slice(5, 7), 16);
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
  }, [themePreset, merchantThemeColor]);

  const merchantColor = themePreset?.primary || merchantThemeColor || undefined;

  return (
    <MobileShell>
      <TopBar />

      {/* Today's Special popup */}
      {merchantSlug && <TodaySpecialPopup slug={merchantSlug} />}

      <div className="flex flex-col gap-5 pb-6">
        {/* Hero Loyalty Card */}
        <HeroLoyaltyCard
          merchantName={merchantName || "Select a store"}
          merchantLogo={merchantLogo}
          merchantCategory={merchantCategory}
          tier={tier}
          points={points}
          freeRewards={freeRewards}
          progressPercent={progressPercent}
          streak={streak}
          ordersCount={ordersCount}
          memberName={memberName}
          cardNumber={cardNumber}
          theme={themePreset}
          themeColor={merchantThemeColor}
          cardTextColor={cardTextColor}
          cardBackgroundImage={cardBackgroundImage}
          joined={joined}
          onJoin={handleJoin}
          joining={joining}
        />

        {/* Quick Actions */}
        {joined && (
          <QuickActions
            onScanQR={() => setShowTableScanner(true)}
            onTransfer={() => setShowTransfer(true)}
            availablePoints={points}
            merchantColor={merchantColor}
          />
        )}

        {/* Transfer expanded panel */}
        {showTransfer && selectedMerchantId && (
          <section className="px-5">
            <div className="rounded-[24px] bg-white p-5" style={{ boxShadow: "var(--shadow-card)" }}>
              <div className="flex items-center justify-between">
                <h3 className="font-display text-xl text-[#1A1A1A]">Transfer Points</h3>
                <button
                  onClick={() => setShowTransfer(false)}
                  className="grid h-8 w-8 place-items-center rounded-full bg-[#F5F3EF] text-[#1A1A1A]/40 transition-colors hover:bg-[#EDEBE7]"
                >
                  <XIcon className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-3 flex gap-1.5 rounded-2xl bg-[#F5F3EF] p-1">
                <button
                  onClick={() => setTransferMode("send")}
                  className={`flex flex-1 items-center justify-center gap-2 rounded-[14px] py-2.5 text-xs font-medium transition-all ${
                    transferMode === "send"
                      ? "bg-white text-[#1A1A1A]"
                      : "text-[#1A1A1A]/40"
                  }`}
                  style={transferMode === "send" ? { boxShadow: "0 1px 3px rgba(0,0,0,0.06)" } : {}}
                >
                  <SendHorizontal className="h-4 w-4" /> Send
                </button>
                <button
                  onClick={() => setTransferMode("receive")}
                  className={`flex flex-1 items-center justify-center gap-2 rounded-[14px] py-2.5 text-xs font-medium transition-all ${
                    transferMode === "receive"
                      ? "bg-white text-[#1A1A1A]"
                      : "text-[#1A1A1A]/40"
                  }`}
                  style={transferMode === "receive" ? { boxShadow: "0 1px 3px rgba(0,0,0,0.06)" } : {}}
                >
                  <QrCode className="h-4 w-4" /> Receive
                </button>
              </div>
              <div className="mt-4">
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
                  <Suspense
                    fallback={
                      <div className="flex justify-center py-6">
                        <Loader2 className="h-5 w-5 animate-spin text-[#8A8A8A]" />
                      </div>
                    }
                  >
                    <PersonalQR />
                  </Suspense>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Today's Special Banner */}
        {selectedMerchantId && todaySpecial && (
          <section className="px-5">
            <div
              className="relative overflow-hidden rounded-[24px] bg-white p-5"
              style={{ boxShadow: "var(--shadow-card)" }}
            >
              <div className="flex gap-4">
                {todaySpecial.image_url && (
                  <img
                    src={todaySpecial.image_url}
                    alt={todaySpecial.title}
                    className="h-20 w-20 shrink-0 rounded-2xl object-cover"
                  />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-[#E85D3A]/10 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#E85D3A]">
                      Today's Special
                    </span>
                  </div>
                  <h3 className="font-display mt-2 truncate text-xl leading-tight text-[#1A1A1A]">
                    {todaySpecial.title}
                  </h3>
                  {todaySpecial.description && (
                    <p className="mt-1 line-clamp-2 text-xs text-[#1A1A1A]/45">
                      {todaySpecial.description}
                    </p>
                  )}
                  {(todaySpecial.linked_menu_item_name || todaySpecial.linked_reward_name) && (
                    <span className="mt-2 inline-flex items-center gap-1 text-[10px] font-medium text-[#E85D3A]">
                      ✨ {todaySpecial.linked_menu_item_name ?? todaySpecial.linked_reward_name}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Punch Cards */}
        {selectedMerchantId && allPunchCards.length > 0 && (
          <section className="px-5">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1A1A1A]/35">
              Punch Cards
            </p>
            <div className="space-y-3">
              {allPunchCards.map((card) => (
                <PremiumPunchCard
                  key={card.id}
                  card={card}
                  onRedeem={handleRedeemPunch}
                  redeeming={punchRedeeming === card.id}
                />
              ))}
            </div>
          </section>
        )}

        {/* Missions */}
        {selectedMerchantId && joined && missions.length > 0 && (
          <section className="px-5">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1A1A1A]/35">
              Missions
            </p>
            <div className="space-y-3">
              {missions.map((m) => (
                <div
                  key={m.id}
                  className="rounded-[20px] bg-white p-4"
                  style={{ boxShadow: "var(--shadow-card)" }}
                >
                  <div className="flex items-start gap-3">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#FEF0EB] text-lg">
                      {m.icon}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-medium text-[#1A1A1A]">{m.title}</p>
                        {m.is_completed ? (
                          <span className="shrink-0 rounded-full bg-[#10B981]/10 px-2 py-0.5 text-[10px] font-semibold text-[#10B981]">
                            Done ✓
                          </span>
                        ) : (
                          <span className="shrink-0 rounded-full bg-[#E85D3A]/10 px-2 py-0.5 text-[10px] font-semibold text-[#E85D3A]">
                            +{m.reward_points} pts
                          </span>
                        )}
                      </div>
                      {m.description && (
                        <p className="mt-0.5 line-clamp-1 text-[11px] text-[#1A1A1A]/40">
                          {m.description}
                        </p>
                      )}
                      <div className="mt-2">
                        <div className="mb-1 flex items-center justify-between text-[10px] text-[#1A1A1A]/40">
                          <span>
                            {m.current_count} / {m.target_count}
                          </span>
                          <span>{m.mission_type.replace(/_/g, " ")}</span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#F5F3EF]">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(100, (m.current_count / m.target_count) * 100)}%`,
                              background: m.is_completed ? "#1A1A1A" : "#E85D3A",
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

        {/* Search */}
        {selectedMerchantId && menuItems.length > 0 && (
          <section className="px-5">
            <SearchBar
              value={search}
              onChange={setSearch}
              merchantName={merchantName}
            />
          </section>
        )}

        {/* Category Chips */}
        {menuItems.length > 0 && !search && (
          <CategoryChips
            categories={cats}
            active={cat}
            onSelect={setCat}
            merchantColor={merchantColor}
          />
        )}

        {/* Search result count */}
        {search && (
          <p className="px-5 text-xs text-[#1A1A1A]/40">
            {filteredItems.length} result{filteredItems.length !== 1 ? "s" : ""} for &quot;{search}&quot;
          </p>
        )}

        {/* Menu Grid */}
        {selectedMerchantId && menuItems.length > 0 && (
          <section className="px-5">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1A1A1A]/35">
              Menu
            </p>
            <div className="grid grid-cols-2 gap-3">
              {loading && (
                <p className="col-span-2 py-8 text-center text-sm text-[#1A1A1A]/40">
                  Loading menu…
                </p>
              )}
              {!loading && filteredItems.length === 0 && (
                <p className="col-span-2 py-8 text-center text-sm text-[#1A1A1A]/40">
                  {search ? `No items match "${search}"` : "No menu items available."}
                </p>
              )}
              {filteredItems.map((item) => (
                <MenuItemCard
                  key={item.id}
                  item={item}
                  onAdd={() => add(item.id)}
                  disabled={!selectedMerchantId}
                  merchantColor={merchantColor}
                />
              ))}
            </div>
          </section>
        )}

        {/* No merchant selected */}
        {!selectedMerchantId && !loading && (
          <section className="px-5">
            <div className="rounded-[24px] bg-white p-8 text-center" style={{ boxShadow: "var(--shadow-card)" }}>
              <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#FEF0EB]">
                <span className="text-2xl">✦</span>
              </div>
              <p className="mt-4 text-sm font-semibold text-[#1A1A1A]">Welcome to Zentro</p>
              <p className="mt-1 text-xs text-[#1A1A1A]/40">
                Browse stores to start earning loyalty points.
              </p>
              <Link
                to="/map"
                className="mt-5 inline-flex h-10 items-center justify-center rounded-full bg-[#1A1A1A] px-6 text-xs font-medium text-white transition-all active:scale-95"
              >
                Discover stores
              </Link>
            </div>
          </section>
        )}
      </div>

      {/* Floating cart bar */}
      {count > 0 && (
        <Link
          to="/cart"
          className="fixed inset-x-0 bottom-24 z-40 mx-auto flex max-w-[400px] items-center justify-between rounded-full bg-[#1A1A1A] px-5 py-3.5 text-white transition-colors"
          style={{
            boxShadow: "0 8px 32px -4px rgba(0,0,0,0.25)",
            width: "calc(100% - 40px)",
          }}
        >
          <span className="flex items-center gap-2 text-sm font-medium">
            <ShoppingBag className="h-4 w-4" /> {count} {count === 1 ? "item" : "items"}
          </span>
          <span className="font-display text-lg">NPR {total.toLocaleString()} →</span>
        </Link>
      )}

      {/* Punch card proof modal */}
      {proofCard && (
        <PunchCardProofModal
          card={proofCard}
          onClose={() => setProofCard(null)}
          onRedeemed={() => {
            setProofCard(null);
            if (selectedMerchantId) {
              punchCardApi
                .customerList(selectedMerchantId)
                .then((data) => setPunchCards(data))
                .catch(() => {});
            }
          }}
        />
      )}

      {/* Table QR scanner */}
      {showTableScanner && (
        <Suspense fallback={null}>
          <TableQRScanner onClose={() => setShowTableScanner(false)} />
        </Suspense>
      )}
    </MobileShell>
  );
}
