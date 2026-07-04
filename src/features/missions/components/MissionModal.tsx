import React, { useState } from "react";
import { Mission } from "@/lib/api";
import { Modal, FL, inputCls } from "@/components/LoyaltyShared";

export function MissionModal({ initial, saving, onSave, onClose }: {
  initial: Mission | null; saving: boolean;
  onSave: (d: Omit<Mission, "id" | "merchant_id" | "created_at">) => void; onClose: () => void;
}) {
  const [title, setTitle]       = useState(initial?.title ?? "");
  const [description, setDesc]  = useState(initial?.description ?? "");
  const [target, setTarget]     = useState(String(initial?.target_count ?? 5));
  const [reward, setReward]     = useState(String(initial?.reward_points ?? 100));
  const [type, setType]         = useState(initial?.mission_type ?? "order_count");
  return (
    <Modal title={initial ? "Edit mission" : "New mission"} onClose={onClose}>
      <div className="space-y-3">
        <FL label="Title"><input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. First 5 orders" className={inputCls} /></FL>
        <FL label="Description"><input value={description} onChange={(e) => setDesc(e.target.value)} placeholder="Shown to customers" className={inputCls} /></FL>
        <FL label="Type">
          <select value={type} onChange={(e) => setType(e.target.value as typeof type)} className={inputCls}>
            <option value="order_count">Order Count</option>
            <option value="spend_amount">Spend Amount</option>
            <option value="visit_streak">Visit Streak</option>
          </select>
        </FL>
        <div className="grid grid-cols-2 gap-3">
          <FL label="Target"><input type="number" min={1} value={target} onChange={(e) => setTarget(e.target.value)} className={inputCls} /></FL>
          <FL label="Points reward"><input type="number" min={1} value={reward} onChange={(e) => setReward(e.target.value)} className={inputCls} /></FL>
        </div>
        <div className="flex gap-2 pt-2">
          <button onClick={onClose} className="h-10 flex-1 rounded-2xl border border-border text-sm text-muted-foreground">Cancel</button>
          <button
            onClick={() => onSave({ title, description, icon: "🎯", target_count: Number(target), reward_points: Number(reward), mission_type: type as any, is_active: initial?.is_active ?? true })}
            disabled={saving || !title.trim()}
            className="h-10 flex-1 rounded-2xl bg-ink text-sm font-medium text-primary-foreground disabled:opacity-50">
            {saving ? "Saving…" : initial ? "Save changes" : "Create"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
