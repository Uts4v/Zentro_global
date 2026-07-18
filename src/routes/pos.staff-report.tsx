import { createFileRoute } from "@tanstack/react-router";
import StaffDailyReportScreen from "@/features/pos/screens/StaffDailyReportScreen";

export const Route = createFileRoute("/pos/staff-report")({
  component: StaffDailyReportScreen,
});
