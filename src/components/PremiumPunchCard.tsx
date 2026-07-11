import { useState } from "react";
import { Gift, CreditCard } from "lucide-react";
import type { CustomerPunchCard } from "@/lib/api";

interface PremiumPunchCardProps {
  card: CustomerPunchCard;
  onRedeem?: (id: string) => void;
  redeeming?: boolean;
}

export function PremiumPunchCard({ card, onRedeem, redeeming }: PremiumPunchCardProps) {
  const config = card.punch_card;
  if (!config) return null;

  const punchesNeeded = config.stamps_required;
  const punchCount = card.current_stamps;
  const freeRewardReady = card.is_completed && !card.is_redeemed;
  const remaining = Math.max(punchesNeeded - punchCount, 0);

  return (
    <div
      className="rounded-[28px] bg-card p-5 shadow-[0_8px_30px_rgba(0,0,0,0.06)] dark:shadow-[0_8px_30px_rgba(0,0,0,0.3)]"
      style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded border border-border flex items-center justify-center">
            <CreditCard className="h-3 w-3 text-muted-foreground" />
          </div>
          <span className="text-[15px] font-semibold text-foreground">Punch Card</span>
        </div>
        <span className="text-[15px] font-medium text-muted-foreground">
          {punchCount} / {punchesNeeded} punches
        </span>
      </div>

      {/* Reward text */}
      <p className="mt-2 text-[14px] font-medium text-muted-foreground">
        Reward: <span className="font-semibold text-foreground">{config.reward_text}</span>
      </p>

      {/* Punch strip */}
      <div
        className="relative mt-4 h-[52px] rounded-full overflow-hidden"
        style={{
          backgroundImage:
            config.animated_gif_background || config.background_image
              ? `url(${config.animated_gif_background || config.background_image})`
              : undefined,
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundColor:
            config.animated_gif_background || config.background_image
              ? undefined
              : config.color_scheme || "#1e293b",
        }}
      >
        <div className="relative flex items-center justify-between h-full px-3">
          {Array.from({ length: punchesNeeded }).map((_, i) => {
            const filled = i < punchCount || freeRewardReady;
            const isFreeSlot = freeRewardReady && i === punchesNeeded - 1;

            return (
              <div
                key={i}
                className="w-[30px] h-[30px] rounded-full flex items-center justify-center transition-all duration-300"
                style={{
                  background: filled
                    ? isFreeSlot
                      ? config.color_scheme || "#10b981"
                      : "rgba(255,255,255,0.95)"
                    : "rgba(255,255,255,0.75)",
                  backdropFilter: filled ? undefined : "blur(8px)",
                  color: filled && !isFreeSlot ? config.color_scheme || "#202124" : "#6B7280",
                  boxShadow: filled ? "0 2px 8px rgba(0,0,0,0.12)" : undefined,
                }}
              >
                {isFreeSlot ? (
                  <Gift className="h-4 w-4 text-white" />
                ) : filled ? (
                  config.stamp_gif_url ? (
                    <img
                      src={config.stamp_gif_url}
                      alt=""
                      className="w-5 h-5 rounded-full object-cover"
                    />
                  ) : (
                    <span className="text-sm">{config.stamp_icon || "✨"}</span>
                  )
                ) : (
                  <span className="text-[13px] font-medium text-gray-500 dark:text-gray-400">{i + 1}</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3 h-[5px] rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-foreground transition-all duration-500"
          style={{ width: `${(punchCount / punchesNeeded) * 100}%` }}
        />
      </div>

      {/* Reward card */}
      <div className="mt-4 rounded-[22px] bg-muted p-4">
        <div className="flex items-center justify-between">
          <span className="text-[18px] font-semibold text-foreground">
            Get {remaining > 0 ? `${remaining} more` : "reward ready"}
          </span>
          <span className="text-[15px] font-medium text-muted-foreground">
            {remaining > 0 ? `${remaining} more` : "Done!"}
          </span>
        </div>
        <p className="mt-1 text-[14px] text-muted-foreground">
          {punchesNeeded} punches → 🎁 {config.reward_text}
        </p>
      </div>

      {/* Redeem button */}
      {freeRewardReady && onRedeem && (
        <button
          onClick={() => onRedeem(card.id)}
          disabled={redeeming}
          className="mt-4 w-full rounded-2xl py-3 text-[15px] font-semibold text-primary-foreground transition-opacity disabled:opacity-50 gradient-ember"
        >
          {redeeming ? "Redeeming..." : "Redeem Free Reward"}
        </button>
      )}
    </div>
  );
}
