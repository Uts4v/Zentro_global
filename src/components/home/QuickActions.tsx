// src/components/home/QuickActions.tsx
// Two focused action cards: Scan QR + Transfer Points
import { ScanLine, ArrowLeftRight, ChevronRight } from "lucide-react";

interface QuickActionsProps {
  onScanQR: () => void;
  onTransfer: () => void;
  availablePoints: number;
  merchantColor?: string;
}

export function QuickActions({ onScanQR, onTransfer, availablePoints, merchantColor }: QuickActionsProps) {
  const accent = merchantColor || "var(--ink)";

  return (
    <section className="px-5">
      <div className="grid grid-cols-2 gap-3">
        {/* Scan QR */}
        <button
          onClick={onScanQR}
          className="group relative overflow-hidden rounded-[20px] bg-white p-4 text-left transition-all active:scale-[0.97]"
          style={{
            boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 8px 24px -8px rgba(0,0,0,0.06)",
          }}
        >
          <div
            className="mb-3 grid h-10 w-10 place-items-center rounded-xl transition-colors duration-300"
            style={{ background: `${accent}12`, color: accent }}
          >
            <ScanLine className="h-5 w-5" strokeWidth={1.8} />
          </div>
          <p className="text-sm font-semibold text-[#1A1A1A]">Scan QR</p>
          <p className="mt-0.5 text-[11px] leading-snug text-[#1A1A1A]/50">Scan table QR to order</p>
          <ChevronRight
            className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#1A1A1A]/20 transition-transform group-hover:translate-x-0.5"
          />
        </button>

        {/* Transfer Points */}
        <button
          onClick={onTransfer}
          className="group relative overflow-hidden rounded-[20px] bg-white p-4 text-left transition-all active:scale-[0.97]"
          style={{
            boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 8px 24px -8px rgba(0,0,0,0.06)",
          }}
        >
          <div
            className="mb-3 grid h-10 w-10 place-items-center rounded-xl transition-colors duration-300"
            style={{ background: "#10B98112", color: "#10B981" }}
          >
            <ArrowLeftRight className="h-5 w-5" strokeWidth={1.8} />
          </div>
          <p className="text-sm font-semibold text-[#1A1A1A]">Transfer Points</p>
          <p className="mt-0.5 text-[11px] leading-snug text-[#1A1A1A]/50">Send or receive points</p>
          <div className="mt-2.5 flex items-center justify-between">
            <span className="rounded-full bg-[#10B98112] px-2.5 py-1 text-[10px] font-semibold text-[#10B981]">
              {availablePoints} pts
            </span>
          </div>
        </button>
      </div>
    </section>
  );
}
