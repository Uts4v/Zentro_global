// src/routes/merchant.store.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useCallback, useRef } from "react";
import {
  MapPin, Clock, Loader2, Save, Check, X,
  ImageIcon, Upload, QrCode, ExternalLink, RefreshCw, LocateFixed, Palette, CreditCard, Send,
} from "lucide-react";
import { merchantApi, type MerchantProfile, merchantCardDesignApi, type MembershipCardDesign } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { optimizeImage } from "@/lib/image-optimize";
import { uploadImage } from "@/lib/image-upload";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

export const Route = createFileRoute("/merchant/store")({
  head: () => ({ meta: [{ title: "Store · Merchant · Zentro" }] }),
  component: StoreConfig,
});

type ImgStatus =
  | { status: "idle" }
  | { status: "processing" }
  | { status: "uploading"; previewUrl: string }
  | { status: "done"; previewUrl: string }
  | { status: "error"; error: string };

// ── Inline image uploader ─────────────────────────────────────────────────────
function InlineImageUploader({
  label, hint, currentUrl, onUpload, onClear,
  aspectClass = "aspect-video", shape = "square", disabled = false,
  merchantId, bucket, storagePath, preset,
}: {
  label: string;
  hint?: string;
  currentUrl?: string | null;
  onUpload: (url: string) => void;
  onClear: () => void;
  aspectClass?: string;
  shape?: "square" | "circle";
  disabled?: boolean;
  merchantId: string;
  bucket: string;
  storagePath: string;
  preset: "logo" | "banner" | "profile" | "product";
}) {
  const [imgState, setImgState] = useState<ImgStatus>(
    currentUrl ? { status: "done", previewUrl: currentUrl } : { status: "idle" }
  );
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (currentUrl && imgState.status === "idle") {
      setImgState({ status: "done", previewUrl: currentUrl });
    }
  }, [currentUrl]);

  const imgUploading =
    imgState.status === "processing" || imgState.status === "uploading";
  const displayUrl =
    imgState.status === "uploading" || imgState.status === "done"
      ? imgState.previewUrl
      : currentUrl || null;
  const radiusCls = shape === "circle" ? "rounded-full" : "rounded-2xl";

  async function handleFile(file: File) {
    setImgState({ status: "processing" });
    let optimized;
    try {
      optimized = await optimizeImage(file, preset);
    } catch (err: any) {
      setImgState({ status: "error", error: err.message ?? "Could not process image." });
      return;
    }
    setImgState({ status: "uploading", previewUrl: optimized.previewUrl });
    try {
      const { publicUrl } = await uploadImage(file, preset, bucket, storagePath);
      setImgState({ status: "done", previewUrl: optimized.previewUrl });
      onUpload(publicUrl);
    } catch (err: any) {
      setImgState({ status: "error", error: err.message ?? "Upload failed." });
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  function handleClear() {
    setImgState({ status: "idle" });
    onClear();
  }

  return (
    <div className="space-y-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={handleInputChange}
        disabled={disabled || imgUploading}
      />
      <div
        className={`relative ${aspectClass} w-full overflow-hidden border-2 border-dashed transition-colors
          ${radiusCls}
          ${disabled || imgUploading ? "cursor-wait" : "cursor-pointer hover:border-ink/40"}
          ${imgState.status === "error" ? "border-rose-400" : ""}
          ${imgState.status === "done" ? "border-emerald-400" : "border-border"}
        `}
        onClick={() => !disabled && !imgUploading && inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {displayUrl ? (
          <img
            src={displayUrl}
            alt={label}
            className={`h-full w-full object-cover ${radiusCls}`}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 bg-mist p-4 text-center">
            <ImageIcon className="h-6 w-6 text-muted-foreground/40" />
            <p className="text-xs text-muted-foreground">{hint ?? "Click or drag to upload"}</p>
            <p className="text-[10px] text-muted-foreground/60">JPG · PNG · WebP · max 5 MB</p>
          </div>
        )}
        {imgUploading && (
          <div className={`absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/50 ${radiusCls}`}>
            <Loader2 className="h-7 w-7 animate-spin text-white" />
            <p className="text-xs font-medium text-white">
              {imgState.status === "processing" ? "Optimising…" : "Uploading…"}
            </p>
          </div>
        )}
        {imgState.status === "done" && (
          <div className="absolute bottom-2 right-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500 shadow">
              <Check className="h-3.5 w-3.5 text-white" />
            </span>
          </div>
        )}
        {displayUrl && !imgUploading && !disabled && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); handleClear(); }}
            className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <div className="flex min-h-[18px] items-center justify-between">
        {imgState.status === "error" && (
          <p className="text-xs text-rose-500">{imgState.error}</p>
        )}
        {imgState.status === "done" && (
          <p className="text-xs text-emerald-600">Saved ✓</p>
        )}
        {displayUrl && !imgUploading && (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={disabled}
            className="ml-auto inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 text-[11px] text-muted-foreground hover:border-ink hover:text-ink disabled:opacity-50"
          >
            <Upload className="h-3 w-3" /> Change
          </button>
        )}
      </div>
    </div>
  );
}

// ── QR Code section ───────────────────────────────────────────────────────────
function QRSection({
  profile,
  onRegenerate,
}: {
  profile: MerchantProfile | null;
  onRegenerate: () => void;
}) {
  const { refreshMerchantProfile } = useAuth();
  const storeUrl = `${window.location.origin}/customer/merchant/${profile?.slug ?? ""}`;

  const generateQR = useMutation({
    mutationFn: () => merchantApi.regenerateQR(),
    onSuccess: async () => {
      await refreshMerchantProfile();
      onRegenerate();
      toast.success("QR code generated!");
    },
    onError: () => {
      toast.error("Failed to generate QR code.");
    },
  });

  return (
    <section className="glass-strong rounded-3xl p-6">
      <div className="flex items-center gap-2">
        <QrCode className="h-4 w-4 text-muted-foreground" />
        <h2 className="font-display text-2xl text-ink">QR Code &amp; Store Link</h2>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Customers scan this to open your loyalty page. Print it and place it at your counter.
      </p>

      <div className="mt-6 flex flex-col items-center gap-6 sm:flex-row sm:items-start">
        <div className="flex shrink-0 flex-col items-center gap-3">
          {profile?.qr_code ? (
            <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
              <img
                src={profile.qr_code}
                alt={`QR code for ${profile.business_name}`}
                className="h-48 w-48"
              />
            </div>
          ) : (
            <div className="flex h-48 w-48 flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border bg-mist">
              <QrCode className="h-12 w-12 text-muted-foreground/30" />
              <p className="text-center text-xs text-muted-foreground">No QR yet</p>
            </div>
          )}

          <div className="flex gap-2">
            {profile?.qr_code && (
              <a href={profile.qr_code}
                download={`${profile.slug}-qr.png`}
                className="inline-flex items-center gap-1.5 rounded-full border border-border px-4 py-2 text-xs text-muted-foreground transition-colors hover:border-ink hover:text-ink"
              >
                Download
              </a>
            )}
            <button
              onClick={() => generateQR.mutate()}
              disabled={generateQR.isPending}
              className="inline-flex items-center gap-1.5 rounded-full border border-border px-4 py-2 text-xs text-muted-foreground transition-colors hover:border-ink hover:text-ink disabled:opacity-50"
            >
              {generateQR.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3" />
              )}
              {profile?.qr_code ? "Regenerate" : "Generate QR"}
            </button>
          </div>
        </div>

        <div className="flex flex-1 flex-col gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Your store link
            </p>
            <div className="mt-2 flex items-center gap-2 rounded-2xl bg-mist px-4 py-3">
              <span className="flex-1 truncate text-sm text-ink">{storeUrl}</span>
              <a href={`/customer/merchant/${profile?.slug}`}
                target="_blank"
                rel="noreferrer"
                className="shrink-0 text-muted-foreground hover:text-ink"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
          </div>

          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Your slug
            </p>
            <p className="mt-1 text-sm text-ink">
              <span className="text-muted-foreground">/customer/merchant/</span>
              <span className="font-medium">{profile?.slug ?? "—"}</span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              To change your slug, contact support.
            </p>
          </div>

          <div className="rounded-2xl bg-amber-50 dark:bg-amber-950/30 px-4 py-3 text-xs leading-relaxed text-amber-700 dark:text-amber-400">
            The QR code points to your public customer page. It contains no
            private tokens — safe to print and share anywhere.
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
function StoreConfig() {
  const { merchantProfile: authMerchant } = useAuth();
  const [profile, setProfile] = useState<MerchantProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  const [form, setForm] = useState({
    business_name: "",
    description: "",
    business_type: "",
    address: "",
    phone: "",
    logo_url: "",
    banner_url: "",
    is_open: true,
    latitude: "" as string,
    longitude: "" as string,
    store_theme_color: "",
  });

  const [cardDesign, setCardDesign] = useState<Partial<MembershipCardDesign>>({
    card_title: "Membership",
    card_subtitle: "",
    primary_color: "#171717",
    secondary_color: "#382418",
    accent_color: "#D97941",
    text_mode: "light",
    background_type: "solid",
    background_pattern: "none",
    points_label: "POINTS",
    membership_label: "MEMBERSHIP",
    show_lifetime_points: true,
    show_joined_date: true,
    show_qr_shortcut: true,
    is_published: false,
  });
  const [cardDesignSaving, setCardDesignSaving] = useState(false);

  const fetchProfile = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await merchantApi.me();
      setProfile(data);
      setForm({
        business_name: data.business_name || "",
        description: data.description || "",
        business_type: data.business_type || "",
        address: data.address || "",
        phone: data.phone || "",
        logo_url: data.logo_url || "",
        banner_url: data.banner_url || "",
        is_open: data.is_open ?? true,
        latitude: data.latitude ?? "",
        longitude: data.longitude ?? "",
        store_theme_color: data.store_theme_color || "",
      });
    } catch (err) {
      setError("Could not load your store profile.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProfile(); }, [fetchProfile]);

  useEffect(() => {
    merchantCardDesignApi.get().then(setCardDesign).catch(() => {});
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setSaved(false);
      setError(null);
      const updated = await merchantApi.update(form);
      setProfile(updated);
      setForm({
        business_name: updated.business_name || "",
        description: updated.description || "",
        business_type: updated.business_type || "",
        address: updated.address || "",
        phone: updated.phone || "",
        logo_url: updated.logo_url || "",
        banner_url: updated.banner_url || "",
        is_open: updated.is_open ?? true,
        latitude: updated.latitude ?? "",
        longitude: updated.longitude ?? "",
        store_theme_color: updated.store_theme_color || "",
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError("Failed to save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field: string, value: string | boolean) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  async function handleSaveCardDesign(publish = false) {
    setCardDesignSaving(true);
    try {
      const updated = await merchantCardDesignApi.update(cardDesign);
      if (publish) {
        await merchantCardDesignApi.publish();
        toast.success("Card design published!");
      } else {
        toast.success("Card design saved!");
      }
      setCardDesign(updated);
    } catch {
      toast.error("Failed to save card design");
    }
    setCardDesignSaving(false);
  }

  function handleUseCurrentLocation() {
    if (!navigator.geolocation) {
      setLocationError("Your browser doesn't support location.");
      return;
    }
    setLocating(true);
    setLocationError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm((prev) => ({
          ...prev,
          latitude: pos.coords.latitude.toFixed(6),
          longitude: pos.coords.longitude.toFixed(6),
        }));
        setLocating(false);
      },
      (err) => {
        setLocationError(
          err.code === err.PERMISSION_DENIED
            ? "Location permission was denied. Enable it in your browser settings."
            : "Couldn't get your location. Try again."
        );
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
        <p className="text-sm text-destructive">{error}</p>
        <button
          onClick={fetchProfile}
          className="h-10 rounded-full bg-ink px-5 text-sm font-medium text-primary-foreground"
        >
          Retry
        </button>
      </div>
    );
  }

  const merchantId = String(profile?.id ?? "");
  const hasLocation = form.latitude !== "" && form.longitude !== "";

  return (
    <div className="space-y-8">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Storefront</p>
        <h1 className="font-display mt-1 text-5xl text-ink">Your store</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          How customers see you in the app. Keep it personal.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => updateField("is_open", !form.is_open)}
          className={`inline-flex h-9 items-center gap-2 rounded-full px-4 text-xs font-medium transition-all ${
            form.is_open ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400" : "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400"
          }`}
        >
          <span className={`h-2 w-2 rounded-full ${form.is_open ? "bg-emerald-500" : "bg-red-500"}`} />
          {form.is_open ? "Open" : "Closed"}
        </button>
        {profile && !profile.is_approved && (
          <span className="inline-flex h-9 items-center gap-2 rounded-full bg-amber-100 dark:bg-amber-900/40 px-4 text-xs font-medium text-amber-700 dark:text-amber-400">
            Pending approval
          </span>
        )}
      </div>

      <QRSection profile={profile} onRegenerate={fetchProfile} />

      <section className="glass-strong rounded-3xl p-6 space-y-6">
        <h2 className="font-display text-2xl text-ink">Images</h2>
        {merchantId && (
          <InlineImageUploader
            label="Store banner"
            hint="Recommended 1200 × 500 px"
            currentUrl={form.banner_url}
            onUpload={(url) => updateField("banner_url", url)}
            onClear={() => updateField("banner_url", "")}
            aspectClass="aspect-[12/5]"
            shape="square"
            merchantId={merchantId}
            bucket="banner-images"
            storagePath={`${merchantId}/banner.webp`}
            preset="banner"
          />
        )}
        {merchantId && (
          <div className="flex items-start gap-5">
            <div className="w-28 shrink-0">
              <InlineImageUploader
                label="Store logo"
                hint="Square"
                currentUrl={form.logo_url}
                onUpload={(url) => updateField("logo_url", url)}
                onClear={() => updateField("logo_url", "")}
                aspectClass="aspect-square"
                shape="circle"
                merchantId={merchantId}
                bucket="merchant-images"
                storagePath={`${merchantId}/logo.webp`}
                preset="logo"
              />
            </div>
            <p className="pt-8 text-xs leading-relaxed text-muted-foreground">
              Shown on the store listing card and in the customer app.
              <br />Min 200 × 200 px recommended.
            </p>
          </div>
        )}
      </section>

      {/* Theme section */}
      <section className="glass-strong rounded-3xl p-6">
        <div className="flex items-center gap-2">
          <Palette className="h-4 w-4 text-muted-foreground" />
          <h2 className="font-display text-2xl text-ink">Store Theme</h2>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose a brand color for your store. Customers will see this color in the app.
        </p>
        <div className="mt-5 space-y-4">
          <div>
            <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Brand Color
            </span>
            <div className="mt-2 flex items-center gap-3">
              <input
                type="color"
                value={form.store_theme_color || "#1e293b"}
                onChange={(e) => updateField("store_theme_color", e.target.value)}
                className="h-12 w-12 shrink-0 cursor-pointer rounded-xl border border-border"
              />
              <input
                value={form.store_theme_color}
                onChange={(e) => updateField("store_theme_color", e.target.value)}
                placeholder="#1e293b"
                className="h-12 flex-1 rounded-2xl bg-mist px-4 text-sm text-ink font-mono outline-none transition-all focus:ring-2 focus:ring-ember/40"
              />
              {form.store_theme_color && (
                <button
                  onClick={() => updateField("store_theme_color", "")}
                  className="text-xs text-muted-foreground hover:text-ink"
                >
                  Reset
                </button>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { label: "Slate", color: "#1e293b" },
              { label: "Emerald", color: "#059669" },
              { label: "Amber", color: "#d97706" },
              { label: "Rose", color: "#e11d48" },
              { label: "Indigo", color: "#4f46e5" },
              { label: "Teal", color: "#0d9488" },
              { label: "Violet", color: "#7c3aed" },
              { label: "Orange", color: "#ea580c" },
            ].map((preset) => (
              <button
                key={preset.color}
                onClick={() => updateField("store_theme_color", preset.color)}
                className="flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs transition-colors hover:border-ink"
              >
                <span
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: preset.color }}
                />
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {(form.logo_url || form.banner_url || form.business_name) && (
        <section className="glass-strong overflow-hidden rounded-3xl">
          <p className="px-5 pt-4 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Preview</p>
          <div
            className="relative h-28 bg-gradient-to-br from-ember/40 via-ember-soft to-mist"
            style={
              form.banner_url
                ? { backgroundImage: `url(${form.banner_url})`, backgroundSize: "cover", backgroundPosition: "center" }
                : undefined
            }
          />
          <div className="relative px-5 pb-5">
            <div className="-mt-8 flex items-end gap-3">
              <div
                className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl text-3xl text-primary-foreground shadow-soft"
                style={{
                  backgroundColor: form.store_theme_color || undefined,
                  backgroundImage: !form.store_theme_color && form.logo_url ? undefined : undefined,
                  ...(form.logo_url ? { backgroundImage: `url(${form.logo_url})`, backgroundSize: "cover", backgroundPosition: "center" } : {}),
                  ...(form.store_theme_color && !form.logo_url ? { backgroundColor: form.store_theme_color } : {}),
                }}
              >
                {!form.logo_url && "☕"}
              </div>
              <div className="pb-1">
                <p className="font-display text-lg text-ink">{form.business_name || "Your store name"}</p>
                <p className="text-xs text-muted-foreground">{form.business_type || "Café"}</p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ── Membership Card Design ─────────────────────────────────────────── */}
      <section className="glass-strong rounded-3xl p-6">
        <div className="flex items-center gap-2">
          <CreditCard className="h-4 w-4 text-muted-foreground" />
          <h2 className="font-display text-2xl text-ink">Membership Card Design</h2>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Customise how your loyalty card looks for customers. Changes are live once published.
        </p>

        {/* ── Live Preview ─────────────────────────────────────────────────── */}
        <div className="mt-6 flex flex-col items-center">
          <p className="mb-3 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Live Preview</p>
          <div
            className="relative w-[320px] h-[200px] rounded-[28px] overflow-hidden shadow-lg"
            style={{
              background: `linear-gradient(145deg, ${cardDesign.primary_color} 0%, ${cardDesign.secondary_color} 100%)`,
              color: cardDesign.text_mode === "light" ? "#ffffff" : "#1a1a1a",
            }}
          >
            {/* Pattern overlays */}
            {cardDesign.background_pattern === "dots" && (
              <div
                className="pointer-events-none absolute inset-0"
                style={{
                  backgroundImage: `radial-gradient(${cardDesign.text_mode === "light" ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"} 1.5px, transparent 1.5px)`,
                  backgroundSize: "16px 16px",
                }}
              />
            )}
            {cardDesign.background_pattern === "diamonds" && (
              <div
                className="pointer-events-none absolute inset-0"
                style={{
                  backgroundImage: `linear-gradient(45deg, ${cardDesign.text_mode === "light" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"} 25%, transparent 25%, transparent 75%, ${cardDesign.text_mode === "light" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"} 75%), linear-gradient(45deg, ${cardDesign.text_mode === "light" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"} 25%, transparent 25%, transparent 75%, ${cardDesign.text_mode === "light" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"} 75%)`,
                  backgroundSize: "24px 24px",
                  backgroundPosition: "0 0, 12px 12px",
                }}
              />
            )}
            {cardDesign.background_pattern === "geometric" && (
              <div
                className="pointer-events-none absolute inset-0"
                style={{
                  backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 30px, ${cardDesign.text_mode === "light" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"} 30px, ${cardDesign.text_mode === "light" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"} 31px), repeating-linear-gradient(90deg, transparent, transparent 30px, ${cardDesign.text_mode === "light" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"} 30px, ${cardDesign.text_mode === "light" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"} 31px)`,
                }}
              />
            )}

            {/* Decorative blurs */}
            <div
              className="pointer-events-none absolute -right-10 -top-10 h-36 w-36 rounded-full"
              style={{ background: "rgba(255,255,255,0.07)", filter: "blur(40px)" }}
            />
            <div
              className="pointer-events-none absolute -bottom-14 -left-14 h-36 w-36 rounded-full"
              style={{ background: "rgba(255,255,255,0.04)", filter: "blur(40px)" }}
            />

            {/* Card content */}
            <div className="relative flex h-full flex-col p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[9px] uppercase tracking-[0.22em] opacity-45">
                    {cardDesign.card_title || "Membership"}
                  </p>
                  <p className="mt-0.5 font-display text-[22px] leading-tight">
                    {profile?.business_name || "Your Store"}
                  </p>
                </div>
                <span
                  className="mt-0.5 shrink-0 rounded-full px-2.5 py-1 text-[9px] font-semibold uppercase tracking-widest"
                  style={{ background: "rgba(255,255,255,0.15)", color: cardDesign.text_mode === "light" ? "#ffffff" : "#1a1a1a" }}
                >
                  Bronze
                </span>
              </div>

              <div className="mt-auto">
                <p className="text-[9px] uppercase tracking-[0.22em] opacity-45">
                  {cardDesign.points_label || "POINTS"}
                </p>
                <p
                  className="font-display text-[52px] leading-none tracking-tight"
                  style={{ letterSpacing: "-0.03em", color: cardDesign.accent_color }}
                >
                  0
                </p>
              </div>

              <div className="mt-4 flex items-end justify-between">
                <div>
                  <p className="text-[9px] uppercase tracking-widest opacity-35">
                    {cardDesign.membership_label || "MEMBERSHIP"}
                  </p>
                  {cardDesign.show_joined_date && (
                    <p className="mt-0.5 font-mono text-[11px] tracking-wider opacity-60">
                      •••• ••••
                    </p>
                  )}
                </div>
                <p className="text-right text-[8px] opacity-25 tracking-wide">
                  Powered by Zentro
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Card Settings ─────────────────────────────────────────────────── */}
        <div className="mt-8 space-y-5">
          {/* Card title & subtitle */}
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Card Title</span>
              <input
                value={cardDesign.card_title ?? ""}
                onChange={(e) => setCardDesign((p) => ({ ...p, card_title: e.target.value }))}
                placeholder="Membership"
                className="mt-1.5 h-12 w-full rounded-2xl bg-mist px-4 text-sm text-ink outline-none transition-all focus:ring-2 focus:ring-ember/40"
              />
            </label>
            <label className="block">
              <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Card Subtitle</span>
              <input
                value={cardDesign.card_subtitle ?? ""}
                onChange={(e) => setCardDesign((p) => ({ ...p, card_subtitle: e.target.value }))}
                placeholder="Optional subtitle"
                className="mt-1.5 h-12 w-full rounded-2xl bg-mist px-4 text-sm text-ink outline-none transition-all focus:ring-2 focus:ring-ember/40"
              />
            </label>
          </div>

          {/* Colors */}
          {([
            { key: "primary_color", label: "Primary Color" },
            { key: "secondary_color", label: "Secondary Color" },
            { key: "accent_color", label: "Accent Color" },
          ] as const).map(({ key, label }) => (
            <div key={key}>
              <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
              <div className="mt-2 flex items-center gap-3">
                <input
                  type="color"
                  value={(cardDesign[key] as string) || "#000000"}
                  onChange={(e) => setCardDesign((p) => ({ ...p, [key]: e.target.value }))}
                  className="h-12 w-12 shrink-0 cursor-pointer rounded-xl border border-border"
                />
                <input
                  value={(cardDesign[key] as string) ?? ""}
                  onChange={(e) => setCardDesign((p) => ({ ...p, [key]: e.target.value }))}
                  placeholder="#000000"
                  className="h-12 flex-1 rounded-2xl bg-mist px-4 text-sm text-ink font-mono outline-none transition-all focus:ring-2 focus:ring-ember/40"
                />
              </div>
            </div>
          ))}

          {/* Text mode */}
          <div>
            <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Text Mode</span>
            <div className="mt-2 flex gap-2">
              {(["light", "dark"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setCardDesign((p) => ({ ...p, text_mode: mode }))}
                  className={`flex h-10 items-center gap-2 rounded-full px-5 text-xs font-medium transition-all ${
                    cardDesign.text_mode === mode
                      ? "bg-ink text-primary-foreground"
                      : "border border-border text-muted-foreground hover:border-ink hover:text-ink"
                  }`}
                >
                  {mode === "light" ? "Light Text" : "Dark Text"}
                </button>
              ))}
            </div>
          </div>

          {/* Background pattern */}
          <div>
            <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Background Pattern</span>
            <div className="mt-2 flex flex-wrap gap-2">
              {(["none", "dots", "geometric", "diamonds"] as const).map((pat) => (
                <button
                  key={pat}
                  onClick={() => setCardDesign((p) => ({ ...p, background_pattern: pat }))}
                  className={`flex h-9 items-center rounded-full px-4 text-xs font-medium capitalize transition-all ${
                    cardDesign.background_pattern === pat
                      ? "bg-ink text-primary-foreground"
                      : "border border-border text-muted-foreground hover:border-ink hover:text-ink"
                  }`}
                >
                  {pat}
                </button>
              ))}
            </div>
          </div>

          {/* Labels */}
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Points Label</span>
              <input
                value={cardDesign.points_label ?? ""}
                onChange={(e) => setCardDesign((p) => ({ ...p, points_label: e.target.value }))}
                placeholder="POINTS"
                className="mt-1.5 h-12 w-full rounded-2xl bg-mist px-4 text-sm text-ink outline-none transition-all focus:ring-2 focus:ring-ember/40"
              />
            </label>
            <label className="block">
              <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Membership Label</span>
              <input
                value={cardDesign.membership_label ?? ""}
                onChange={(e) => setCardDesign((p) => ({ ...p, membership_label: e.target.value }))}
                placeholder="MEMBERSHIP"
                className="mt-1.5 h-12 w-full rounded-2xl bg-mist px-4 text-sm text-ink outline-none transition-all focus:ring-2 focus:ring-ember/40"
              />
            </label>
          </div>

          {/* Toggle options */}
          <div className="space-y-3">
            {([
              { key: "show_lifetime_points" as const, label: "Show Lifetime Points" },
              { key: "show_joined_date" as const, label: "Show Joined Date" },
            ]).map(({ key, label }) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm text-ink">{label}</span>
                <button
                  type="button"
                  onClick={() => setCardDesign((p) => ({ ...p, [key]: !p[key] }))}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors ${
                    cardDesign[key] ? "bg-ink" : "bg-border"
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform mt-0.5 ${
                      cardDesign[key] ? "translate-x-[22px]" : "translate-x-0.5"
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* ── Actions ───────────────────────────────────────────────────────── */}
        <div className="mt-8 flex items-center justify-end gap-3">
          <button
            onClick={() => handleSaveCardDesign(false)}
            disabled={cardDesignSaving}
            className="inline-flex h-11 items-center gap-2 rounded-full border border-border px-5 text-xs font-medium text-muted-foreground transition-colors hover:border-ink hover:text-ink disabled:opacity-50"
          >
            {cardDesignSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            {cardDesignSaving ? "Saving…" : "Save Draft"}
          </button>
          <button
            onClick={() => handleSaveCardDesign(true)}
            disabled={cardDesignSaving}
            className="inline-flex h-12 items-center gap-2 rounded-full bg-ink px-7 text-sm font-medium text-primary-foreground shadow-ember transition-all disabled:opacity-50"
          >
            {cardDesignSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {cardDesignSaving ? "Publishing…" : "Publish"}
          </button>
        </div>
      </section>

      <section className="glass-strong rounded-3xl p-6">
        <h2 className="font-display text-2xl text-ink">Details</h2>
        <div className="mt-5 space-y-4">
          <Field
            label="Business name"
            value={form.business_name}
            onChange={(v) => updateField("business_name", v)}
          />
          <Field
            label="Tagline / Description"
            value={form.description}
            onChange={(v) => updateField("description", v)}
            multiline
          />
          <Field
            label="Category"
            value={form.business_type}
            onChange={(v) => updateField("business_type", v)}
            placeholder="e.g. Café · Bakery"
          />
        </div>
      </section>

      <div className="grid gap-3 lg:grid-cols-2">
        <section className="glass-strong rounded-3xl p-6">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
            <MapPin className="h-3.5 w-3.5" /> Location
          </div>
          <div className="mt-3 space-y-3">
            <Field
              label="Address"
              value={form.address}
              onChange={(v) => updateField("address", v)}
              placeholder="42 Thamel Street, Kathmandu"
            />
            <Field
              label="Phone"
              value={form.phone}
              onChange={(v) => updateField("phone", v)}
              placeholder="+977 98-0000-0000"
            />

            {/* ── Map coordinates ── */}
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  Map location
                </span>
                {hasLocation && (
                  <span className="text-[11px] text-emerald-600">Set ✓</span>
                )}
              </div>

              <button
                type="button"
                onClick={handleUseCurrentLocation}
                disabled={locating}
                className="mt-2 inline-flex h-11 w-full items-center justify-center gap-2 rounded-2xl border border-border text-sm font-medium text-ink transition-colors hover:border-ink disabled:opacity-50"
              >
                {locating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <LocateFixed className="h-4 w-4" />
                )}
                {locating
                  ? "Getting your location…"
                  : hasLocation
                  ? "Update to my current location"
                  : "Use my current location"}
              </button>

              {hasLocation && (
                <p className="mt-2 text-xs text-muted-foreground">
                  {Number(form.latitude).toFixed(5)}, {Number(form.longitude).toFixed(5)}
                </p>
              )}
              {locationError && (
                <p className="mt-2 text-xs text-rose-500">{locationError}</p>
              )}
              {!hasLocation && !locationError && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Stand at your store and tap this so customers can find you on the map.
                </p>
              )}
            </div>
          </div>
        </section>
        <section className="glass-strong rounded-3xl p-6">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
            <Clock className="h-3.5 w-3.5" /> Hours
          </div>
          <ul className="mt-3 space-y-2 text-sm">
            {[
              ["Mon – Fri", "7:00 – 18:00"],
              ["Saturday", "8:00 – 19:00"],
              ["Sunday", "8:00 – 16:00"],
            ].map(([d, h]) => (
              <li key={d} className="flex items-center justify-between">
                <span className="text-muted-foreground">{d}</span>
                <span className="text-ink">{h}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11px] italic text-muted-foreground">Hours editing coming soon</p>
        </section>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex items-center justify-end gap-3">
        {saved && (
          <span className="inline-flex items-center gap-1.5 text-sm text-emerald-600">
            <Check className="h-4 w-4" /> Saved!
          </span>
        )}
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex h-12 items-center gap-2 rounded-full bg-ink px-7 text-sm font-medium text-primary-foreground shadow-ember transition-all disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {saving ? "Saving…" : "Save changes"}
        </button>
      </div>
    </div>
  );
}

// ── Field component ───────────────────────────────────────────────────────────
function Field({
  label, value, onChange, placeholder, multiline = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  multiline?: boolean;
}) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
      {multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={3}
          className="mt-1.5 w-full resize-none rounded-2xl bg-mist px-4 py-3 text-sm text-ink outline-none transition-all focus:ring-2 focus:ring-ember/40"
        />
      ) : (
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="mt-1.5 h-12 w-full rounded-2xl bg-mist px-4 text-sm text-ink outline-none transition-all focus:ring-2 focus:ring-ember/40"
        />
      )}
    </label>
  );
}