import { apiUrl, djangoFetch } from "@/lib/django-api-base";
import { djangoHeaders as authHeaders } from "@/lib/auth";

export const analyticsApi = {
  merchant: async (days = 30) => {
    return djangoFetch<any>(apiUrl(`/merchants/analytics/?days=${days}`), {
      headers: authHeaders(),
    });
  },
};
