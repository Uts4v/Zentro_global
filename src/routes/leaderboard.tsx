import { createFileRoute } from "@tanstack/react-router";
import { requireAuth } from "@/lib/auth-guard";
import { LeaderboardPage } from "@/features/loyalty-engine/pages/LeaderboardPage";

export const Route = createFileRoute("/leaderboard")({
  beforeLoad: requireAuth,
  head: () => ({ meta: [{ title: "Leaderboard · Zentro" }] }),
  component: LeaderboardPage,
});
