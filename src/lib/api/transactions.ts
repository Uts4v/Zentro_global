import { apiUrl, djangoFetch } from "@/lib/django-api-base";
import { djangoHeaders as authHeaders } from "@/lib/auth";
import type { PointTransaction } from "./types";

export const transactionApi = {
  customerList: async (merchantId: string): Promise<PointTransaction[]> => {
    return djangoFetch<PointTransaction[]>(
      apiUrl(`/loyalty/transactions/?merchant=${merchantId}`),
      {
        headers: authHeaders(),
      },
    );
  },

  merchantList: async (): Promise<PointTransaction[]> => {
    return djangoFetch<PointTransaction[]>(apiUrl("/loyalty/merchant/transactions/"), {
      headers: authHeaders(),
    });
  },
};
