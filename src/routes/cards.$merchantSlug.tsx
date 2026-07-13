import { createFileRoute } from "@tanstack/react-router";
import { requireAuth } from "@/lib/auth-guard";
import { MembershipCardDetail } from "@/features/cards/components/MembershipCardDetail";

export const Route = createFileRoute("/cards/$merchantSlug")({
  beforeLoad: requireAuth,
  head: () => ({ meta: [{ title: "Card · Zentro" }] }),
  component: CardDetailPage,
});

function CardDetailPage() {
  const { merchantSlug } = Route.useParams();
  return <MembershipCardDetail merchantSlug={merchantSlug} />;
}
