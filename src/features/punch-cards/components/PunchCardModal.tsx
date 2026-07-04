import React, { useState } from "react";
import { MerchantPunchCard } from "@/lib/api";
import { Modal, FL, inputCls } from "@/components/LoyaltyShared";

export function PunchCardModal({ initial, saving, onSave, onClose }: {
  initial: MerchantPunchCard | null; saving: boolean;
  onSave: (d: Partial<MerchantPunchCard>) => void; onClose: () => void;
}) {
  const [name, setName]                   = useState(initial?.name ?? "");
  const [mode, setMode]                   = useState(initial?.mode ?? "per_order");
  const [stampsRequired, setStamps]       = useState(String(initial?.stamps_required ?? 5));
  const [rewardText, setRewardText]       = useState(initial?.reward_text ?? "");
  const [stampIcon, setStampIcon]         = useState(initial?.stamp_icon ?? "✨");
  const [colorScheme, setColorScheme]     = useState(initial?.color_scheme ?? "#1e293b");

  return (
    <Modal title={initial ? "Edit punch card" : "New punch card"} onClose={onClose}>
      <div className="space-y-3 max-h-[80vh] overflow-y-auto px-1 pb-1">
        <FL label="Card name"><input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Free Coffee Card" className={inputCls} /></FL>
        <FL label="Reward text"><input value={rewardText} onChange={(e) => setRewardText(e.target.value)} placeholder="e.g. 1 Free Iced Latte" className={inputCls} /></FL>
        
        <div className="grid grid-cols-2 gap-3">
          <FL label="Mode">
            <select value={mode} onChange={(e) => setMode(e.target.value as any)} className={inputCls}>
              <option value="per_order">Per Order</option>
              <option value="per_streak">Per Streak (12h gap)</option>
            </select>
          </FL>
          <FL label="Stamps required"><input type="number" min={1} value={stampsRequired} onChange={(e) => setStamps(e.target.value)} className={inputCls} /></FL>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          <FL label="Stamp Icon (Emoji)"><input value={stampIcon} onChange={(e) => setStampIcon(e.target.value)} className={inputCls} maxLength={2} /></FL>
          <FL label="Theme Color"><input type="color" value={colorScheme} onChange={(e) => setColorScheme(e.target.value)} className={`${inputCls} p-1 h-10`} /></FL>
        </div>

        <div className="flex gap-2 pt-2">
          <button onClick={onClose} className="h-10 flex-1 rounded-2xl border border-border text-sm text-muted-foreground">Cancel</button>
          <button
            onClick={() => onSave({ name, mode: mode as any, stamps_required: Number(stampsRequired), reward_text: rewardText, stamp_icon: stampIcon, color_scheme: colorScheme, is_active: initial?.is_active ?? true })}
            disabled={saving || !name.trim() || !rewardText.trim()}
            className="h-10 flex-1 rounded-2xl bg-ink text-sm font-medium text-primary-foreground disabled:opacity-50">
            {saving ? "Saving…" : initial ? "Save changes" : "Create"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
