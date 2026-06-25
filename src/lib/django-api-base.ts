// src/lib/django-api.ts
// Shared helpers for talking to the Django loyalty backend.
import { supabase } from "@/lib/supabase";

// VITE_DJANGO_API_BASE_URL in .env is already: http://127.0.0.1:8080/api/loyalty
// So loyaltyUrl() must NOT append /loyalty again — just append the path directly.
const RAW_BASE =
  (import.meta.env.VITE_DJANGO_API_BASE_URL as string | undefined) ||
  "http://127.0.0.1:8080/api/loyalty";

// Strip any trailing slash so path joins are always clean.
export const DJANGO_LOYALTY_BASE = RAW_BASE.replace(/\/$/, "");

// Also expose a base without /loyalty for non-loyalty endpoints (e.g. /accounts/me/)
// e.g. "http://127.0.0.1:8080/api/loyalty" → "http://127.0.0.1:8080/api"
export const DJANGO_API_BASE = DJANGO_LOYALTY_BASE.replace(/\/loyalty$/, "");

/**
 * Build a URL under the loyalty API root.
 * loyaltyUrl("/missions/") → "http://127.0.0.1:8080/api/loyalty/missions/"
 */
export function loyaltyUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${DJANGO_LOYALTY_BASE}${p}`;
}

/**
 * Build a URL under the Django API root (non-loyalty endpoints).
 * apiUrl("/accounts/me/") → "http://127.0.0.1:8080/api/accounts/me/"
 */
export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${DJANGO_API_BASE}${p}`;
}

/**
 * Returns fetch headers with the Supabase JWT attached.
 * Pass json=true to also set Content-Type: application/json.
 */
export async function djangoHeaders(json = false): Promise<HeadersInit> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token;
  if (!token) throw new Error("Not authenticated — please log in again.");
  const h: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (json) h["Content-Type"] = "application/json";
  return h;
}

/**
 * Typed fetch wrapper. Throws on non-2xx with the Django error message.
 * Returns undefined for 204 No Content.
 */
export async function djangoFetch<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(url, options);
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      (data as any)?.error ||
        (data as any)?.detail ||
        `Request failed: ${res.status}`
    );
  }
  return data as T;
}