import { createFileRoute, Outlet, useRouterState } from "@tanstack/react-router";
import ReportsScreen from "@/features/pos/screens/ReportsScreen";

function ReportsLayout() {
  const routerState = useRouterState();
  const pathname = routerState.location.pathname;

  // If on a child route (e.g. /pos/reports/z-report), render the child
  if (pathname !== "/pos/reports" && pathname !== "/pos/reports/") {
    return <Outlet />;
  }

  // Otherwise render the reports dashboard
  return <ReportsScreen />;
}

export const Route = createFileRoute("/pos/reports")({
  component: ReportsLayout,
});
