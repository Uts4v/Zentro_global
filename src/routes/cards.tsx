import { createFileRoute, Outlet, useMatches } from "@tanstack/react-router";
import { requireAuth } from "@/lib/auth-guard";
import { MobileShell, TopBar } from "@/components/MobileShell";
import { MembershipCardStack } from "@/features/cards/components/MembershipCardStack";

export const Route = createFileRoute("/cards")({
  beforeLoad: requireAuth,
  head: () => ({ meta: [{ title: "My Cards · Zentro" }] }),
  component: CardsPage,
});

function CardsPage() {
  const matches = useMatches();
  const isIndex = matches[matches.length - 1]?.routeId === "/cards";

  return (
    <MobileShell>
      <TopBar />
      <div className="px-5 pb-10 pt-2">
        {isIndex ? <MembershipCardStack /> : <Outlet />}
      </div>
    </MobileShell>
  );
}