import { createFileRoute } from "@tanstack/react-router";
import ZReportScreen from "@/features/pos/screens/ZReportScreen";

export const Route = createFileRoute("/pos/reports/z-report")({
  component: ZReportScreen,
});
