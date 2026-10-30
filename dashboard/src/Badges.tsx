import type { Outcome, Status } from "./api";
import { OUTCOME_LABELS, STATUS_LABELS } from "./format";

export function StatusBadge({ status }: Readonly<{ status: Status }>) {
  return (
    <span className={`badge status-${status}`}>{STATUS_LABELS[status]}</span>
  );
}

export function OutcomeBadge({ outcome }: Readonly<{ outcome: Outcome }>) {
  return (
    <span className={`badge outcome-${outcome}`}>
      {OUTCOME_LABELS[outcome]}
    </span>
  );
}
