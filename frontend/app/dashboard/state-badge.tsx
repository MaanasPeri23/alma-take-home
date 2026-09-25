import type { components } from "@/lib/api/schema";

type LeadState = components["schemas"]["LeadState"];

export const STATE_LABELS: Record<LeadState, string> = {
  PENDING: "Pending",
  REACHED_OUT: "Reached out",
};

const STATE_STYLES: Record<LeadState, string> = {
  PENDING: "bg-amber-100 text-amber-800",
  REACHED_OUT: "bg-green-100 text-green-800",
};

export default function StateBadge({ state }: { state: LeadState }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATE_STYLES[state]}`}>
      {STATE_LABELS[state]}
    </span>
  );
}
