import { useEffect, useState } from "react";
import { Loader2, ArrowUpRight, ArrowDownLeft, Inbox } from "lucide-react";
import { transferApi, type PointTransaction } from "@/lib/api";

interface TransferHistoryProps {
  merchantId?: string;
  refreshKey?: number;
}

export function TransferHistory({ merchantId, refreshKey }: TransferHistoryProps) {
  const [transactions, setTransactions] = useState<PointTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    transferApi
      .customerList(merchantId)
      .then((data) => setTransactions(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [merchantId, refreshKey]);

  if (loading) {
    return (
      <div className="flex justify-center py-10">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="glass rounded-3xl py-10 text-center">
        <div className="flex justify-center"><Inbox className="h-8 w-8 text-muted-foreground" /></div>
        <p className="mt-2 text-sm text-muted-foreground">
          No transfers yet.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {transactions.map((tx) => {
        const isSent = tx.transaction_type === "TRANSFER_SENT";
        return (
          <div
            key={tx.id}
            className="glass flex items-center gap-4 rounded-2xl px-4 py-3"
          >
            <div
              className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${
                isSent
                  ? "bg-rose-100 dark:bg-rose-950/40 text-rose-600"
                  : "bg-emerald-100 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400"
              }`}
            >
              {isSent ? (
                <ArrowUpRight className="h-4 w-4" />
              ) : (
                <ArrowDownLeft className="h-4 w-4" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-ink">
                {isSent ? "Sent" : "Received"}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {tx.description || tx.merchant_name}
              </p>
            </div>
            <div className="text-right">
              <p
                className={`text-sm font-semibold ${
                  isSent ? "text-rose-600" : "text-emerald-600 dark:text-emerald-400"
                }`}
              >
                {isSent ? "" : "+"}{tx.points}
              </p>
              <p className="text-[10px] text-muted-foreground">
                {new Date(tx.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
