import { createFileRoute } from "@tanstack/react-router";
import PosOrderScreen from "@/features/pos/screens/PosOrderScreen";

export const Route = createFileRoute("/pos/")({
  component: PosOrderScreen,
});
