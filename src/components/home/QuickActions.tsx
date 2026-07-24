// src/components/home/QuickActions.tsx
// Two minimalist action tiles matching clean design system: Scan QR + Transfer Points
import { motion } from "framer-motion";
import { ScanLine, ArrowLeftRight, ArrowRight } from "lucide-react";

interface QuickActionsProps {
  onScanQR: () => void;
  onTransfer: () => void;
  availablePoints: number;
  merchantColor?: string;
}

export function QuickActions({ onScanQR, onTransfer, availablePoints }: QuickActionsProps) {
  return (
    <section className="px-5">
      <div className="grid grid-cols-2 gap-3">
        {/* Scan to Order (Clean Minimal White Tile) */}
        <motion.button
          onClick={onScanQR}
          className="group relative overflow-hidden bg-white p-4.5 pb-12 text-left transition-all"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          whileTap={{ scale: 0.97 }}
          style={{
            borderRadius: 28,
            boxShadow: "0 12px 36px rgba(0,0,0,0.04)",
            border: "1px solid #F0ECE6",
          }}
        >
          <div className="relative mb-3.5 flex h-11 w-11 items-center justify-center rounded-2xl bg-[#FFEFEA] text-[#FF5238] transition-transform duration-300 group-active:scale-95">
            <ScanLine className="h-5.5 w-5.5" strokeWidth={2} />
          </div>

          <p className="relative text-[15px] font-extrabold text-[#18102B]">Scan QR</p>
          <p className="relative mt-0.5 text-[11px] font-medium leading-snug text-[#7D7D9C]">
            Scan table QR to order
          </p>

          <span className="absolute bottom-4 right-4 flex h-7 w-7 items-center justify-center rounded-full bg-[#FAF8F5] text-[#FF5238] transition-all group-hover:translate-x-0.5">
            <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.5} />
          </span>
        </motion.button>

        {/* Transfer Points (Clean Minimal White Tile) */}
        <motion.button
          onClick={onTransfer}
          className="group relative overflow-hidden bg-white p-4.5 pb-12 text-left transition-all"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          whileTap={{ scale: 0.97 }}
          style={{
            borderRadius: 28,
            boxShadow: "0 12px 36px rgba(0,0,0,0.04)",
            border: "1px solid #F0ECE6",
          }}
        >
          {/* Points Balance Badge */}
          <span
            className="absolute top-4 right-4 rounded-full px-2.5 py-0.5 text-[10px] font-extrabold text-white shadow-xs"
            style={{ background: "#10B981" }}
          >
            {availablePoints} pts
          </span>

          <div className="relative mb-3.5 flex h-11 w-11 items-center justify-center rounded-2xl bg-[#EBFBF3] text-[#10B981] transition-transform duration-300 group-active:scale-95">
            <ArrowLeftRight className="h-5.5 w-5.5" strokeWidth={2} />
          </div>

          <p className="relative text-[15px] font-extrabold text-[#18102B]">Transfer Points</p>
          <p className="relative mt-0.5 text-[11px] font-medium leading-snug text-[#7D7D9C]">
            Send or receive points
          </p>

          <span className="absolute bottom-4 right-4 flex h-7 w-7 items-center justify-center rounded-full bg-[#FAF8F5] text-[#10B981] transition-all group-hover:translate-x-0.5">
            <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.5} />
          </span>
        </motion.button>
      </div>
    </section>
  );
}
