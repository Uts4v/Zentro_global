import { createFileRoute } from "@tanstack/react-router";
import ConflictResolver from "@/features/pos/screens/ConflictResolver";

export const Route = createFileRoute("/pos/conflicts")({
  component: ConflictResolver,
});
