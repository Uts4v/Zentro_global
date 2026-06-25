import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { Loader2, Lock, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/auth/reset-password")({
  head: () => ({ meta: [{ title: "Set New Password · Zentro" }] }),
  component: ResetPassword,
});

function ResetPassword() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const [tokenReady, setTokenReady] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const navigate = useNavigate();

  // FIX: Supabase sends the reset token as a URL hash fragment like:
  // /auth/reset-password#access_token=xxx&type=recovery
  // We must let Supabase process this hash and establish a session
  // before we can call updateUser.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const hash = window.location.hash;

    // If there's no hash at all, the user navigated here directly
    if (!hash || !hash.includes("access_token")) {
      setTokenError("Invalid or expired reset link. Please request a new one.");
      return;
    }

    // Parse the hash manually to get the token type
    const params = new URLSearchParams(hash.substring(1));
    const type = params.get("type");
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");

    if (type !== "recovery" || !accessToken) {
      setTokenError("Invalid reset link. Please request a new one.");
      return;
    }

    // Set the session from the hash tokens so updateUser works
    supabase.auth
      .setSession({ access_token: accessToken, refresh_token: refreshToken ?? "" })
      .then(({ error: sessionErr }) => {
        if (sessionErr) {
          setTokenError("Reset link has expired. Please request a new one.");
        } else {
          setTokenReady(true);
          // Clean the hash from the URL without triggering a reload
          window.history.replaceState(null, "", window.location.pathname);
        }
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setBusy(true);
    try {
      const { error: err } = await supabase.auth.updateUser({ password });
      if (err) {
        setError(err.message);
      } else {
        setSuccess(true);
        // Sign out so user has to sign in fresh with new password
        await supabase.auth.signOut();
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-dvh max-w-[480px] flex-col px-5 pb-10 pt-10">
      <Link to="/" className="font-display text-2xl text-ink">
        zentro<span className="text-ember">.</span>
      </Link>

      <div className="mt-12">
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          New password
        </p>
        <h1 className="font-display mt-2 text-5xl leading-[1.05] text-ink">
          Set your new
          <br />password.
        </h1>
      </div>

      {/* Token error — link is invalid or expired */}
      {tokenError && (
        <div className="mt-10 rounded-2xl bg-rose-50 px-5 py-6 text-center">
          <p className="text-sm font-medium text-rose-700">Link expired</p>
          <p className="mt-1 text-xs text-rose-600">{tokenError}</p>
          <Link
            to="/auth/forgot-password"
            className="mt-4 inline-flex h-10 items-center justify-center rounded-full bg-ink px-5 text-xs font-medium text-primary-foreground"
          >
            Request new link
          </Link>
        </div>
      )}

      {/* Waiting for token to be processed */}
      {!tokenError && !tokenReady && (
        <div className="mt-16 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {error && tokenReady && (
        <div className="mt-6 rounded-2xl bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {success ? (
        <div className="mt-10 rounded-2xl bg-emerald-50 px-5 py-6 text-center">
          <p className="text-sm font-medium text-emerald-700">Password updated!</p>
          <p className="mt-1 text-xs text-emerald-600">
            You can now sign in with your new password.
          </p>
          <Link
            to="/auth"
            className="mt-4 inline-flex h-10 items-center justify-center rounded-full bg-ink px-5 text-xs font-medium text-primary-foreground"
          >
            Sign in
          </Link>
        </div>
      ) : tokenReady ? (
        <form onSubmit={handleSubmit} className="mt-10 space-y-3">
          <label className="block">
            <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              New password
            </span>
            <div className="relative mt-1.5">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                <Lock className="h-4 w-4" />
              </span>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-14 w-full rounded-2xl bg-mist pl-11 pr-4 text-sm text-ink outline-none transition-all placeholder:text-muted-foreground/60 focus:ring-2 focus:ring-ember/40"
              />
            </div>
          </label>

          <label className="block">
            <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Confirm password
            </span>
            <div className="relative mt-1.5">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                <Lock className="h-4 w-4" />
              </span>
              <input
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="h-14 w-full rounded-2xl bg-mist pl-11 pr-4 text-sm text-ink outline-none transition-all placeholder:text-muted-foreground/60 focus:ring-2 focus:ring-ember/40"
              />
            </div>
          </label>

          <button
            type="submit"
            disabled={busy}
            className="mt-6 grid h-14 w-full place-items-center rounded-2xl bg-ink text-sm font-medium text-primary-foreground shadow-ember transition-all hover:opacity-90 disabled:opacity-50"
          >
            {busy ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <span className="flex items-center gap-2">
                Update password <ArrowRight className="h-4 w-4" />
              </span>
            )}
          </button>
        </form>
      ) : null}
    </div>
  );
}