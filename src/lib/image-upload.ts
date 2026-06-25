// src/lib/image-upload.ts
// Supabase Storage helpers: upload optimized blobs, delete old files,
// return stable public URLs. One function per image category.

import { supabase } from "@/lib/supabase";
import { optimizeImage, type ImagePreset } from "@/lib/image-optimize";

// ── Bucket names (must exist in your Supabase project) ───────────────────────
const BUCKETS = {
  merchant: "merchant-images",
  customer: "customer-images",
  product:  "product-images",
  banner:   "banner-images",
} as const;

export interface UploadResult {
  publicUrl: string;
  path: string;
}

// ── Core low-level uploader ───────────────────────────────────────────────────

/**
 * Optimize a File then upsert it into a Supabase Storage bucket.
 * Returns the permanent public URL and the storage path.
 *
 * We always upsert (overwrite) so the path acts as the stable key —
 * no need to track or delete old files when using fixed paths like
 * `product-images/{merchantId}/{productId}.webp`.
 */
export async function uploadImage(
  file: File,
  preset: ImagePreset,
  bucket: string,
  storagePath: string      // e.g. "abc123/profile.webp"
): Promise<UploadResult> {
  const { blob } = await optimizeImage(file, preset);

  const { error } = await supabase.storage
    .from(bucket)
    .upload(storagePath, blob, {
      contentType: "image/webp",
      upsert: true,           // overwrite silently — same path = same logical image
      cacheControl: "3600",
    });

  if (error) throw new Error(`Storage upload failed: ${error.message}`);

  const { data } = supabase.storage.from(bucket).getPublicUrl(storagePath);
  if (!data?.publicUrl) throw new Error("Could not get public URL after upload");

  return { publicUrl: data.publicUrl, path: storagePath };
}

/**
 * Delete a file from Supabase Storage by its path.
 * Silently ignores "not found" errors — safe to call on first upload.
 */
export async function deleteImage(bucket: string, path: string): Promise<void> {
  const { error } = await supabase.storage.from(bucket).remove([path]);
  if (error && !error.message.includes("Not Found")) {
    console.warn(`[deleteImage] ${error.message}`);
  }
}

// ── Per-category helpers ──────────────────────────────────────────────────────

/** Upload merchant logo. Path: merchant-images/{merchantId}/logo.webp */
export async function uploadMerchantLogo(
  file: File,
  merchantId: string
): Promise<UploadResult> {
  return uploadImage(
    file,
    "logo",
    BUCKETS.merchant,
    `${merchantId}/logo.webp`
  );
}

/** Upload merchant banner. Path: banner-images/{merchantId}/banner.webp */
export async function uploadMerchantBanner(
  file: File,
  merchantId: string
): Promise<UploadResult> {
  return uploadImage(
    file,
    "banner",
    BUCKETS.banner,
    `${merchantId}/banner.webp`
  );
}

/** Upload customer profile image. Path: customer-images/{customerId}/profile.webp */
export async function uploadCustomerProfile(
  file: File,
  customerId: string
): Promise<UploadResult> {
  return uploadImage(
    file,
    "profile",
    BUCKETS.customer,
    `${customerId}/profile.webp`
  );
}

/**
 * Upload a product/menu item image.
 * Path: product-images/{merchantId}/{productId}.webp
 * Pass productId as "new" for items not yet saved — caller can rename after.
 */
export async function uploadProductImage(
  file: File,
  merchantId: string,
  productId: string
): Promise<UploadResult> {
  return uploadImage(
    file,
    "product",
    BUCKETS.product,
    `${merchantId}/${productId}.webp`
  );
}

// ── Bucket names export (for direct use if needed) ────────────────────────────
export { BUCKETS };