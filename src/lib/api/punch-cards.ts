import { apiUrl, djangoFetch } from "@/lib/django-api-base";
import { djangoHeaders as authHeaders } from "@/lib/auth";
import type { MerchantPunchCard, CustomerPunchCard } from "./types";

export const punchCardApi = {
  generateProof: async (
    id: string,
  ): Promise<{
    proof_code: string;
    expires_at: string;
    reward_text: string;
    store_name: string;
    customer_name: string;
  }> => {
    return djangoFetch(apiUrl(`/loyalty/punch-cards/${id}/generate-proof/`), {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify({}),
    });
  },

  confirmProof: async (
    proofCode: string,
  ): Promise<{
    success: boolean;
    customer_name: string;
    reward_text: string;
    order_id: string;
    new_card_started: boolean;
  }> => {
    return djangoFetch(apiUrl("/loyalty/punch-cards/confirm-proof/"), {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify({ proof_code: proofCode }),
    });
  },

  merchantList: async (): Promise<MerchantPunchCard[]> => {
    return djangoFetch<MerchantPunchCard[]>(apiUrl("/loyalty/merchant/punch-cards/"), {
      headers: authHeaders(),
    });
  },

  merchantCreate: async (data: Partial<MerchantPunchCard>): Promise<MerchantPunchCard> => {
    return djangoFetch<MerchantPunchCard>(apiUrl("/loyalty/merchant/punch-cards/create/"), {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify(data),
    });
  },

  merchantUpdate: async (
    id: string,
    data: Partial<MerchantPunchCard>,
  ): Promise<MerchantPunchCard> => {
    return djangoFetch<MerchantPunchCard>(apiUrl(`/loyalty/merchant/punch-cards/${id}/`), {
      method: "PATCH",
      headers: authHeaders(true),
      body: JSON.stringify(data),
    });
  },

  customerList: async (
    merchantId: string,
  ): Promise<{ active: CustomerPunchCard[]; completed: CustomerPunchCard[] }> => {
    return djangoFetch<{ active: CustomerPunchCard[]; completed: CustomerPunchCard[] }>(
      apiUrl(`/loyalty/punch-cards/?merchant=${merchantId}`),
      {
        headers: authHeaders(),
      },
    );
  },

  customerRedeem: async (id: string): Promise<CustomerPunchCard> => {
    return djangoFetch<CustomerPunchCard>(apiUrl(`/loyalty/punch-cards/${id}/redeem/`), {
      method: "POST",
      headers: authHeaders(),
    });
  },
};
