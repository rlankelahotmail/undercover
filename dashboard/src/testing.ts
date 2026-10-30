import { vi } from "vitest";

export function stubApi(routes: Record<string, unknown>) {
  const fetch = vi.fn((input: string, init?: RequestInit) => {
    const key = init?.method === "POST" ? `POST ${input}` : input;
    if (key in routes) return Promise.resolve(Response.json(routes[key]));
    return Promise.resolve(new Response("{}", { status: 404 }));
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

export const QUEUE = [
  {
    claim_id: "CLM-1001",
    customer_name: "Maya Patel",
    claim_type: "trip_delay",
    summary: "Flight home canceled",
    submitted_on: "2026-06-24",
    amount_claimed: 420,
    status: "decided",
    outcome: "approve",
    payout: 420,
    paid: true,
  },
  {
    claim_id: "CLM-1002",
    customer_name: "Tom Becker",
    claim_type: "baggage",
    summary: "Suitcase lost on a connecting flight",
    submitted_on: "2026-07-20",
    amount_claimed: 1150,
    status: "waiting",
    outcome: null,
    payout: null,
    paid: false,
  },
  {
    claim_id: "CLM-1003",
    customer_name: "Ana Ruiz",
    claim_type: "emergency_medical",
    summary: "Fractured wrist",
    submitted_on: "2026-07-02",
    amount_claimed: 3800,
    status: "waiting_for_sign_off",
    outcome: "approve",
    payout: 1250,
    paid: false,
  },
  {
    claim_id: "CLM-1004",
    customer_name: "Lee Chen",
    claim_type: "passport",
    summary: "Passport stolen",
    submitted_on: "2026-07-05",
    amount_claimed: 186,
    status: "decided",
    outcome: "decline",
    payout: 0,
    paid: false,
  },
];
