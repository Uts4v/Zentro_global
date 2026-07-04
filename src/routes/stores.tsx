import { createFileRoute } from "@tanstack/react-router";
import { requireAuth } from "@/lib/auth-guard";
import { StoresPage } from "@/features/store-locator/pages/StoresPage";

export const Route = createFileRoute("/stores")({
  beforeLoad: requireAuth,
  head: () => ({ meta: [{ title: "Discover · Zentro" }] }),
  component: StoresPage,
});
