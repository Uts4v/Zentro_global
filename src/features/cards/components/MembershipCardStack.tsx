// src/features/cards/components/MembershipCardStack.tsx
import { useState, useEffect, useRef, useCallback } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { membershipCardApi, type MembershipCard } from "@/lib/api";
import { QRCodeSVG } from "qrcode.react";
import {
  QrCode,
  ChevronRight,
  Sparkles,
  ArrowRightLeft,
  Flame,
  X,
} from "lucide-react";

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function cardGradient(design: MembershipCard["card_design"], merchantName: string) {
  if (design) {
    return {
      background: `linear-gradient(145deg, ${design.primary_color} 0%, ${design.secondary_color} 100%)`,
      color: design.text_mode === "light" ? "#ffffff" : "#1a1a1a",
    };
  }
  const safe = merchantName || "Zentro";
  const h = safe.split("").reduce((acc, c) => (acc * 31 + c.charCodeAt(0)) | 0, 0);
  const hue = Math.abs(h) % 360;
  return {
    background: `linear-gradient(145deg, hsl(${hue}, 32%, 17%) 0%, hsl(${(hue + 25) % 360}, 38%, 25%) 100%)`,
    color: "#ffffff",
  };
}

function tierLabel(tier: string) {
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}

function tierBadgeBg(tier: string, isDark: boolean) {
  if (isDark) {
    switch (tier) {
      case "platinum":
        return "rgba(255,255,255,0.18)";
      case "gold":
        return "rgba(217,169,78,0.25)";
      case "silver":
        return "rgba(255,255,255,0.12)";
      default:
        return "rgba(255,255,255,0.08)";
    }
  }
  switch (tier) {
    case "platinum":
      return "rgba(255,255,255,0.22)";
    case "gold":
      return "rgba(180,130,40,0.18)";
    case "silver":
      return "rgba(255,255,255,0.15)";
    default:
      return "rgba(255,255,255,0.10)";
  }
}

/* ── Card peek height constants (px) ───────────────────────────────────── */

const PEEK_1 = 52;
const PEEK_2 = 40;
const STACK_GAP = 10;

/* ── QR Modal ──────────────────────────────────────────────────────────── */

function QrModal({
  merchantSlug,
  merchantName,
  onClose,
}: {
  merchantSlug: string;
  merchantName: string;
  onClose: () => void;
}) {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQr = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await membershipCardApi.getQr(merchantSlug);
      setToken(data.public_token);
    } catch (e: any) {
      setError(e?.message || "Failed to load QR");
    } finally {
      setLoading(false);
    }
  }, [merchantSlug]);

  useEffect(() => {
    fetchQr();
  }, [fetchQr]);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 px-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="glass-strong relative w-full max-w-sm rounded-3xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 grid h-8 w-8 place-items-center rounded-full bg-muted text-muted-foreground hover:bg-muted/70"
        >
          <X className="h-4 w-4" />
        </button>

        <p className="text-center text-sm font-medium text-foreground">{merchantName}</p>
        <p className="mt-0.5 text-center text-xs text-muted-foreground">
          Show this to earn or redeem points
        </p>

        <div className="mt-5 flex flex-col items-center">
          {loading ? (
            <div className="grid h-48 w-48 place-items-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-foreground" />
            </div>
          ) : token ? (
            <div className="rounded-2xl bg-white p-4">
              <QRCodeSVG
                value={`${window.location.origin}/loyalty/qr/${token}`}
                size={180}
                bgColor="#ffffff"
                fgColor="#000000"
              />
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 py-8">
              <p className="text-sm text-muted-foreground">{error || "Could not load QR code"}</p>
              <button
                onClick={fetchQr}
                className="rounded-full bg-ember px-4 py-2 text-xs font-medium text-white active:scale-95"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Single Card Face ─────────────────────────────────────────────────── */

function CardFace({
  card,
  isDark,
  compact,
  onQrTap,
}: {
  card: MembershipCard;
  isDark: boolean;
  compact?: boolean;
  onQrTap?: () => void;
}) {
  const merchantName = card.merchant?.name || "Zentro";
  const style = cardGradient(card.card_design, merchantName);
  const tier = card.wallet?.tier ?? "bronze";
  const points = card.wallet?.points_balance ?? 0;
  const isLightText = style.color === "#ffffff";

  if (compact) {
    return (
      <div className="flex items-center gap-3 px-5 py-3.5" style={{ color: style.color }}>
        {card.merchant.logo ? (
          <img
            src={card.merchant.logo}
            alt=""
            className="h-7 w-7 shrink-0 rounded-lg object-cover"
          />
        ) : (
          <div
            className="h-7 w-7 shrink-0 rounded-lg"
            style={{ background: "rgba(255,255,255,0.15)" }}
          />
        )}
        <p className="min-w-0 flex-1 truncate font-display text-[17px]">{merchantName}</p>
        <span
          className="shrink-0 rounded-full px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-widest"
          style={{ background: tierBadgeBg(tier, isLightText), color: style.color }}
        >
          {tierLabel(tier)}
        </span>
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col p-5" style={{ color: style.color }}>
      {/* Decorative */}
      <div
        className="pointer-events-none absolute -right-10 -top-10 h-36 w-36 rounded-full"
        style={{ background: "rgba(255,255,255,0.07)", filter: "blur(40px)" }}
      />
      <div
        className="pointer-events-none absolute -bottom-14 -left-14 h-36 w-36 rounded-full"
        style={{ background: "rgba(255,255,255,0.04)", filter: "blur(40px)" }}
      />

      {/* Top row */}
      <div className="relative flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          {card.merchant.logo ? (
            <img
              src={card.merchant.logo}
              alt=""
              className="h-9 w-9 shrink-0 rounded-xl object-cover"
            />
          ) : null}
          <div className="min-w-0">
            <p className="text-[9px] uppercase tracking-[0.22em] opacity-45">
              {card.card_design?.card_title || "Membership"}
            </p>
            <p className="mt-0.5 truncate font-display text-[22px] leading-tight">{merchantName}</p>
          </div>
        </div>
        <span
          className="mt-0.5 shrink-0 rounded-full px-2.5 py-1 text-[9px] font-semibold uppercase tracking-widest"
          style={{ background: tierBadgeBg(tier, isLightText), color: style.color }}
        >
          {tierLabel(tier)}
        </span>
      </div>

      {/* Points */}
      <div className="relative mt-auto">
        <p className="text-[9px] uppercase tracking-[0.22em] opacity-45">
          {card.card_design?.points_label || "Available Points"}
        </p>
        <p
          className="font-display text-[52px] leading-none tracking-tight"
          style={{ letterSpacing: "-0.03em" }}
        >
          {points.toLocaleString()}
        </p>
        {card.card_design?.show_lifetime_points && card.wallet && (
          <p className="mt-1 text-[11px] opacity-40">
            {card.wallet.lifetime_points.toLocaleString()} lifetime pts
          </p>
        )}
      </div>

      {/* Bottom row */}
      <div className="relative mt-4 flex items-end justify-between">
        <div>
          <p className="text-[9px] uppercase tracking-widest opacity-35">
            {card.card_design?.membership_label || "Member"}
          </p>
          <p className="mt-0.5 font-mono text-[11px] tracking-wider opacity-60">
            {card.membership.membership_number_masked}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {card.wallet && (card.wallet.streak_days ?? 0) > 0 && (
            <span
              className="flex items-center gap-1 rounded-full px-2.5 py-1 text-[9px] font-semibold uppercase tracking-widest"
              style={{ background: "rgba(255,255,255,0.15)" }}
            >
              <Flame className="h-3 w-3" /> {card.wallet.streak_days} day streak
            </span>
          )}
          {card.transfer_enabled && (
            <span
              className="flex items-center gap-1 rounded-full px-2 py-1 text-[8px] uppercase tracking-widest opacity-50"
              style={{ background: "rgba(255,255,255,0.10)" }}
            >
              <ArrowRightLeft className="h-2.5 w-2.5" /> Transfer
            </span>
          )}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onQrTap?.();
            }}
            className="flex items-center gap-1 rounded-full px-2.5 py-1 text-[9px] font-medium uppercase tracking-wider active:scale-95 transition-transform"
            style={{ background: "rgba(255,255,255,0.10)" }}
          >
            <QrCode className="h-3 w-3" /> QR
          </button>
        </div>
      </div>

      {/* Powered by */}
      <p className="relative mt-3 text-right text-[8px] opacity-25 tracking-wide">
        Powered by Zentro
      </p>
    </div>
  );
}

/* ── Skeleton ──────────────────────────────────────────────────────────── */

function CardSkeletonStack() {
  return (
    <div className="relative" style={{ height: 300 }}>
      <div className="absolute left-0 right-0 top-0 h-[52px] animate-pulse rounded-t-[24px] bg-muted opacity-60" />
      <div className="absolute left-0 right-0 top-[44px] h-[52px] animate-pulse rounded-t-[24px] bg-muted opacity-40" />
      <div className="absolute inset-x-0 top-[80px] bottom-0 animate-pulse rounded-[24px] bg-muted" />
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────────────── */

export function MembershipCardStack() {
  const [cards, setCards] = useState<MembershipCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const [qrModal, setQrModal] = useState<{ slug: string; name: string } | null>(null);
  const [dragOffset, setDragOffset] = useState(0);
  const navigate = useNavigate();

  const dragRef = useRef({ startY: 0, active: false });
  const containerRef = useRef<HTMLDivElement>(null);
  const wheelCooldown = useRef(false);

  useEffect(() => {
    let cancelled = false;
    membershipCardApi
      .list()
      .then((data) => {
        if (!cancelled) setCards(data);
      })
      .catch((e: any) => {
        if (!cancelled) setError(e.message || "Failed to load cards");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (activeIdx >= cards.length) setActiveIdx(Math.max(0, cards.length - 1));
  }, [cards.length, activeIdx]);

  const goTo = useCallback(
    (idx: number) => {
      setActiveIdx(Math.max(0, Math.min(idx, cards.length - 1)));
    },
    [cards.length],
  );

  const prev = useCallback(() => goTo(activeIdx - 1), [activeIdx, goTo]);
  const next = useCallback(() => goTo(activeIdx + 1), [activeIdx, goTo]);

  const openDetail = useCallback(
    (slug: string) => {
      navigate({ to: "/cards/$merchantSlug", params: { merchantSlug: slug } });
    },
    [navigate],
  );

  const openQr = useCallback((slug: string, name: string) => {
    setQrModal({ slug, name });
  }, []);

  /* ── Touch drag ── */
  const onTouchStart = useCallback((e: React.TouchEvent) => {
    dragRef.current = { startY: e.touches[0].clientY, active: true };
    setDragOffset(0);
  }, []);

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    if (!dragRef.current.active) return;
    const dy = e.touches[0].clientY - dragRef.current.startY;
    setDragOffset(dy * 0.4); // dampened drag
  }, []);

  const onTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (!dragRef.current.active) return;
      dragRef.current.active = false;
      const dy = e.changedTouches[0].clientY - dragRef.current.startY;
      setDragOffset(0);
      if (dy < -40) next();
      else if (dy > 40) prev();
    },
    [next, prev],
  );

  /* ── Mouse wheel to cycle through cards ── */
  const onWheel = useCallback(
    (e: React.WheelEvent) => {
      if (wheelCooldown.current) return;
      const absY = Math.abs(e.deltaY);
      if (absY < 15) return;
      wheelCooldown.current = true;
      if (e.deltaY > 0) next();
      else prev();
      setTimeout(() => {
        wheelCooldown.current = false;
      }, 300);
    },
    [next, prev],
  );

  /* ── Keyboard ── */
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
        e.preventDefault();
        prev();
      }
      if (e.key === "ArrowDown" || e.key === "ArrowRight") {
        e.preventDefault();
        next();
      }
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        const card = cards[activeIdx];
        if (card) openQr(card.merchant.slug, card.merchant.name);
      }
    },
    [prev, next, cards, activeIdx, openQr],
  );

  /* ── Stack layout ── */
  function stackStyle(idx: number): React.CSSProperties {
    const dist = idx - activeIdx;
    if (dist < 0) return { display: "none" };
    if (dist === 0) {
      return {
        transform: `translateY(${dragOffset}px) scale(1)`,
        opacity: 1,
        zIndex: 100 - dist,
        transition:
          dragOffset !== 0
            ? "none"
            : `transform 0.5s cubic-bezier(0.16,1,0.3,1), opacity 0.4s ease`,
      };
    }
    if (dist === 1) {
      return {
        transform: `translateY(${PEEK_1}px) scale(0.975)`,
        opacity: 1,
        zIndex: 100 - dist,
        transition: `transform 0.5s cubic-bezier(0.16,1,0.3,1), opacity 0.4s ease`,
      };
    }
    if (dist === 2) {
      return {
        transform: `translateY(${PEEK_1 + PEEK_2 + STACK_GAP - 4}px) scale(0.955)`,
        opacity: 0.95,
        zIndex: 100 - dist,
        transition: `transform 0.5s cubic-bezier(0.16,1,0.3,1), opacity 0.4s ease`,
      };
    }
    return {
      transform: `translateY(${PEEK_1 + PEEK_2 + STACK_GAP + 30}px) scale(0.94)`,
      opacity: 0,
      zIndex: 0,
      pointerEvents: "none",
      transition: `transform 0.4s cubic-bezier(0.16,1,0.3,1), opacity 0.3s ease`,
    };
  }

  const walletHeight =
    cards.length <= 1
      ? 300
      : cards.length === 2
        ? 300 + PEEK_1 + 8
        : 300 + PEEK_1 + PEEK_2 + STACK_GAP + 8;

  const activeCard = cards[activeIdx];

  return (
    <section className="flex flex-col">
      {/* Header */}
      <div className="flex items-baseline justify-between px-1">
        <div>
          <h1 className="font-display text-[28px] leading-tight text-foreground">My Cards</h1>
          {!loading && !error && (
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              {cards.length === 0 ? "No memberships yet" : `${cards.length} joined`}
            </p>
          )}
        </div>
        {cards.length > 1 && (
          <p className="text-[11px] text-muted-foreground">
            {activeIdx + 1} / {cards.length}
          </p>
        )}
      </div>

      {error && (
        <div className="mt-4 glass rounded-2xl p-5 text-center">
          <p className="text-sm text-rose-500">{error}</p>
        </div>
      )}

      {!loading && !error && cards.length === 0 && (
        <div className="mt-6 glass rounded-3xl px-6 py-14 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-ember-soft">
            <Sparkles className="h-6 w-6 text-ember" />
          </div>
          <p className="mt-4 text-sm font-medium text-foreground">No cards yet</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Join a merchant to start collecting points.
          </p>
          <Link
            to="/map"
            className="mt-5 inline-flex h-10 items-center justify-center rounded-full bg-ink px-5 text-xs font-medium text-primary-foreground transition-transform hover:scale-[1.03] active:scale-95"
          >
            Discover merchants
          </Link>
        </div>
      )}

      {loading && (
        <div className="mt-4">
          <CardSkeletonStack />
        </div>
      )}

      {/* ── Wallet Stack ────────────────────────────────────────────── */}
      {!loading && !error && cards.length > 0 && (
        <>
          <div
            ref={containerRef}
            className="relative mt-5 w-full select-none outline-none"
            style={{ height: walletHeight }}
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
            onWheel={onWheel}
            onKeyDown={onKeyDown}
            tabIndex={0}
            role="listbox"
            aria-label="Membership cards — swipe or use arrow keys to browse"
            aria-activedescendant={
              activeCard ? `wallet-card-${activeCard.merchant.slug}` : undefined
            }
          >
            {cards.map((card, idx) => {
              const dist = idx - activeIdx;
              const s = stackStyle(idx);
              const isActive = dist === 0;
              const merchantName = card.merchant?.name || "Zentro";
              const bg = cardGradient(card.card_design, merchantName);

              return (
                <div
                  key={card.merchant.slug}
                  id={`wallet-card-${card.merchant.slug}`}
                  role="option"
                  aria-label={`${merchantName} membership card — ${card.wallet?.points_balance ?? 0} points, ${card.wallet?.tier ?? "bronze"} tier`}
                  aria-selected={isActive}
                  className="absolute left-0 right-0 cursor-pointer"
                  style={{
                    top: 0,
                    height: 290,
                    ...s,
                    borderRadius: 24,
                    background: card.card_design?.background_image && isActive
                      ? "rgba(0,0,0,0.25)"
                      : bg.background,
                    color: bg.color,
                    boxShadow: isActive
                      ? "0 20px 50px -12px rgba(0,0,0,0.35), 0 4px 12px -4px rgba(0,0,0,0.15)"
                      : "0 6px 20px -6px rgba(0,0,0,0.2)",
                    overflow: "hidden",
                  }}
                  onClick={() => {
                    if (isActive) {
                      navigate({ to: "/m/$slug", params: { slug: card.merchant.slug } });
                    } else {
                      goTo(idx);
                    }
                  }}
                >
                  {card.card_design?.background_image && isActive && (
                    <img
                      src={card.card_design.background_image}
                      alt=""
                      className="pointer-events-none absolute inset-0 h-full w-full object-cover"
                      style={{ borderRadius: 24 }}
                    />
                  )}
                  <CardFace
                    card={card}
                    isDark={isLightText(bg.color)}
                    compact={!isActive}
                    onQrTap={isActive ? () => openQr(card.merchant.slug, merchantName) : undefined}
                  />
                </div>
              );
            })}
          </div>

          {/* Dot indicator */}
          {cards.length > 1 && (
            <div
              className="mt-3 flex items-center justify-center gap-2"
              role="tablist"
              aria-label="Card position"
            >
              {cards.map((c, i) => (
                <button
                  key={c.merchant.slug}
                  onClick={() => goTo(i)}
                  className="rounded-full"
                  role="tab"
                  aria-selected={i === activeIdx}
                  aria-label={c.merchant?.name || `Card ${i + 1}`}
                  style={{
                    width: i === activeIdx ? 20 : 7,
                    height: 7,
                    background: i === activeIdx ? "var(--ember)" : "var(--muted-foreground)",
                    opacity: i === activeIdx ? 1 : 0.35,
                    transition:
                      "width 0.3s cubic-bezier(0.16,1,0.3,1), background 0.3s, opacity 0.3s",
                  }}
                />
              ))}
            </div>
          )}

          {/* Hint */}
          {activeCard && (
            <p className="mt-3 text-center text-[11px] text-muted-foreground">
              Tap card to visit store
            </p>
          )}
        </>
      )}

      {qrModal && (
        <QrModal
          merchantSlug={qrModal.slug}
          merchantName={qrModal.name}
          onClose={() => setQrModal(null)}
        />
      )}
    </section>
  );
}

/* ── Tiny helper ───────────────────────────────────────────────────────── */

function isLightText(color: string): boolean {
  if (color === "#1a1a1a") return false;
  if (color === "#ffffff") return true;
  // Fallback: assume dark bg → light text
  return color.length < 8;
}
