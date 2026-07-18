import { useState, useEffect, useCallback } from "react";
import {
  startBackgroundSync,
  stopBackgroundSync,
  processSyncQueue,
  getSyncStatus,
} from "./sync";

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  return isOnline;
}

export function useSyncStatus() {
  const [status, setStatus] = useState({
    pending: 0,
    failed: 0,
    isSyncing: false,
  });
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    getSyncStatus().then(setStatus);
  }, [refreshKey]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      getSyncStatus().then(setStatus);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return { ...status, refresh };
}

export function useBackgroundSync() {
  useEffect(() => {
    startBackgroundSync(30000);
    return () => stopBackgroundSync();
  }, []);

  const syncNow = useCallback(() => {
    return processSyncQueue();
  }, []);

  return { syncNow };
}
