import { createFileRoute } from "@tanstack/react-router";
import PosSettingsScreen from "@/features/pos/screens/PosSettingsScreen";

export const Route = createFileRoute("/pos/settings")({
  component: PosSettingsScreen,
});
