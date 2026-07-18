import { createFileRoute, Outlet } from "@tanstack/react-router";
import PosLayout from "@/features/pos/screens/PosLayout";

export const Route = createFileRoute("/pos")({
  component: PosLayout,
});
