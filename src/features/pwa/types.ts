// src/features/pwa/types.ts

export interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{
    outcome: "accepted" | "dismissed";
    platform: string;
  }>;
}

export type InstallPlatform = "ios" | "android" | "desktop" | "unsupported";

export interface PwaState {
  isInstallable: boolean;
  isInstalled: boolean;
  isStandalone: boolean;
  platform: InstallPlatform;
  deferredPrompt: BeforeInstallPromptEvent | null;
  updateAvailable: boolean;
  offlineReady: boolean;
}
