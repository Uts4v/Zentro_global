import { createFileRoute } from "@tanstack/react-router";
import StaffManagementScreen from "../features/pos/screens/StaffManagementScreen";

export const Route = createFileRoute("/pos/staff")({
  component: StaffManagementScreen,
});
