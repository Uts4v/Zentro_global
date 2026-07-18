import { createFileRoute } from "@tanstack/react-router";
import OrderDetailScreen from "@/features/pos/screens/OrderDetailScreen";

export const Route = createFileRoute("/pos/orders")({
  component: () => <OrderDetailScreen orderId={0} onBack={() => history.back()} />,
});
