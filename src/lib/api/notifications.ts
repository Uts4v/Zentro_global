import { apiUrl, djangoFetch } from "@/lib/django-api-base";
import { djangoHeaders as authHeaders } from "@/lib/auth";
import type { Notification } from "./types";

export const notificationApi = {
  list: async (): Promise<Notification[]> => {
    return djangoFetch<Notification[]>(apiUrl("/notifications/"), {
      headers: authHeaders(),
    });
  },

  markRead: async (id: string): Promise<void> => {
    await djangoFetch(apiUrl(`/notifications/${id}/read/`), {
      method: "PATCH",
      headers: authHeaders(),
    });
  },

  markAllRead: async (): Promise<void> => {
    await djangoFetch(apiUrl("/notifications/read-all/"), {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify({}),
    });
  },

  clearAll: async (): Promise<void> => {
    await djangoFetch(apiUrl("/notifications/clear/"), {
      method: "DELETE",
      headers: authHeaders(),
    });
  },

  unreadCount: async (): Promise<{ unread_count: number }> => {
    return djangoFetch<{ unread_count: number }>(apiUrl("/notifications/unread-count/"), {
      headers: authHeaders(),
    });
  },
};
