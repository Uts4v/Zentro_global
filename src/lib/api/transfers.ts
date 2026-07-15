import { apiUrl, djangoFetch } from "@/lib/django-api-base";
import { djangoHeaders as authHeaders } from "@/lib/auth";
import type { PointTransaction, TransferResponse } from "./types";

export const transferApi = {
  create: async (payload: {
    receiver_transfer_code: string;
    merchant_id: number;
    amount: number;
    description?: string;
  }): Promise<TransferResponse> => {
    return djangoFetch<TransferResponse>(apiUrl("/loyalty/transfers/create/"), {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify(payload),
    });
  },

  customerList: async (merchantId?: string): Promise<PointTransaction[]> => {
    const qs = merchantId ? `?merchant=${merchantId}` : "";
    return djangoFetch<PointTransaction[]>(apiUrl(`/loyalty/transfers/${qs}`), {
      headers: authHeaders(),
    });
  },

  merchantList: async (): Promise<PointTransaction[]> => {
    return djangoFetch<PointTransaction[]>(apiUrl("/loyalty/merchant/transfers/"), {
      headers: authHeaders(),
    });
  },
};
