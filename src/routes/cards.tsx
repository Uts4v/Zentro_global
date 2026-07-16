import { useState, useCallback } from "react";
import { createFileRoute, Outlet, useMatches, useNavigate } from "@tanstack/react-router";
import { requireAuth } from "@/lib/auth-guard";
import { MobileShell, TopBar } from "@/components/MobileShell";
import { MembershipCardStack } from "@/features/cards/components/MembershipCardStack";
import { QRScanner } from "@/features/transfers/components/QRScanner";
import { Scan, Download, X, Bell, Check } from "lucide-react";

const APP_STORE_URL = import.meta.env.VITE_APP_STORE_URL as string;
const PLAY_STORE_URL = import.meta.env.VITE_PLAY_STORE_URL as string;

function getPlatform(): "ios" | "android" | "desktop" {
  const ua = navigator.userAgent;
  if (/iPad|iPhone|iPod/.test(ua)) return "ios";
  if (/android/i.test(ua)) return "android";
  return "desktop";
}

export const Route = createFileRoute("/cards")({
  beforeLoad: requireAuth,
  head: () => ({ meta: [{ title: "My Cards · Zentro" }] }),
  component: CardsPage,
});

function NotificationPrompt({ onClose }: { onClose: () => void }) {
  const [status, setStatus] = useState<"idle" | "granted" | "denied" | "unavailable">("idle");

  const handleEnable = useCallback(async () => {
    if (!("Notification" in window)) {
      setStatus("unavailable");
      return;
    }
    if (Notification.permission === "granted") {
      setStatus("granted");
      return;
    }
    if (Notification.permission === "denied") {
      setStatus("denied");
      return;
    }
    const result = await Notification.requestPermission();
    setStatus(result === "granted" ? "granted" : result === "denied" ? "denied" : "unavailable");
  }, []);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 px-6 backdrop-blur-sm">
      <div className="glass-strong relative w-full max-w-sm rounded-3xl p-6 text-center">
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 grid h-8 w-8 place-items-center rounded-full bg-muted text-muted-foreground hover:bg-muted/70"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-ember-soft">
          <Bell className="h-6 w-6 text-ember" />
        </div>

        <h3 className="mt-4 font-display text-xl text-foreground">Stay Updated</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Get notified about points earned, rewards unlocked, and exclusive offers from your favourite stores.
        </p>

        {status === "granted" ? (
          <div className="mt-5 flex flex-col items-center gap-2">
            <div className="grid h-10 w-10 place-items-center rounded-full bg-emerald-100 dark:bg-emerald-900/40">
              <Check className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">Notifications enabled!</p>
          </div>
        ) : status === "denied" ? (
          <div className="mt-5 space-y-3">
            <p className="text-xs text-muted-foreground">
              Notifications are blocked. Enable them in your browser settings to receive updates.
            </p>
            <button
              onClick={onClose}
              className="inline-flex h-11 items-center justify-center rounded-full bg-ink px-6 text-sm font-medium text-primary-foreground"
            >
              Got it
            </button>
          </div>
        ) : status === "unavailable" ? (
          <div className="mt-5 space-y-3">
            <p className="text-xs text-muted-foreground">
              Notifications are not supported in this browser. Download the app for the best experience.
            </p>
            <button
              onClick={onClose}
              className="inline-flex h-11 items-center justify-center rounded-full bg-ink px-6 text-sm font-medium text-primary-foreground"
            >
              Got it
            </button>
          </div>
        ) : (
          <div className="mt-5 flex flex-col gap-3">
            <button
              onClick={handleEnable}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-ink px-6 text-sm font-medium text-primary-foreground shadow-ember transition-all active:scale-[0.98]"
            >
              <Bell className="h-4 w-4" />
              Enable Notifications
            </button>
            <button
              onClick={onClose}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Maybe later
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function CardsPage() {
  const matches = useMatches();
  const isIndex = matches[matches.length - 1]?.routeId === "/cards";
  const navigate = useNavigate();
  const [scannerOpen, setScannerOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);

  const handleDownload = useCallback(() => {
    const platform = getPlatform();
    if (platform === "ios") {
      window.open(APP_STORE_URL, "_blank", "noopener,noreferrer");
    } else if (platform === "android") {
      window.open(PLAY_STORE_URL, "_blank", "noopener,noreferrer");
    } else {
      window.open(PLAY_STORE_URL, "_blank", "noopener,noreferrer");
    }
    setTimeout(() => setNotifOpen(true), 1500);
  }, []);

  return (
    <MobileShell>
      <TopBar
        right={
          <>
            <button
              onClick={handleDownload}
              aria-label="Download app"
              className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full border border-border text-muted-foreground hover:bg-muted transition-colors"
            >
              <Download className="h-4 w-4" />
            </button>
            <button
              onClick={() => setScannerOpen(true)}
              aria-label="Scan QR"
              className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full border border-border text-muted-foreground hover:bg-muted transition-colors"
            >
              <Scan className="h-4 w-4" />
            </button>
          </>
        }
      />
      <div className="h-dvh overflow-hidden overscroll-none px-5 pb-10 pt-2">
        {isIndex ? (
          <MembershipCardStack />
        ) : (
          <Outlet />
        )}
      </div>

      {scannerOpen && (
        <QRScanner
          onScan={(code) => {
            setScannerOpen(false);
            navigate({ to: "/transfers", search: { code } });
          }}
          onClose={() => setScannerOpen(false)}
        />
      )}

      {notifOpen && <NotificationPrompt onClose={() => setNotifOpen(false)} />}
    </MobileShell>
  );
}
