// src/lib/django-api-base.ts
// Shared helpers for talking to the Django loyalty backend.

export const DJANGO_BASE =
  (import.meta.env.VITE_DJANGO_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000/api";

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${DJANGO_BASE}${p}`;
}

export const tokenStore = {
  getAccess: (): string | null => localStorage.getItem("dja"),
  getRefresh: (): string | null => localStorage.getItem("djr"),
  set: (access: string, refresh: string) => {
    localStorage.setItem("dja", access);
    localStorage.setItem("djr", refresh);
  },
  clear: () => {
    localStorage.removeItem("dja");
    localStorage.removeItem("djr");
  },
};

export async function djangoFetch<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(url, options);
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let errMsg = (data as any)?.error || (data as any)?.detail;
    if (!errMsg && data && typeof data === "object") {
      // Handle DRF serializer field errors
      const messages = Object.entries(data)
        .filter(([k]) => k !== "error" && k !== "detail")
        .map(([field, errors]) => {
          const msgs = Array.isArray(errors) ? errors.join(", ") : String(errors);
          // Capitalize field name and remove underscores for better display
          const displayField = field.charAt(0).toUpperCase() + field.slice(1).replace(/_/g, " ");
          return `${displayField}: ${msgs}`;
        });
      if (messages.length > 0) {
        errMsg = messages.join(" | ");
      }
    }
    throw new Error(errMsg || `Request failed: ${res.status}`);
  }
  return data as T;
}