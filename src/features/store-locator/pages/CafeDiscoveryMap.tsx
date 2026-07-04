// src/features/store-locator/CafeDiscoveryMap.tsx
//
// Public entry point. Deliberately contains NO top-level import of
// "leaflet" or "react-leaflet" — those are pulled in via a dynamic
// import() inside useEffect, so they only ever load in the browser and
// never touch the SSR bundle (Leaflet reads `window` at module load time).
import { useEffect, useState } from "react";
import type { MerchantDiscoveryItem } from "@/lib/api";
import type { CafeDiscoveryMapProps } from "./CafeDiscoveryMapInner.tsx";

export function CafeDiscoveryMap(props: CafeDiscoveryMapProps) {
  const [InnerMap, setInnerMap] = useState<React.ComponentType<CafeDiscoveryMapProps> | null>(null);

  useEffect(() => {
    let active = true;
    import("./CafeDiscoveryMapInner.tsx").then((mod) => {
      if (active) setInnerMap(() => mod.CafeDiscoveryMapInner);
    });
    return () => {
      active = false;
    };
  }, []);

  if (!InnerMap) {
    // Skeleton shown during SSR and while Leaflet loads on the client.
    // No window/document access here, so it's safe to render on the server.
    return <div className="glass rounded-3xl" style={{ height: 260 }} />;
  }

  return <InnerMap {...props} />;
}

export type { MerchantDiscoveryItem };