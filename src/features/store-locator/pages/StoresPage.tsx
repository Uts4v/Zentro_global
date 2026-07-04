// store-locator/StorePage.tsx 
import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { MapPin, Loader2, ChevronRight } from "lucide-react";
import { merchantApi, type MerchantDiscoveryItem } from "@/lib/api";
import { CafeDiscoveryMap } from "@/features/store-locator/pages/CafeDiscoveryMap";

function StoreCard({
  store,
  onOpen,
}: {
  store: MerchantDiscoveryItem;
  onOpen: () => void;
}) {
  return (
    <div className="glass flex items-center gap-3 rounded-2xl p-3">
      <div
        className="grid h-14 w-14 shrink-0 place-items-center rounded-xl bg-mist text-2xl"
        style={
          store.logo_url
            ? { backgroundImage: `url(${store.logo_url})`, backgroundSize: "cover", backgroundPosition: "center" }
            : undefined
        }
      >
        {!store.logo_url && "☕"}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-ink">{store.business_name}</p>
        {store.address && (
          <p className="truncate text-xs text-muted-foreground">{store.address}</p>
        )}
        <div className="mt-1 flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
              store.is_open ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${store.is_open ? "bg-emerald-500" : "bg-red-500"}`} />
            {store.is_open ? "Open" : "Closed"}
          </span>
          {store.distance_km !== null && (
            <span className="text-[11px] text-muted-foreground">{store.distance_km} km away</span>
          )}
        </div>
      </div>

      <button
        onClick={onOpen}
        className="inline-flex h-9 shrink-0 items-center gap-1 rounded-full bg-ink px-4 text-xs font-medium text-primary-foreground"
      >
        Open <ChevronRight className="h-3 w-3" />
      </button>
    </div>
  );
}

export function StoresPage() {
  const [stores, setStores] = useState<MerchantDiscoveryItem[]>([]);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!navigator.geolocation) {
      loadStores();
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setUserLocation(loc);
        loadStores(loc.lat, loc.lng);
      },
      () => {
        // Permission denied or unavailable — fall back to unsorted list
        loadStores();
      },
      { timeout: 8000 }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadStores(lat?: number, lng?: number) {
    setLoading(true);
    setError("");
    try {
      const data = await merchantApi.nearby(lat, lng);
      setStores(data);
    } catch (e: any) {
      setError(e.message || "Failed to load nearby stores");
    } finally {
      setLoading(false);
    }
  }

  function openStore(slug: string) {
    navigate({ to: "/m/$slug", params: { slug } });
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-5 px-5 pb-10 pt-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Discover</p>
        <h1 className="font-display mt-1 text-3xl text-ink">Zentro-connected cafés</h1>
        {!userLocation && (
          <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3" /> Enable location for distance-sorted results
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <CafeDiscoveryMap
        merchants={stores}
        userLocation={userLocation}
        onSelectSlug={openStore}
      />

      <div className="space-y-2">
        {stores.length === 0 ? (
          <div className="glass rounded-3xl py-16 text-center">
            <p className="text-4xl">🔍</p>
            <p className="mt-3 text-sm text-muted-foreground">No connected cafés yet</p>
          </div>
        ) : (
          stores.map((store) => (
            <StoreCard key={store.id} store={store} onOpen={() => openStore(store.slug)} />
          ))
        )}
      </div>
    </div>
  );
}