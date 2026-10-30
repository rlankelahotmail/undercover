import type { Outcome, Status } from "./api";

export const STATUSES: Status[] = [
  "waiting",
  "in_progress",
  "waiting_for_sign_off",
  "decided",
];

export const STATUS_LABELS: Record<Status, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  waiting_for_sign_off: "Waiting for sign-off",
  decided: "Decided",
};

export const OUTCOME_LABELS: Record<Outcome, string> = {
  approve: "Approve",
  decline: "Decline",
  refer: "Refer",
};

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});
const days = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeZone: "UTC",
});
const moments = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function money(amount: number): string {
  return dollars.format(amount);
}

export function day(isoDate: string): string {
  return days.format(new Date(isoDate));
}

export function moment(isoTime: string): string {
  return moments.format(new Date(isoTime));
}

export function words(code: string): string {
  const spaced = code.replaceAll("_", " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
