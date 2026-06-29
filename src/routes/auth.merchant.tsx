// routes/auth.merchant.tsx — Merchant sign-in / sign-up (Django JWT)
import { createFileRoute, Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Loader2, Mail, Lock, User, Store, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/auth/merchant")({
  validateSearch: (search: Record<string, unknown>) => ({
    redirect: (search.redirect as string) || undefined,
  }),
  head: () => ({ meta: [{ title: "Merchant Sign In · Zentro" }] }),
  component: MerchantAuth,
});

function MerchantAuth() {
  const [mode, setMode]           = useState<"signin" | "signup">("signin");
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [name, setName]           = useState("");
  const [storeName, setStoreName] = useState("");
  const [error, setError]         = useState<string | null>(null);
  const [success, setSuccess]     = useState<string | null>(null);
  const [busy, setBusy]           = useState(false);
  const { signIn, signUp, user }  = useAuth();
  const navigate                  = useNavigate();
  const { redirect }              = useSearch({ from: "/auth/merchant" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setBusy(true);

    try {
      if (mode === "signup") {
        if (!storeName.trim()) { setError("Store name is required."); return; }
        const { error: err } = await signUp(email, password, name, {
          role: "merchant",
          store_name: storeName,
        });
        if (err) { setError(err); return; }
        // Auto-logged in after signup — navigate to dashboard
        navigate({ to: (redirect || "/merchant") as any, replace: true });
        return;
      }

      // Sign in
      const { error: err } = await signIn(email, password);
      if (err) { setError(err); return; }

      // After signIn, useAuth() updates `user`. Verify merchant role.
      // We read from the JWT payload stored in tokenStore.
      const access = localStorage.getItem("zentro_access");
      if (access) {
        try {
          const payload = JSON.parse(atob(access.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
          if (payload.role !== "merchant") {
            setError("This account is not a merchant account. Use customer sign in instead.");
            signOut();
            return;
          }
        } catch { /* ignore decode errors */ }
      }

      navigate({ to: (redirect || "/merchant") as any, replace: true });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-dvh max-w-[480px] flex-col px-5 pb-10 pt-10">
      <Link to="/" className="font-display text-2xl text-ink">
        zentro<span className="text-ember">.</span>
        <span className="ml-2 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">for business</span>
      </Link>

      <div className="mt-12">
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          {mode === "signin" ? "Welcome back" : "Grow with Zentro"}
        </p>
        <h1 className="font-display mt-2 text-5xl leading-[1.05] text-ink">
          {mode === "signin" ? "Manage your\nstore." : "Register your\nbusiness."}
        </h1>
        <p className="mt-3 max-w-[300px] text-sm text-muted-foreground">
          {mode === "signin"
            ? "Orders, loyalty, and analytics — all in one place."
            : "Reach thousands of loyal customers on Zentro."}
        </p>
      </div>

      {error && (
        <div className="mt-6 rounded-2xl bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
      )}
      {success && (
        <div className="mt-6 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>
      )}

      <form onSubmit={handleSubmit} className="mt-10 space-y-3">
        {mode === "signup" && (
          <>
            <Field label="Your name" placeholder="Maya Rivera" icon={<User className="h-4 w-4" />} value={name} onChange={setName} />
            <Field label="Store name" placeholder="Maison Aria" icon={<Store className="h-4 w-4" />} value={storeName} onChange={setStoreName} />
          </>
        )}
        <Field label="Business email" placeholder="hello@maison.com" type="email" icon={<Mail className="h-4 w-4" />} value={email} onChange={setEmail} />
        <Field label="Password" placeholder="••••••••" type="password" icon={<Lock className="h-4 w-4" />} value={password} onChange={setPassword} />

        <button
          type="submit" disabled={busy}
          className="mt-6 grid h-14 w-full place-items-center rounded-2xl bg-ink text-sm font-medium text-primary-foreground shadow-ember transition-all hover:opacity-90 disabled:opacity-50"
        >
          {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : (
            <span className="flex items-center gap-2">
              {mode === "signin" ? "Sign in" : "Register business"} <ArrowRight className="h-4 w-4" />
            </span>
          )}
        </button>
      </form>

      <p className="mt-auto pt-8 text-center text-xs text-muted-foreground">
        {mode === "signin" ? "New to Zentro?" : "Already have a business account?"}{" "}
        <button
          type="button"
          onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(null); setSuccess(null); }}
          className="font-medium text-ink underline-offset-4 hover:underline"
        >
          {mode === "signin" ? "Register your business" : "Sign in"}
        </button>
      </p>

      <Link to="/auth" className="mt-3 block text-center text-xs text-muted-foreground hover:text-ink hover:underline">
        Customer sign in →
      </Link>
    </div>
  );
}

function Field({ label, placeholder, type = "text", icon, value, onChange }: {
  label: string; placeholder: string; type?: string;
  icon?: React.ReactNode; value: string; onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
      <div className="relative mt-1.5">
        {icon && <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">{icon}</span>}
        <input
          type={type} placeholder={placeholder} value={value}
          onChange={(e) => onChange(e.target.value)} required
          className={`h-14 w-full rounded-2xl bg-mist text-sm text-ink outline-none transition-all placeholder:text-muted-foreground/60 focus:ring-2 focus:ring-ember/40 ${icon ? "pl-11" : "px-4"} pr-4`}
        />
      </div>
    </label>
  );
}
