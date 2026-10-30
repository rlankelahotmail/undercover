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

export const CLAIM = {
  claim_id: "CLM-1003",
  policy_id: "POL-2003",
  customer_id: "CUS-3003",
  claim_type: "emergency_medical",
  submitted_on: "2026-07-06",
  incident_date: "2026-06-30",
  incident_location: "Lisbon, Portugal",
  summary: "Hospital visit abroad after a fall, fractured wrist",
  story: "I slipped on wet steps in Lisbon and broke my wrist.",
  items: [
    { description: "Emergency room visit", category: "medical", amount: 2400 },
    { description: "Wrist cast", category: "medical", amount: 1400 },
  ],
  amount_claimed: 3800,
  documents: [
    {
      name: "Hospital bill",
      type: "invoice",
      content: "Hospital de Santa Maria. Total: $3,800.00.",
    },
  ],
  status: "waiting_for_sign_off",
  decision: {
    outcome: "approve",
    payout: 1250,
    reason: "The treatment was necessary and covered.",
    policy_section: "Section 7, Emergency Medical",
    decided_at: "2026-10-30T06:30:00+00:00",
  },
  sign_off: null,
  payment: null,
};

export const POLICY = {
  policy_id: "POL-2003",
  plan: "premium",
  add_ons: ["adventure_sports"],
  purchased_on: "2026-05-01",
  sold_through: "UnderCover website",
  trip: {
    destination: "Lisbon, Portugal",
    departs_on: "2026-06-25",
    returns_on: "2026-07-05",
    trip_cost: 2800,
  },
  travelers: ["Aiko Tanaka"],
};

export const HISTORY = {
  customer_id: "CUS-3003",
  name: "Aiko Tanaka",
  customer_since: "2022-02-14",
  previous_claims: [
    {
      claim_id: "CLM-0388",
      filed_on: "2025-03-02",
      claim_type: "baggage_delay",
      summary: "Bag arrived a day late",
      outcome: "approved",
      amount_paid: 90,
    },
  ],
};

export const HANDLERS = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
    can_approve_over_limit: true,
  },
  {
    handler_id: "HND-04",
    name: "Sam Trainee",
    role: "Trainee",
    can_approve_over_limit: false,
  },
];

export const STEPS = [
  {
    id: 1,
    thread_id: "t1",
    kind: "call",
    name: "get_claim",
    content: JSON.stringify({ claim_id: "CLM-1003" }),
    created_at: "2026-10-30T06:29:50+00:00",
  },
  {
    id: 2,
    thread_id: "t1",
    kind: "result",
    name: "get_claim",
    content: JSON.stringify({ claim_id: "CLM-1003", story: "I slipped" }),
    created_at: "2026-10-30T06:29:51+00:00",
  },
  {
    id: 3,
    thread_id: "t1",
    kind: "message",
    name: "agent",
    content: "Approved CLM-1003 for $1,250.00.",
    created_at: "2026-10-30T06:30:01+00:00",
  },
];

export function claimRoutes(claim: object = CLAIM) {
  return {
    "/api/claims/CLM-1003": claim,
    "/api/policies/POL-2003": POLICY,
    "/api/customers/CUS-3003/history": HISTORY,
    "/api/claims/CLM-1003/steps": STEPS,
    "/api/handlers": HANDLERS,
  };
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
