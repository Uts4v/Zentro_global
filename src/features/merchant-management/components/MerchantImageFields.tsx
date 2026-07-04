// src/components/MerchantImageFields.tsx
// Logo + banner uploaders for the merchant profile/settings page.
//
// Usage:
//   <MerchantImageFields
//     merchantId={merchantProfile.id}
//     logoUrl={form.logo_url}
//     bannerUrl={form.banner_url}
//     onLogoChange={(url) => setForm((f) => ({ ...f, logo_url: url }))}
//     onBannerChange={(url) => setForm((f) => ({ ...f, banner_url: url }))}
//   />

import { ImageUploader } from "@/components/image-uploader";

interface MerchantImageFieldsProps {
  merchantId: string;
  logoUrl?: string | null;
  bannerUrl?: string | null;
  onLogoChange: (url: string) => void;
  onBannerChange: (url: string) => void;
  disabled?: boolean;
}

export function MerchantImageFields({
  merchantId,
  logoUrl,
  bannerUrl,
  onLogoChange,
  onBannerChange,
  disabled,
}: MerchantImageFieldsProps) {
  return (
    <div className="space-y-6">
      {/* Banner — wide 12:5 ratio */}
      <ImageUploader
        preset="banner"
        bucket="banner-images"
        storagePath={`${merchantId}/banner.webp`}
        currentUrl={bannerUrl}
        onUpload={onBannerChange}
        onClear={() => onBannerChange("")}
        label="Store banner"
        hint="Recommended: 1200 × 500 px"
        shape="square"
        aspectClass="aspect-[12/5]"
        disabled={disabled}
      />

      {/* Logo — circle, 1:1 */}
      <div className="flex items-start gap-6">
        <div className="w-32 shrink-0">
          <ImageUploader
            preset="logo"
            bucket="merchant-images"
            storagePath={`${merchantId}/logo.webp`}
            currentUrl={logoUrl}
            onUpload={onLogoChange}
            onClear={() => onLogoChange("")}
            label="Store logo"
            hint="Square works best"
            shape="circle"
            aspectClass="aspect-square"
            disabled={disabled}
          />
        </div>
        <div className="pt-6 text-sm text-muted-foreground leading-relaxed">
          Your logo appears on the store listing and customer receipts.
          <br />
          Min 200 × 200 px recommended.
        </div>
      </div>
    </div>
  );
}
