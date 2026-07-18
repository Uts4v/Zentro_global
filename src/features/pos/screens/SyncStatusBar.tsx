import { useSyncStatus, useOnlineStatus } from "../offline/hooks";
import { processSyncQueue } from "../offline/sync";
import { Wifi, WifiOff, RefreshCw, AlertCircle, Loader2 } from "lucide-react";
import { useState } from "react";

export default function SyncStatusBar() {
  const isOnline = useOnlineStatus();
  const { pending, failed, isSyncing, refresh } = useSyncStatus();
  const [syncing, setSyncing] = useState(false);

  const hasIssues = pending > 0 || failed > 0;

  async function handleSync() {
    setSyncing(true);
    await processSyncQueue();
    refresh();
    setSyncing(false);
  }

  // Don't show if everything is clean and online
  if (!hasIssues && isOnline) return null;

  return (
    <div
      className={`flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium ${
        !isOnline
          ? "bg-amber-50 text-amber-700"
          : failed > 0
          ? "bg-red-50 text-red-700"
          : "bg-blue-50 text-blue-700"
      }`}
    >
      {!isOnline ? (
        <>
          <WifiOff className="h-3.5 w-3.5" />
          <span>Offline — {pending} mutation(s) queued</span>
        </>
      ) : isSyncing || syncing ? (
        <>
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>Syncing...</span>
        </>
      ) : failed > 0 ? (
        <>
          <AlertCircle className="h-3.5 w-3.5" />
          <span>
            {failed} failed, {pending} pending
          </span>
          <button
            onClick={handleSync}
            className="ml-auto rounded-lg bg-red-100 px-2 py-0.5 text-[10px] font-bold hover:bg-red-200"
          >
            Retry
          </button>
        </>
      ) : (
        <>
          <Wifi className="h-3.5 w-3.5" />
          <span>{pending} pending sync</span>
          <button
            onClick={handleSync}
            className="ml-auto rounded-lg bg-blue-100 px-2 py-0.5 text-[10px] font-bold hover:bg-blue-200"
          >
            Sync now
          </button>
        </>
      )}
    </div>
  );
}
