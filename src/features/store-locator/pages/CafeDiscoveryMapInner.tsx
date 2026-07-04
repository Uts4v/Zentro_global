// src/features/store-locator/CafeDiscoveryMapInner.tsx
//
// This file is only ever loaded via a dynamic import() from
// CafeDiscoveryMap.tsx, which happens inside a useEffect (client-only).
// Never import this file directly, and never import it at the top of a
// file that participates in SSR — Leaflet touches `window` at module load
// time and will crash the server render.
import { useEffect, useMemo, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { MerchantDiscoveryItem } from "@/lib/api";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const userIcon = L.divIcon({
  className: "",
  html: `<div style="
    width: 16px; height: 16px; border-radius: 9999px;
    background: #3b82f6; border: 3px solid white;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.4);
  "></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

export interface CafeDiscoveryMapProps {
  merchants: MerchantDiscoveryItem[];
  userLocation: { lat: number; lng: number } | null;
  onSelectSlug: (slug: string) => void;
}

function MapRecenter({ center }: { center: [number, number] }) {
  const map = useMap();
  const hasCentered = useRef(false);

  useEffect(() => {
    if (!hasCentered.current) {
      map.setView(center, map.getZoom());
      hasCentered.current = true;
    }
  }, [center, map]);

  return null;
}

export function CafeDiscoveryMapInner({ merchants, userLocation, onSelectSlug }: CafeDiscoveryMapProps) {
  const pins = useMemo(
    () =>
      merchants
        .filter((m) => m.latitude !== null && m.longitude !== null)
        .map((m) => ({
          ...m,
          lat: parseFloat(m.latitude as string),
          lng: parseFloat(m.longitude as string),
        }))
        .filter((m) => !Number.isNaN(m.lat) && !Number.isNaN(m.lng)),
    [merchants]
  );

  const center: [number, number] = useMemo(() => {
    if (userLocation) return [userLocation.lat, userLocation.lng];
    if (pins.length > 0) return [pins[0].lat, pins[0].lng];
    return [27.7172, 85.324];
  }, [userLocation, pins]);

  if (pins.length === 0 && !userLocation) {
    return null;
  }

  return (
    <div className="glass overflow-hidden rounded-3xl" style={{ height: 260 }}>
      <MapContainer center={center} zoom={13} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapRecenter center={center} />

        {userLocation && (
          <Marker position={[userLocation.lat, userLocation.lng]} icon={userIcon}>
            <Popup>You are here</Popup>
          </Marker>
        )}

        {pins.map((store) => (
          <Marker
            key={store.id}
            position={[store.lat, store.lng]}
            icon={defaultIcon}
            eventHandlers={{ click: () => onSelectSlug(store.slug) }}
          >
            <Popup>
              <div className="text-sm font-medium">{store.business_name}</div>
              {store.address && <div className="text-xs text-muted-foreground">{store.address}</div>}
              <button onClick={() => onSelectSlug(store.slug)} className="mt-1 text-xs font-semibold text-ember underline">
                Open store →
              </button>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}