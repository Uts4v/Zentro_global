import { apiUrl, djangoFetch } from "@/lib/django-api-base";

export const leaderboardApi = {
  get: async (merchantId?: string, limit = 10) => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (merchantId) qs.set("merchant", merchantId);
    return djangoFetch<any[]>(apiUrl(`/loyalty/leaderboard/?${qs}`));
  },
};
