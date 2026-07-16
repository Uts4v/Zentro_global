import { createFileRoute } from "@tanstack/react-router";
import { requireCustomer } from "@/lib/auth-guard";
import { CartPage } from "@/features/transactions/pages/CartPage";

export const Route = createFileRoute("/cart")({
  beforeLoad: requireCustomer,
  head: () => ({ meta: [{ title: "Your bag · Zentro" }] }),
  component: CartPage,
});
