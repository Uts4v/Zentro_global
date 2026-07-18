import { createFileRoute } from "@tanstack/react-router";
import TableOrderScreen from "@/features/pos/screens/TableOrderScreen";

export const Route = createFileRoute("/table/$token/order")({
  component: TableOrderScreen,
});
