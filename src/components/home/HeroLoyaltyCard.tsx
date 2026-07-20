// src/components/home/HeroLoyaltyCard.tsx
// Premium merchant-themed loyalty card — minimalist creative gradient
import { useMemo } from "react";
import { Flame, Star, ShoppingBag, TrendingUp } from "lucide-react";
import { getIllustrationSVG, type MerchantThemePreset } from "@/lib/merchant-theme-presets";

interface HeroLoyaltyCardProps {
  merchantName: string;
  merchantLogo?: string | null;
  merchantCategory?: string | null;
  tier: string;
  points: number;
  freeRewards: number;
  progressPercent: number;
  streak: number;
  ordersCount: number;
  memberName: string;
  cardNumber: string;
  theme?: MerchantThemePreset | null;
  themeColor?: string;
  cardTextColor?: string;
  cardBackgroundImage?: string;
  joined: boolean;
  onJoin?: () => void;
  joining?: boolean;
}

function tierLabel(tier: string): string {
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}

function tierIcon(tier: string): string {
  switch (tier) {
    case "platinum": return "✦";
    case "gold": return "★";
    case "silver": return "◆";
    default: return "●";
  }
}

function hexToRGBA(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function isLightColor(hex: string): boolean {
  if (!hex || !hex.startsWith("#")) return false;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.6;
}

export function HeroLoyaltyCard({
  merchantName,
  merchantLogo,
  merchantCategory,
  tier,
  points,
  freeRewards,
  progressPercent,
  streak,
  ordersCount,
  memberName,
  cardNumber,
  theme,
  themeColor,
  cardTextColor,
  cardBackgroundImage,
  joined,
  onJoin,
  joining,
}: HeroLoyaltyCardProps) {
  const primary = theme?.primary ?? themeColor ?? "#1A1A1A";
  const secondary = theme?.secondary ?? themeColor ?? "#2C2C2C";

  // Resolve text color: merchant custom > preset > auto-detect
  const resolvedTextColor = cardTextColor || "#FFFFFF";
  const isLight = isLightColor(resolvedTextColor);

  // Gradient: if merchant has a bg image, use solid color overlay; otherwise creative gradient
  const cardStyle: React.CSSProperties = useMemo(() => {
    if (cardBackgroundImage) {
      return {
        background: `linear-gradient(165deg, ${hexToRGBA(primary, 0.92)}, ${hexToRGBA(secondary, 0.88)}), url(${cardBackgroundImage})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        color: resolvedTextColor,
        boxShadow: `0 20px 60px -12px ${hexToRGBA(primary, 0.45)}`,
      };
    }
    // Minimalist creative gradient — not flat, not busy
    return {
      background: `linear-gradient(165deg, ${primary} 0%, ${secondary} 55%, ${hexToRGBA(primary, 0.7)} 100%)`,
      color: resolvedTextColor,
      boxShadow: `0 20px 60px -12px ${hexToRGBA(primary, 0.45)}`,
    };
  }, [primary, secondary, cardBackgroundImage, resolvedTextColor]);

  const textSecondary = isLight ? "rgba(0,0,0,0.5)" : "rgba(255,255,255,0.5)";
  const textTertiary = isLight ? "rgba(0,0,0,0.3)" : "rgba(255,255,255,0.3)";
  const overlayBg = isLight ? "rgba(0,0,0,0.06)" : "rgba(255,255,255,0.08)";

  const illustrationSVG = useMemo(() => {
    if (!theme?.illustration) return null;
    return getIllustrationSVG(theme.illustration);
  }, [theme?.illustration]);

  // ── Not joined state ──
  if (!joined) {
    return (
      <section className="px-5">
        <div
          className="relative overflow-hidden rounded-[28px] p-6 text-center"
          style={cardStyle}
        >
          {cardBackgroundImage && (
            <img
              src={cardBackgroundImage}
              alt=""
              className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-15"
            />
          )}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.06]"
            style={{ color: resolvedTextColor }}
            dangerouslySetInnerHTML={{ __html: illustrationSVG ?? "" }}
          />

          <div className="relative">
            {merchantLogo && (
              <img src={merchantLogo} alt="" className="mx-auto h-12 w-12 rounded-2xl object-cover mb-3" />
            )}
            <p className="font-display text-2xl">{merchantName}</p>
            {merchantCategory && (
              <p className="mt-1 text-xs" style={{ color: textSecondary }}>{merchantCategory}</p>
            )}
            <p className="mt-4 text-sm" style={{ color: textSecondary }}>
              Join this store to earn points, track orders, and redeem rewards.
            </p>
            <button
              onClick={onJoin}
              disabled={joining}
              className="mt-5 inline-flex items-center gap-2 rounded-full px-8 py-3 text-sm font-semibold transition-all active:scale-95 disabled:opacity-60"
              style={{
                background: isLight ? primary : "#FFFFFF",
                color: isLight ? "#FFFFFF" : primary,
              }}
            >
              {joining ? "Joining…" : "Join & Start Earning"}
            </button>
          </div>
        </div>
      </section>
    );
  }

  // ── Joined state ──
  return (
    <section className="px-5">
      <div
        className="relative overflow-hidden rounded-[28px] p-6 pb-5"
        style={{ ...cardStyle, minHeight: 310 }}
      >
        {/* Background image overlay */}
        {cardBackgroundImage && (
          <img
            src={cardBackgroundImage}
            alt=""
            className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-20"
          />
        )}

        {/* Illustration */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.06]"
          style={{ color: resolvedTextColor }}
          dangerouslySetInnerHTML={{ __html: illustrationSVG ?? "" }}
        />

        {/* Subtle decorative orb — gradient accent */}
        <div
          className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full opacity-20 blur-3xl"
          style={{ background: `radial-gradient(circle, ${theme?.accent || hexToRGBA(primary, 0.4)}, transparent)` }}
        />

        {/* Top row: Logo + Name + Tier */}
        <div className="relative flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            {merchantLogo ? (
              <img
                src={merchantLogo}
                alt=""
                className="h-10 w-10 shrink-0 rounded-xl object-cover"
                style={{ background: overlayBg }}
              />
            ) : (
              <div className="h-10 w-10 shrink-0 rounded-xl" style={{ background: overlayBg }} />
            )}
            <div className="min-w-0">
              <p className="text-[9px] uppercase tracking-[0.22em]" style={{ color: textTertiary }}>
                Membership
              </p>
              <p className="mt-0.5 truncate font-display text-[22px] leading-tight">{merchantName}</p>
              {merchantCategory && (
                <p className="text-[11px]" style={{ color: textSecondary }}>{merchantCategory}</p>
              )}
            </div>
          </div>
          <span
            className="mt-0.5 shrink-0 rounded-full px-3 py-1.5 text-[9px] font-bold uppercase tracking-[0.15em]"
            style={{ background: overlayBg, color: resolvedTextColor }}
          >
            {tierIcon(tier)} {tierLabel(tier)}
          </span>
        </div>

        {/* Points — large, clean */}
        <div className="relative mt-6">
          <p className="text-[9px] uppercase tracking-[0.22em]" style={{ color: textTertiary }}>
            Available Points
          </p>
          <p
            className="font-display text-[56px] leading-none tracking-tight"
            style={{ letterSpacing: "-0.03em" }}
          >
            {points.toLocaleString()}
          </p>
        </div>

        {/* Stats row — 3 columns, minimal */}
        <div className="relative mt-5 grid grid-cols-3 gap-2">
          <div className="rounded-2xl p-3" style={{ background: overlayBg }}>
            <div className="flex items-center gap-1">
              <Flame className="h-3 w-3" style={{ color: theme?.accent || resolvedTextColor }} />
              <span className="text-[9px] uppercase tracking-widest" style={{ color: textTertiary }}>Streak</span>
            </div>
            <p className="font-display mt-1 text-xl leading-tight">{streak}</p>
            <p className="text-[10px]" style={{ color: textSecondary }}>days</p>
          </div>
          <div className="rounded-2xl p-3" style={{ background: overlayBg }}>
            <div className="flex items-center gap-1">
              <Star className="h-3 w-3" style={{ color: theme?.accent || resolvedTextColor }} />
              <span className="text-[9px] uppercase tracking-widest" style={{ color: textTertiary }}>Rewards</span>
            </div>
            <p className="font-display mt-1 text-xl leading-tight">{freeRewards}</p>
            <p className="text-[10px]" style={{ color: textSecondary }}>available</p>
          </div>
          <div className="rounded-2xl p-3" style={{ background: overlayBg }}>
            <div className="flex items-center gap-1">
              <ShoppingBag className="h-3 w-3" style={{ color: theme?.accent || resolvedTextColor }} />
              <span className="text-[9px] uppercase tracking-widest" style={{ color: textTertiary }}>Orders</span>
            </div>
            <p className="font-display mt-1 text-xl leading-tight">{ordersCount}</p>
            <p className="text-[10px]" style={{ color: textSecondary }}>total</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="relative mt-4">
          <div className="flex items-center gap-1.5">
            <TrendingUp className="h-3 w-3" style={{ color: theme?.accent || resolvedTextColor }} />
            <span className="text-[10px] font-medium" style={{ color: textSecondary }}>
              {Math.round(progressPercent)}% to next tier
            </span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full" style={{ background: overlayBg }}>
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${Math.min(progressPercent, 100)}%`,
                background: isLight
                  ? `linear-gradient(90deg, ${primary}, ${hexToRGBA(primary, 0.7)})`
                  : `linear-gradient(90deg, ${theme?.accent || "#FFFFFF"}, ${theme?.accent || "#FFFFFF"}88)`,
              }}
            />
          </div>
        </div>

        {/* Bottom row: member + card number */}
        <div className="relative mt-5 flex items-end justify-between">
          <div>
            <p className="text-[9px] uppercase tracking-widest" style={{ color: textTertiary }}>Member</p>
            <p className="mt-0.5 text-sm font-medium">{memberName}</p>
          </div>
          <p className="font-mono text-[11px] tracking-wider" style={{ color: textSecondary }}>
            {cardNumber}
          </p>
        </div>

        {/* Powered by */}
        <p className="relative mt-3 text-right text-[8px] tracking-wide" style={{ color: textTertiary }}>
          Powered by Zentro
        </p>
      </div>
    </section>
  );
}
