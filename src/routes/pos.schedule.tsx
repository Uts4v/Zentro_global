import { createFileRoute } from "@tanstack/react-router";
import StaffScheduleScreen from "@/features/pos/screens/StaffScheduleScreen";

export const Route = createFileRoute("/pos/schedule")({
  component: StaffScheduleScreen,
});
