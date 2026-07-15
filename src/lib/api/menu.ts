import { apiUrl, djangoFetch } from "@/lib/django-api-base";
import { djangoHeaders as authHeaders } from "@/lib/auth";
import type { MenuItem, MenuItemInput } from "./types";

export const menuApi = {
  myItems: async (): Promise<MenuItem[]> => {
    return djangoFetch<MenuItem[]>(apiUrl("/merchants/menu-items/"), {
      headers: authHeaders(),
    });
  },

  create: async (input: Partial<MenuItemInput>): Promise<MenuItem> => {
    return djangoFetch<MenuItem>(apiUrl("/merchants/menu-items/"), {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify(input),
    });
  },

  update: async (id: string, input: Partial<MenuItemInput>): Promise<MenuItem> => {
    return djangoFetch<MenuItem>(apiUrl(`/merchants/menu-items/${id}/`), {
      method: "PATCH",
      headers: authHeaders(true),
      body: JSON.stringify(input),
    });
  },

  delete: async (id: string): Promise<void> => {
    return djangoFetch<void>(apiUrl(`/merchants/menu-items/${id}/`), {
      method: "DELETE",
      headers: authHeaders(),
    });
  },

  toggleAvailability: async (id: string): Promise<MenuItem> => {
    return djangoFetch<MenuItem>(apiUrl(`/merchants/menu-items/${id}/toggle-availability/`), {
      method: "PATCH",
      headers: authHeaders(),
    });
  },

  forMerchant: async (merchantId: string): Promise<MenuItem[]> => {
    return djangoFetch<MenuItem[]>(apiUrl(`/merchants/${merchantId}/menu/`));
  },
};
