import { useCallback, useEffect, useState } from "react";

export type Status =
  "waiting" | "in_progress" | "waiting_for_sign_off" | "decided";
export type Outcome = "approve" | "decline" | "refer";

export interface ClaimSummary {
  claim_id: string;
  customer_name: string;
  claim_type: string;
  summary: string;
  submitted_on: string;
  amount_claimed: number;
  status: Status;
  outcome: Outcome | null;
  payout: number | null;
  paid: boolean;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface Document {
  name: string;
  type: string;
  content: string;
}

export interface Decision {
  outcome: Outcome;
  payout: number;
  reason: string;
  policy_section: string;
  decided_at: string;
}

export interface SignOff {
  handler_id: string;
  handler_name: string;
  signed_off_at: string;
}

export interface Payment {
  amount: number;
  paid_at: string;
}

export interface Claim {
  claim_id: string;
  policy_id: string;
  customer_id: string;
  claim_type: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  summary: string;
  story: string;
  items: Item[];
  amount_claimed: number;
  documents: Document[];
  status: Status;
  decision: Decision | null;
  sign_off: SignOff | null;
  payment: Payment | null;
}

export interface Policy {
  policy_id: string;
  plan: string;
  add_ons: string[];
  purchased_on: string;
  sold_through: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
}

export interface PreviousClaim {
  claim_id: string;
  filed_on: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface ClaimHistory {
  customer_id: string;
  name: string;
  customer_since: string;
  previous_claims: PreviousClaim[];
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
  can_approve_over_limit: boolean;
}

export interface Step {
  id: number;
  thread_id: string;
  kind: "call" | "result" | "message";
  name: string;
  content: string;
  created_at: string;
}

// The backend's answers are trusted to have these shapes.
export const read = {
  queue: (data: unknown) => data as ClaimSummary[],
  claim: (data: unknown) => data as Claim,
  policy: (data: unknown) => data as Policy,
  history: (data: unknown) => data as ClaimHistory,
  handlers: (data: unknown) => data as Handler[],
  steps: (data: unknown) => data as Step[],
  instructions: (data: unknown) => data as { instructions: string },
};

const REFRESH_MS = 2000;

function check(response: Response): Response {
  if (!response.ok) {
    throw new Error(`The backend answered ${String(response.status)}`);
  }
  return response;
}

export async function post(path: string, body: object): Promise<void> {
  check(
    await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export function useApi<T>(
  path: string,
  reader: (data: unknown) => T,
  poll = true,
) {
  const [data, setData] = useState<T>();
  const [failed, setFailed] = useState(false);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let live = true;
    const load = () => {
      void fetch(path)
        .then((response) => check(response).json())
        .then((value: unknown) => {
          if (!live) return;
          setData(reader(value));
          setFailed(false);
        })
        .catch(() => {
          if (live) setFailed(true);
        });
    };
    load();
    const timer = poll ? setInterval(load, REFRESH_MS) : undefined;
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [path, reader, poll, version]);

  const refresh = useCallback(() => {
    setVersion((current) => current + 1);
  }, []);

  return { data, failed, refresh };
}
