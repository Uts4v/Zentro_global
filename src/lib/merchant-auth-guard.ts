/**
 * src/lib/merchant-auth-guard.ts
 *
 * Guards merchant-only routes. Checks both token presence and the `role`
 * claim embedded in the JWT payload.
 */

import { redirect } from "@tanstack/react-router";
import { tokenStore } from "@/lib/django-api-base";

function getTokenPayload(): Record<string, any> | null {
  if (typeof window === "undefined") return null;
  const access = tokenStore.getAccess();
  if (!access) return null;
  try {
    const payload = JSON.parse(atob(access.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (payload.exp < Math.floor(Date.now() / 1000)) return null; // expired
    return payload;
  } catch {
    return null;
  }
}

export async function requireMerchant() {
  if (typeof window === "undefined") return;

  const redirectPath = window.location.pathname;
  const payload = getTokenPayload();

  if (!payload) {
    throw redirect({ to: "/auth/merchant", search: { redirect: redirectPath } });
  }

  if (payload.role !== "merchant") {
    throw redirect({ to: "/auth/merchant", search: { redirect: redirectPath } });
  }
}
