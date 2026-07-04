// src/routes/merchant.store.tsx
import { createFileRoute } from "@tanstack/react-router";
import { MerchantStorePage } from "@/features/business-profile/pages/MerchantStorePage";
import { MerchantSpecialsPage } from "@/features/catalog/pages/MerchantSpecialsPage";
import { useState } from "react";

export const Route = createFileRoute("/merchant/store")({
  head: () => ({ meta: [{ title: "Store · Merchant · Zentro" }] }),
  component: MerchantStoreRoute,
});

function MerchantStoreRoute() {
  const [tab, setTab] = useState<"profile" | "specials">("profile");

  return (
    <div className="space-y-6">
      {/* Tab switcher */}
      <div className="flex gap-1 rounded-2xl bg-mist p-1 w-fit">
        {(["profile", "specials"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-xl px-5 py-2 text-xs font-medium capitalize transition-colors ${tab === t
              ? "bg-white text-ink shadow-sm"
              : "text-muted-foreground hover:text-ink"
              }`}
          >
            {t === "profile" ? "Store profile" : "Today's special"}
          </button>
        ))}
      </div>

      {tab === "profile" ? <MerchantStorePage /> : <MerchantSpecialsPage />}
    </div>
  );
}