import { redirect } from "@tanstack/react-router";
import { authReady } from "@/lib/supabase-auth-ready";

export async function requireAuth() {
  if (typeof window === "undefined") return;

  const session = await authReady;

  if (!session) {
    throw redirect({
      to: "/auth",
      search: { redirect: window.location.pathname },
    });
  }
}