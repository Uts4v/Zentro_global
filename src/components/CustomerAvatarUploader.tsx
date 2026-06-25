// src/components/CustomerAvatarUploader.tsx
// Avatar uploader for the customer profile page.
// Calls supabase to persist the new URL after upload.
//
// Usage:
//   <CustomerAvatarUploader
//     customerId={user.id}
//     currentUrl={profile?.avatar_url}
//     onSaved={(url) => setProfile((p) => p ? { ...p, avatar_url: url } : p)}
//   />

import { useState } from "react";
import { ImageUploader } from "@/components/ImageUploader";
import { supabase } from "@/lib/supabase";
import { Loader2 } from "lucide-react";

interface CustomerAvatarUploaderProps {
  customerId: string;
  currentUrl?: string | null;
  /** Called after the URL has been persisted to the profiles table. */
  onSaved?: (url: string) => void;
  disabled?: boolean;
}

export function CustomerAvatarUploader({
  customerId,
  currentUrl,
  onSaved,
  disabled,
}: CustomerAvatarUploaderProps) {
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  async function handleUpload(publicUrl: string) {
    setSaving(true);
    setSaveError("");
    try {
      const { error } = await supabase
        .from("profiles")
        .update({ avatar_url: publicUrl })
        .eq("id", customerId);

      if (error) throw error;
      onSaved?.(publicUrl);
    } catch (err: any) {
      setSaveError(err.message ?? "Failed to save avatar.");
    } finally {
      setSaving(false);
    }
  }

  async function handleClear() {
    try {
      await supabase
        .from("profiles")
        .update({ avatar_url: null })
        .eq("id", customerId);
      onSaved?.("");
    } catch {
      /* best-effort clear */
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-5">
        {/* Circle avatar upload */}
        <div className="w-24 shrink-0">
          <ImageUploader
            preset="profile"
            bucket="customer-images"
            storagePath={`${customerId}/profile.webp`}
            currentUrl={currentUrl}
            onUpload={handleUpload}
            onClear={handleClear}
            shape="circle"
            aspectClass="aspect-square"
            hint=""
            disabled={disabled || saving}
          />
        </div>

        <div>
          <p className="text-sm font-medium text-ink">Profile photo</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            JPG, PNG, or WebP · max 5 MB
          </p>
          {saving && (
            <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" /> Saving…
            </p>
          )}
          {saveError && (
            <p className="mt-1 text-xs text-rose-500">{saveError}</p>
          )}
        </div>
      </div>
    </div>
  );
}