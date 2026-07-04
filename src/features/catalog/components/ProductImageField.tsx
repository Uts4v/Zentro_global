// src/components/ProductImageField.tsx
// Replaces the plain "Image URL" text input in merchant/menu.tsx.
// Drop this into MerchantMenu's form modal where the image_url field is.
//
// Usage:
//   <ProductImageField
//     merchantId={merchantProfile.id}
//     productId={editing?.id ?? "new"}
//     currentUrl={form.image_url}
//     onChange={(url) => setForm((f) => ({ ...f, image_url: url }))}
//   />

import { ImageUploader } from "@/components/image-uploader";

interface ProductImageFieldProps {
  merchantId: string;
  /** Pass the real product id when editing, or "new" for create flow. */
  productId: string;
  currentUrl?: string;
  onChange: (url: string) => void;
  disabled?: boolean;
}

export function ProductImageField({
  merchantId,
  productId,
  currentUrl,
  onChange,
  disabled,
}: ProductImageFieldProps) {
  // For new items we use a stable temp key; after the item is saved the
  // merchant can re-upload (or you can re-key storagePath with the real id).
  const storagePath = `${merchantId}/${productId}.webp`;

  return (
    <ImageUploader
      preset="product"
      bucket="product-images"
      storagePath={storagePath}
      currentUrl={currentUrl}
      onUpload={onChange}
      onClear={() => onChange("")}
      label="Product image"
      hint="Click or drag product photo here"
      shape="square"
      aspectClass="aspect-square"
      disabled={disabled}
    />
  );
}
