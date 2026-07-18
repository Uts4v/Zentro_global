import { createFileRoute } from "@tanstack/react-router";
import CashMovementsScreen from "@/features/pos/screens/CashMovementsScreen";

export const Route = createFileRoute("/pos/cash-movements")({
  component: CashMovementsScreen,
});
