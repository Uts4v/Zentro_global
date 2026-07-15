import { apiUrl, djangoFetch } from "@/lib/django-api-base";
import { djangoHeaders as authHeaders } from "@/lib/auth";
import type {
  CustomerProfile,
  CustomerMerchantWallet,
  CustomerMerchantProfile,
  JoinedMerchant,
} from "./types";

export const customerApi = {
  profile: async (): Promise<CustomerProfile> => {
    const data = await djangoFetch<any>(apiUrl("/auth/me/"), {
      headers: authHeaders(),
    });
    const cp = data.customer_profile ?? {};
    return {
      id: cp.id ? String(cp.id) : String(data.id),
      full_name: cp.full_name ?? null,
      loyalty_points: cp.loyalty_points ?? 0,
      streak_days: cp.streak_days ?? 0,
      tier: cp.tier ?? "bronze",
      total_orders: cp.total_orders ?? 0,
      transfer_code: cp.transfer_code ?? undefined,
    };
  },

  getWallet: async (merchantId: string): Promise<CustomerMerchantWallet | null> => {
    try {
      const data = await djangoFetch<any>(apiUrl(`/loyalty/wallets/mine/?merchant=${merchantId}`), {
        headers: authHeaders(),
      });
      if (!data) return null;
      return {
        id: String(data.id ?? ""),
        merchant_id: String(data.merchant_id ?? merchantId),
        merchant_name: data.merchant_name ?? "",
        merchant_slug: data.merchant_slug ?? "",
        points_balance: data.points_balance ?? 0,
        lifetime_points: data.lifetime_points ?? 0,
        expired_points: data.expired_points ?? 0,
        order_count: data.order_count ?? 0,
        streak_days: data.streak_days ?? 0,
        last_order_date: data.last_order_date ?? null,
        last_point_earned_at: data.last_point_earned_at ?? null,
        tier_level: data.tier_level ?? "bronze",
        created_at: data.created_at ?? "",
        updated_at: data.updated_at ?? "",
      };
    } catch {
      return null;
    }
  },

  listWallets: async (): Promise<CustomerMerchantWallet[]> => {
    const data = await djangoFetch<any[]>(apiUrl("/loyalty/wallets/"), {
      headers: authHeaders(),
    });
    return (data ?? []).map((w) => ({
      id: String(w.id ?? ""),
      merchant_id: String(w.merchant_id ?? ""),
      merchant_name: w.merchant_name ?? "",
      merchant_slug: w.merchant_slug ?? "",
      points_balance: w.points_balance ?? 0,
      lifetime_points: w.lifetime_points ?? 0,
      expired_points: w.expired_points ?? 0,
      order_count: w.order_count ?? 0,
      streak_days: w.streak_days ?? 0,
      last_order_date: w.last_order_date ?? null,
      last_point_earned_at: w.last_point_earned_at ?? null,
      tier_level: w.tier_level ?? "bronze",
      created_at: w.created_at ?? "",
      updated_at: w.updated_at ?? "",
    }));
  },

  joinMerchant: async (
    merchantSlug: string,
  ): Promise<{
    profile: CustomerMerchantProfile;
    wallet: CustomerMerchantWallet;
    created: boolean;
  }> => {
    const data = await djangoFetch<any>(apiUrl("/loyalty/merchant-profiles/join/"), {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify({ merchant_slug: merchantSlug }),
    });
    const normProfile = (p: any): CustomerMerchantProfile => ({
      id: String(p.id ?? ""),
      merchant_id: String(p.merchant_id ?? ""),
      merchant_name: p.merchant_name ?? "",
      merchant_slug: p.merchant_slug ?? merchantSlug,
      joined_at: p.joined_at ?? "",
      status: p.status ?? "active",
      created_at: p.created_at ?? "",
      updated_at: p.updated_at ?? "",
    });
    const normWallet = (w: any): CustomerMerchantWallet => ({
      id: String(w.id ?? ""),
      merchant_id: String(w.merchant_id ?? ""),
      merchant_name: w.merchant_name ?? "",
      merchant_slug: w.merchant_slug ?? merchantSlug,
      points_balance: w.points_balance ?? 0,
      lifetime_points: w.lifetime_points ?? 0,
      expired_points: w.expired_points ?? 0,
      order_count: w.order_count ?? 0,
      streak_days: w.streak_days ?? 0,
      last_order_date: w.last_order_date ?? null,
      last_point_earned_at: w.last_point_earned_at ?? null,
      tier_level: w.tier_level ?? "bronze",
      created_at: w.created_at ?? "",
      updated_at: w.updated_at ?? "",
    });
    return {
      profile: normProfile(data.profile),
      wallet: normWallet(data.wallet),
      created: Boolean(data.created),
    };
  },

  joinedMerchants: async (): Promise<JoinedMerchant[]> => {
    return djangoFetch<JoinedMerchant[]>(apiUrl("/loyalty/merchant-profiles/joined/"), {
      headers: authHeaders(),
    });
  },
};
