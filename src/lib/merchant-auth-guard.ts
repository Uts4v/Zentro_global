import { redirect } from "@tanstack/react-router";
import { authReady } from "@/lib/supabase-auth-ready";

export async function requireMerchant() {
  // Skip on SSR — no session available server-side, client will re-run on hydration
  if (typeof window === "undefined") return;

  const redirectPath = window.location.pathname;
  const session = await authReady;

  if (!session) {
    throw redirect({ to: "/auth/merchant", search: { redirect: redirectPath } });
  }

  const role = session.user?.user_metadata?.role;
  if (role !== "merchant") {
    throw redirect({ to: "/auth/merchant", search: { redirect: redirectPath } });
  }
}