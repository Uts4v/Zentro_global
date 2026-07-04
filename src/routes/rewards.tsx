import { createFileRoute } from "@tanstack/react-router";
import { requireAuth } from "@/lib/auth-guard";
import { RewardsPage } from "@/features/loyalty-engine/pages/RewardsPage";

export const Route = createFileRoute("/rewards")({
  beforeLoad: requireAuth,
  head: () => ({ meta: [{ title: "Rewards · Zentro" }] }),
  component: RewardsPage,
});