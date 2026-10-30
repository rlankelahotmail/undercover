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

export const read = {
  queue: (data: unknown) => data as ClaimSummary[],
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
