import { createFileRoute } from "@tanstack/react-router";
import { Plus, Pencil, Trash2, X, Check, AlertCircle, Loader2, Gift } from "lucide-react";
import { useState, useEffect } from "react";
import { loyaltyApi, missionApi, punchCardApi, transactionApi, type Reward, type Mission, type MerchantPunchCard, type PointTransaction } from "@/lib/api";

export const Route = createFileRoute("/merchant/loyalty")({
  head: () => ({ meta: [{ title: "Loyalty · Merchant · Zentro" }] }),
  component: MerchantLoyalty,
});

interface RedeemResult {
  success: boolean;
  message: string;
  customer_name?: string;
  points_deducted?: number;
}

function MerchantLoyalty() {
  const [tab, setTab] = useState<"missions" | "rewards" | "punch_cards" | "transactions" | "redeem">("missions");

  // ── Missions ───────────────────────────────────────────────────────────────
  const [missions, setMissions]               = useState<Mission[]>([]);
  const [missionsLoading, setMissionsLoading] = useState(true);
  const [missionsError, setMissionsError]     = useState("");
  const [missionModal, setMissionModal]       = useState<"new" | Mission | null>(null);
  const [missionSaving, setMissionSaving]     = useState(false);

  // ── Rewards ────────────────────────────────────────────────────────────────
  const [rewards, setRewards]               = useState<Reward[]>([]);
  const [rewardsLoading, setRewardsLoading] = useState(true);
  const [rewardsError, setRewardsError]     = useState("");
  const [rewardModal, setRewardModal]       = useState<"new" | Reward | null>(null);
  const [rewardSaving, setRewardSaving]     = useState(false);

  // ── Redeem ─────────────────────────────────────────────────────────────────
  const [redeemCode, setRedeemCode]         = useState("");
  const [redeemLoading, setRedeemLoading]   = useState(false);
  const [redeemResult, setRedeemResult]     = useState<RedeemResult | null>(null);

  useEffect(() => {
    missionApi.merchantMissions()
      .then(setMissions)
      .catch((e: any) => setMissionsError(e.message))
      .finally(() => setMissionsLoading(false));
  }, []);

  useEffect(() => {
    loyaltyApi.getRewards()
      .then(setRewards)
      .catch((e: any) => setRewardsError(e.message))
      .finally(() => setRewardsLoading(false));
  }, []);

  // ── Punch Cards ────────────────────────────────────────────────────────────
  const [punchCards, setPunchCards] = useState<MerchantPunchCard[]>([]);
  const [punchCardsLoading, setPunchCardsLoading] = useState(true);
  const [punchCardsError, setPunchCardsError] = useState("");
  const [punchCardModal, setPunchCardModal] = useState<"new" | MerchantPunchCard | null>(null);
  const [punchCardSaving, setPunchCardSaving] = useState(false);

  useEffect(() => {
    punchCardApi.merchantList()
      .then(setPunchCards)
      .catch((e: any) => setPunchCardsError(e.message))
      .finally(() => setPunchCardsLoading(false));
  }, []);

  async function savePunchCard(data: Partial<MerchantPunchCard>) {
    setPunchCardSaving(true);
    setPunchCardsError("");
    try {
      if (typeof punchCardModal === "object" && punchCardModal !== null) {
        const updated = await punchCardApi.merchantUpdate(punchCardModal.id, data);
        setPunchCards((pcs) => pcs.map((pc) => pc.id === updated.id ? updated : pc));
      } else {
        const created = await punchCardApi.merchantCreate(data);
        setPunchCards((pcs) => [created, ...pcs]);
      }
      setPunchCardModal(null);
    } catch (e: any) {
      setPunchCardsError(e.message);
    } finally {
      setPunchCardSaving(false);
    }
  }

  async function togglePunchCard(pc: MerchantPunchCard) {
    try {
      const updated = await punchCardApi.merchantUpdate(pc.id, { is_active: !pc.is_active });
      setPunchCards((pcs) => pcs.map((x) => x.id === pc.id ? updated : x));
    } catch (e: any) {
      setPunchCardsError(e.message);
    }
  }

  // ── Transactions ───────────────────────────────────────────────────────────
  const [transactions, setTransactions] = useState<PointTransaction[]>([]);
  const [transactionsLoading, setTransactionsLoading] = useState(true);
  const [transactionsError, setTransactionsError] = useState("");

  useEffect(() => {
    if (tab === "transactions") {
      setTransactionsLoading(true);
      transactionApi.merchantList()
        .then(setTransactions)
        .catch((e: any) => setTransactionsError(e.message))
        .finally(() => setTransactionsLoading(false));
    }
  }, [tab]);

  // ── Mission CRUD ───────────────────────────────────────────────────────────
  async function saveMission(data: Omit<Mission, "id" | "merchant_id" | "created_at">) {
    setMissionSaving(true);
    setMissionsError("");
    try {
      if (typeof missionModal === "object" && missionModal !== null) {
        const updated = await missionApi.update(missionModal.id, data);
        setMissions((ms) => ms.map((m) => m.id === updated.id ? updated : m));
      } else {
        const created = await missionApi.create(data);
        setMissions((ms) => [created, ...ms]);
      }
      setMissionModal(null);
    } catch (e: any) {
      setMissionsError(e.message);
    } finally {
      setMissionSaving(false);
    }
  }

  async function deleteMission(id: string) {
    try {
      await missionApi.delete(id);
      setMissions((ms) => ms.filter((m) => m.id !== id));
    } catch (e: any) {
      setMissionsError(e.message);
    }
  }

  async function toggleMission(m: Mission) {
    try {
      const updated = await missionApi.update(m.id, { is_active: !m.is_active });
      setMissions((ms) => ms.map((x) => x.id === m.id ? updated : x));
    } catch (e: any) {
      setMissionsError(e.message);
    }
  }

  // ── Reward CRUD ────────────────────────────────────────────────────────────
  async function saveReward(data: Omit<Reward, "id" | "merchant_id" | "created_at">) {
    setRewardSaving(true);
    setRewardsError("");
    try {
      if (typeof rewardModal === "object" && rewardModal !== null) {
        const updated = await loyaltyApi.updateReward(rewardModal.id, data);
        setRewards((rs) => rs.map((r) => r.id === updated.id ? updated : r));
      } else {
        const created = await loyaltyApi.createReward(data);
        setRewards((rs) => [created, ...rs]);
      }
      setRewardModal(null);
    } catch (e: any) {
      setRewardsError(e.message);
    } finally {
      setRewardSaving(false);
    }
  }

  async function deleteReward(id: string) {
    try {
      await loyaltyApi.deleteReward(id);
      setRewards((rs) => rs.filter((r) => r.id !== id));
    } catch (e: any) {
      setRewardsError(e.message);
    }
  }

  async function toggleReward(r: Reward) {
    try {
      const updated = await loyaltyApi.updateReward(r.id, { is_active: !r.is_active });
      setRewards((rs) => rs.map((x) => x.id === r.id ? updated : x));
    } catch (e: any) {
      setRewardsError(e.message);
    }
  }

  // ── Confirm redemption code ────────────────────────────────────────────────
  async function handleConfirmCode() {
    if (!redeemCode.trim()) return;
    setRedeemLoading(true);
    setRedeemResult(null);
    try {
      const result = await loyaltyApi.confirmRedemption(redeemCode.trim().toUpperCase());
      setRedeemResult({
        success: true,
        message: `Redemption confirmed!`,
        customer_name: result.customer_name,
        points_deducted: result.points_deducted,
      });
      setRedeemCode("");
    } catch (e: any) {
      setRedeemResult({ success: false, message: e.message });
    } finally {
      setRedeemLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Engine</p>
        <h1 className="font-display mt-1 text-5xl text-ink">Loyalty</h1>
      </div>

      <div className="flex gap-1 rounded-2xl bg-mist p-1 overflow-x-auto">
        {(["missions", "rewards", "punch_cards", "transactions", "redeem"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 min-w-[100px] rounded-xl py-2 text-xs font-medium capitalize transition-colors ${tab === t ? "bg-white text-ink shadow-sm" : "text-muted-foreground hover:text-ink"}`}>
            {t.replace("_", " ")}
          </button>
        ))}
      </div>

      {tab === "missions" && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="font-display text-2xl text-ink">Missions</h2>
              <p className="text-xs text-muted-foreground">Challenges customers can complete for points.</p>
            </div>
            <button onClick={() => setMissionModal("new")}
              className="inline-flex h-9 items-center gap-1.5 rounded-full bg-ink px-4 text-xs font-medium text-primary-foreground">
              <Plus className="h-3.5 w-3.5" /> New
            </button>
          </div>
          {missionsError && <ErrorBanner message={missionsError} />}
          {missionsLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : missions.length === 0 ? (
            <EmptyState icon="🎯" title="No missions yet" sub="Create your first mission to engage customers." />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {missions.map((m) => (
                <div key={m.id} className={`glass rounded-3xl p-5 transition-opacity ${m.is_active ? "" : "opacity-60"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-ink">{m.title}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{m.description}</p>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <IconBtn onClick={() => setMissionModal(m)}><Pencil className="h-3.5 w-3.5" /></IconBtn>
                      <IconBtn onClick={() => deleteMission(m.id)} danger><Trash2 className="h-3.5 w-3.5" /></IconBtn>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between">
                    <div className="flex gap-3">
                      <Chip label="Target" value={`${m.target_count} orders`} />
                      <Chip label="Reward" value={`${m.reward_points} pts`} />
                    </div>
                    <Toggle active={m.is_active} onToggle={() => toggleMission(m)} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {tab === "rewards" && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="font-display text-2xl text-ink">Rewards</h2>
              <p className="text-xs text-muted-foreground">Items customers can redeem with points.</p>
            </div>
            <button onClick={() => setRewardModal("new")}
              className="inline-flex h-9 items-center gap-1.5 rounded-full bg-ink px-4 text-xs font-medium text-primary-foreground">
              <Plus className="h-3.5 w-3.5" /> New
            </button>
          </div>
          {rewardsError && <ErrorBanner message={rewardsError} />}
          {rewardsLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : rewards.length === 0 ? (
            <EmptyState icon="🎁" title="No rewards yet" sub="Add a reward so customers can redeem their points." />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {rewards.map((r) => (
                <div key={r.id} className={`glass rounded-3xl p-5 transition-opacity ${r.is_active ? "" : "opacity-60"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className="grid h-12 w-12 place-items-center rounded-xl bg-mist text-2xl">
                        {r.emoji || <Gift className="h-5 w-5 text-ember" />}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate font-medium text-ink">{r.name}</p>
                        <p className="text-xs text-muted-foreground line-clamp-1">{r.description}</p>
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <IconBtn onClick={() => setRewardModal(r)}><Pencil className="h-3.5 w-3.5" /></IconBtn>
                      <IconBtn onClick={() => deleteReward(r.id)} danger><Trash2 className="h-3.5 w-3.5" /></IconBtn>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between">
                    <div className="flex gap-3">
                      <Chip label="Cost"  value={`${r.points_cost} pts`} />
                      <Chip label="Stock" value={r.stock === -1 ? "Unlimited" : `${r.stock} left`} />
                    </div>
                    <Toggle active={r.is_active} onToggle={() => toggleReward(r)} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {tab === "punch_cards" && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="font-display text-2xl text-ink">Punch Cards</h2>
              <p className="text-xs text-muted-foreground">Digital loyalty cards for streaks or orders.</p>
            </div>
            <button onClick={() => setPunchCardModal("new")}
              className="inline-flex h-9 items-center gap-1.5 rounded-full bg-ink px-4 text-xs font-medium text-primary-foreground">
              <Plus className="h-3.5 w-3.5" /> New
            </button>
          </div>
          {punchCardsError && <ErrorBanner message={punchCardsError} />}
          {punchCardsLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : punchCards.length === 0 ? (
            <EmptyState icon="🎟️" title="No punch cards yet" sub="Create your first punch card." />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {punchCards.map((pc) => (
                <div key={pc.id} className={`glass rounded-3xl p-5 transition-opacity ${pc.is_active ? "" : "opacity-60"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-ink">{pc.name}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{pc.reward_text}</p>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <IconBtn onClick={() => setPunchCardModal(pc)}><Pencil className="h-3.5 w-3.5" /></IconBtn>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between">
                    <div className="flex gap-3">
                      <Chip label="Mode" value={pc.mode === "per_order" ? "Per Order" : "Per Streak"} />
                      <Chip label="Stamps" value={String(pc.stamps_required)} />
                    </div>
                    <Toggle active={pc.is_active} onToggle={() => togglePunchCard(pc)} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {tab === "transactions" && (
        <section>
          <div className="mb-4">
            <h2 className="font-display text-2xl text-ink">Point Transactions</h2>
            <p className="text-xs text-muted-foreground">Log of all points awarded or redeemed across your store.</p>
          </div>
          {transactionsError && <ErrorBanner message={transactionsError} />}
          {transactionsLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : transactions.length === 0 ? (
            <EmptyState icon="📝" title="No transactions yet" sub="Transactions will appear here when customers earn or spend points." />
          ) : (
            <div className="space-y-2 overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="font-medium p-3">Date</th>
                    <th className="font-medium p-3">Customer</th>
                    <th className="font-medium p-3">Type</th>
                    <th className="font-medium p-3">Points</th>
                    <th className="font-medium p-3">Balance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-mist/50 transition-colors">
                      <td className="p-3 text-xs text-muted-foreground">{new Date(tx.created_at).toLocaleString()}</td>
                      <td className="p-3">{tx.customer_name}</td>
                      <td className="p-3 text-xs capitalize">{tx.transaction_type.toLowerCase().replace("_", " ")}</td>
                      <td className={`p-3 font-medium ${tx.points >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                        {tx.points > 0 ? "+" : ""}{tx.points}
                      </td>
                      <td className="p-3 text-muted-foreground">{tx.balance_after}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {tab === "redeem" && (
        <section className="space-y-6">
          <div className="glass-strong rounded-3xl p-6">
            <h2 className="font-display text-2xl text-ink">Confirm code</h2>
            <p className="mt-1 text-xs text-muted-foreground">Enter the redemption code the customer shows you.</p>
            <div className="mt-4 flex gap-2">
              <input value={redeemCode} onChange={(e) => setRedeemCode(e.target.value.toUpperCase())}
                placeholder="Paste code here"
                className="flex-1 rounded-xl border border-border bg-background px-4 py-2.5 font-mono text-sm uppercase tracking-widest text-ink placeholder:normal-case placeholder:tracking-normal placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ink/20" />
              <button onClick={handleConfirmCode} disabled={redeemLoading || redeemCode.length < 4}
                className="inline-flex h-10 items-center gap-2 rounded-xl bg-ink px-4 text-sm font-medium text-primary-foreground disabled:opacity-50">
                {redeemLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Confirm
              </button>
            </div>
            {redeemResult && <ResultBanner result={redeemResult} />}
          </div>
        </section>
      )}

      {missionModal !== null && (
        <MissionModal initial={missionModal === "new" ? null : missionModal}
          saving={missionSaving} onSave={saveMission} onClose={() => setMissionModal(null)} />
      )}
      {rewardModal !== null && (
        <RewardModal initial={rewardModal === "new" ? null : rewardModal}
          saving={rewardSaving} onSave={saveReward} onClose={() => setRewardModal(null)} />
      )}
      {punchCardModal !== null && (
        <PunchCardModal initial={punchCardModal === "new" ? null : punchCardModal}
          saving={punchCardSaving} onSave={savePunchCard} onClose={() => setPunchCardModal(null)} />
      )}
    </div>
  );
}

// ── Shared sub-components ─────────────────────────────────────────────────────

const inputCls = "w-full rounded-2xl border border-border bg-background px-4 py-2.5 text-sm text-ink placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-ink/20";

function ErrorBanner({ message }: { message: string }) {
  return <div className="mb-3 flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"><AlertCircle className="h-4 w-4 shrink-0" /> {message}</div>;
}

function ResultBanner({ result }: { result: RedeemResult }) {
  return (
    <div className={`mt-4 flex items-start gap-3 rounded-2xl p-4 ${result.success ? "bg-emerald-50" : "bg-rose-50"}`}>
      {result.success ? <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" /> : <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />}
      <div>
        <p className={`text-sm font-medium ${result.success ? "text-emerald-700" : "text-rose-600"}`}>{result.message}</p>
        {result.success && result.customer_name && (
          <p className="mt-0.5 text-xs text-emerald-600">
            {result.customer_name}{result.points_deducted ? ` · −${result.points_deducted} pts` : ""}
          </p>
        )}
      </div>
    </div>
  );
}

function EmptyState({ icon, title, sub }: { icon: string; title: string; sub: string }) {
  return <div className="glass rounded-3xl py-12 text-center"><p className="text-4xl">{icon}</p><p className="mt-3 text-sm font-medium text-ink">{title}</p><p className="mt-1 text-xs text-muted-foreground">{sub}</p></div>;
}

function Toggle({ active, onToggle }: { active: boolean; onToggle: () => void }) {
  return <button onClick={onToggle} className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${active ? "bg-ink" : "bg-border"}`}><span className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${active ? "translate-x-4" : "translate-x-1"}`} /></button>;
}

function IconBtn({ onClick, danger, children }: { onClick: () => void; danger?: boolean; children: React.ReactNode }) {
  return <button onClick={onClick} className={`flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors ${danger ? "hover:bg-rose-50 hover:text-rose-500" : "hover:bg-mist"}`}>{children}</button>;
}

function Chip({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</p><p className="text-xs font-medium text-ink">{value}</p></div>;
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 backdrop-blur-sm sm:items-center" onClick={onClose}>
      <div className="w-full max-w-md space-y-4 rounded-t-3xl bg-background p-6 shadow-2xl sm:rounded-3xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-display text-xl text-ink">{title}</h3>
          <button onClick={onClose} className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground hover:bg-mist"><X className="h-4 w-4" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function FL({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><label className="text-[11px] uppercase tracking-widest text-muted-foreground">{label}</label>{children}</div>;
}

function MissionModal({ initial, saving, onSave, onClose }: {
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

function RewardModal({ initial, saving, onSave, onClose }: {
  initial: Reward | null; saving: boolean;
  onSave: (d: Omit<Reward, "id" | "merchant_id" | "created_at">) => void; onClose: () => void;
}) {
  const [name, setName]           = useState(initial?.name ?? "");
  const [description, setDesc]    = useState(initial?.description ?? "");
  const [emoji, setEmoji]         = useState(initial?.emoji ?? "🎁");
  const [pointsCost, setPoints]   = useState(String(initial?.points_cost ?? 100));
  const [stock, setStock]         = useState(String(initial?.stock ?? -1));
  return (
    <Modal title={initial ? "Edit reward" : "New reward"} onClose={onClose}>
      <div className="space-y-3">
        <FL label="Reward name"><input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Free flat white" className={inputCls} /></FL>
        <FL label="Description"><input value={description} onChange={(e) => setDesc(e.target.value)} placeholder="What the customer gets" className={inputCls} /></FL>
        <div className="grid grid-cols-3 gap-3">
          <FL label="Emoji"><input value={emoji} onChange={(e) => setEmoji(e.target.value)} className={inputCls} maxLength={2} /></FL>
          <FL label="Points cost"><input type="number" min={1} value={pointsCost} onChange={(e) => setPoints(e.target.value)} className={inputCls} /></FL>
          <FL label="Stock (-1=∞)"><input type="number" min={-1} value={stock} onChange={(e) => setStock(e.target.value)} className={inputCls} /></FL>
        </div>
        <div className="flex gap-2 pt-2">
          <button onClick={onClose} className="h-10 flex-1 rounded-2xl border border-border text-sm text-muted-foreground">Cancel</button>
          <button
            onClick={() => onSave({ name, description, emoji, points_cost: Number(pointsCost), stock: Number(stock), is_active: initial?.is_active ?? true })}
            disabled={saving || !name.trim()}
            className="h-10 flex-1 rounded-2xl bg-ink text-sm font-medium text-primary-foreground disabled:opacity-50">
            {saving ? "Saving…" : initial ? "Save changes" : "Create"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

function PunchCardModal({ initial, saving, onSave, onClose }: {
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
