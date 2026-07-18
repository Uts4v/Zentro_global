import { createFileRoute } from "@tanstack/react-router";
import AccountList from "@/features/pos/screens/AccountList";
import DebitTopupModal from "@/features/pos/screens/DebitTopupModal";
import CreditSaleModal from "@/features/pos/screens/CreditSaleModal";
import CreditRepaymentModal from "@/features/pos/screens/CreditRepaymentModal";
import CreateDebitAccountModal from "@/features/pos/screens/CreateDebitAccountModal";
import CreateCreditAccountModal from "@/features/pos/screens/CreateCreditAccountModal";
import { DebitAccount, CreditAccount } from "@/features/pos/api";
import { useState } from "react";

function AccountsPage() {
  const [topupAccount, setTopupAccount] = useState<DebitAccount | null>(null);
  const [creditSaleAccount, setCreditSaleAccount] = useState<CreditAccount | null>(null);
  const [creditRepayAccount, setCreditRepayAccount] = useState<CreditAccount | null>(null);
  const [creditSaleOrderId, setCreditSaleOrderId] = useState("");
  const [showCreateDebit, setShowCreateDebit] = useState(false);
  const [showCreateCredit, setShowCreateCredit] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleCreated = () => setRefreshKey((k) => k + 1);

  return (
    <>
      <AccountList
        key={refreshKey}
        onTopup={(a) => setTopupAccount(a)}
        onCreditSale={(a) => {
          const orderId = prompt("Enter Order ID for this credit sale:");
          if (orderId) {
            setCreditSaleOrderId(orderId);
            setCreditSaleAccount(a);
          }
        }}
        onCreditRepayment={(a) => setCreditRepayAccount(a)}
        onCreateDebit={() => setShowCreateDebit(true)}
        onCreateCredit={() => setShowCreateCredit(true)}
      />
      {topupAccount && (
        <DebitTopupModal
          open={!!topupAccount}
          account={topupAccount}
          onDone={() => setTopupAccount(null)}
          onClose={() => setTopupAccount(null)}
        />
      )}
      {creditSaleAccount && (
        <CreditSaleModal
          open={!!creditSaleAccount}
          account={creditSaleAccount}
          orderId={creditSaleOrderId}
          onDone={() => {
            setCreditSaleAccount(null);
            setCreditSaleOrderId("");
          }}
          onClose={() => {
            setCreditSaleAccount(null);
            setCreditSaleOrderId("");
          }}
        />
      )}
      {creditRepayAccount && (
        <CreditRepaymentModal
          open={!!creditRepayAccount}
          account={creditRepayAccount}
          onDone={() => setCreditRepayAccount(null)}
          onClose={() => setCreditRepayAccount(null)}
        />
      )}
      {showCreateDebit && (
        <CreateDebitAccountModal
          open={showCreateDebit}
          onDone={handleCreated}
          onClose={() => setShowCreateDebit(false)}
        />
      )}
      {showCreateCredit && (
        <CreateCreditAccountModal
          open={showCreateCredit}
          onDone={handleCreated}
          onClose={() => setShowCreateCredit(false)}
        />
      )}
    </>
  );
}

export const Route = createFileRoute("/pos/accounts")({
  component: AccountsPage,
});
