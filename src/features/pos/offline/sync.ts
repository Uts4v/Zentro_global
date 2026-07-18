/**
 * Background sync engine for POS offline mutations.
 * Processes the sync queue when online, with retry logic.
 */

import { djangoFetch, apiUrl, tokenStore } from "@/lib/django-api-base";
import { syncQueue, offlineOrders, offlinePayments, SyncQueueItem } from "./db";

const MAX_RETRIES = 5;
const RETRY_DELAY_MS = 2000;

let isSyncing = false;
let syncInterval: ReturnType<typeof setInterval> | null = null;

function headers() {
  return {
    Authorization: `Bearer ${tokenStore.getAccess()}`,
    "Content-Type": "application/json",
  };
}

// ── Enqueue a mutation for offline sync ─────────────────────────────────────

export async function enqueueMutation(
  type: SyncQueueItem["type"],
  endpoint: string,
  method: SyncQueueItem["method"],
  body: Record<string, any>,
  clientMutationId: string
): Promise<void> {
  const item: SyncQueueItem = {
    id: clientMutationId,
    type,
    endpoint,
    method,
    body,
    client_mutation_id: clientMutationId,
    status: "pending",
    attempts: 0,
    created_at: new Date().toISOString(),
  };

  await syncQueue.add(item);
}

// ── Process a single queue item ─────────────────────────────────────────────

async function processItem(item: SyncQueueItem): Promise<boolean> {
  try {
    await syncQueue.markSyncing(item.id);

    const response = await djangoFetch<any>(apiUrl(item.endpoint), {
      method: item.method,
      headers: headers(),
      body: JSON.stringify(item.body),
    });

    // Success — remove from queue
    await syncQueue.remove(item.id);

    // Handle special post-sync actions
    if (item.type === "order" && response?.id) {
      await offlineOrders.markSynced(item.client_mutation_id, response.id);
    }
    if (item.type === "payment" && response?.id) {
      await offlinePayments.markSynced(item.client_mutation_id, response.id);
    }

    return true;
  } catch (error: any) {
    if (item.attempts >= MAX_RETRIES) {
      await syncQueue.markFailed(item.id, error?.message || "Max retries exceeded");
    } else {
      await syncQueue.markFailed(item.id, error?.message || "Sync failed");
    }
    return false;
  }
}

// ── Process entire queue ────────────────────────────────────────────────────

export async function processSyncQueue(): Promise<{
  synced: number;
  failed: number;
  pending: number;
}> {
  if (isSyncing) return { synced: 0, failed: 0, pending: 0 };
  if (!navigator.onLine) return { synced: 0, failed: 0, pending: 0 };

  isSyncing = true;
  let synced = 0;
  let failed = 0;

  try {
    const pending = await syncQueue.getPending();

    // Sort by created_at to process in order
    pending.sort((a, b) => a.created_at.localeCompare(b.created_at));

    for (const item of pending) {
      if (!navigator.onLine) break; // Stop if we go offline mid-sync

      const success = await processItem(item);
      if (success) synced++;
      else failed++;

      // Small delay between requests to avoid overwhelming the server
      await new Promise((r) => setTimeout(r, 100));
    }

    const remaining = await syncQueue.getPending();
    return { synced, failed, pending: remaining.length };
  } finally {
    isSyncing = false;
  }
}

// ── Auto-sync on reconnect ──────────────────────────────────────────────────

function handleOnline() {
  console.log("[POS Sync] Back online — processing queue...");
  processSyncQueue();
}

function handleOffline() {
  console.log("[POS Sync] Gone offline — mutations will be queued");
}

// ── Start/stop background sync ──────────────────────────────────────────────

export function startBackgroundSync(intervalMs = 30000) {
  if (syncInterval) return; // Already running

  window.addEventListener("online", handleOnline);
  window.addEventListener("offline", handleOffline);

  // Process immediately if online
  if (navigator.onLine) {
    processSyncQueue();
  }

  // Then process periodically
  syncInterval = setInterval(() => {
    if (navigator.onLine) {
      processSyncQueue();
    }
  }, intervalMs);

  console.log(`[POS Sync] Background sync started (every ${intervalMs / 1000}s)`);
}

export function stopBackgroundSync() {
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
  }
  window.removeEventListener("online", handleOnline);
  window.removeEventListener("offline", handleOffline);
  console.log("[POS Sync] Background sync stopped");
}

// ── Sync status query ───────────────────────────────────────────────────────

export async function getSyncStatus(): Promise<{
  pending: number;
  failed: number;
  isSyncing: boolean;
}> {
  const pending = await syncQueue.getPending();
  return {
    pending: pending.filter((i) => i.status === "pending").length,
    failed: pending.filter((i) => i.status === "failed").length,
    isSyncing,
  };
}

// ── Retry a specific failed item ────────────────────────────────────────────

export async function retryItem(id: string): Promise<boolean> {
  const item = await syncQueue.get(id);
  if (!item || item.status !== "failed") return false;
  item.status = "pending";
  item.attempts = 0;
  await syncQueue.add(item);
  return processSyncQueue().then(() => true);
}
