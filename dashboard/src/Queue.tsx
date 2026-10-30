import { type ClaimSummary, read, useApi } from "./api";
import { OutcomeBadge, StatusBadge } from "./Badges";
import { STATUS_LABELS, STATUSES, day, money, words } from "./format";

function Decision({ claim }: Readonly<{ claim: ClaimSummary }>) {
  if (!claim.outcome) return <span className="muted">None yet</span>;
  return (
    <span className="decision">
      <OutcomeBadge outcome={claim.outcome} />
      {claim.outcome === "approve" && claim.payout !== null && (
        <span className="mono">{money(claim.payout)}</span>
      )}
      {claim.paid && <span className="muted">Paid</span>}
    </span>
  );
}

export function Queue() {
  const { data: claims, failed } = useApi("/api/claims", read.queue);

  return (
    <>
      <h1>Claims queue</h1>
      {failed && (
        <p className="alert" role="alert">
          The backend is not responding. Trying again.
        </p>
      )}
      {claims && (
        <>
          <section className="tiles" aria-label="Claims by status">
            {STATUSES.map((status) => {
              const count = claims.filter((c) => c.status === status).length;
              const label = STATUS_LABELS[status];
              return (
                <div
                  key={status}
                  className="panel tile"
                  aria-label={`${label}: ${String(count)}`}
                >
                  <span className="count mono">{count}</span>
                  <StatusBadge status={status} />
                </div>
              );
            })}
          </section>
          <section className="panel">
            <table>
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Customer</th>
                  <th>Type</th>
                  <th>Summary</th>
                  <th>Submitted</th>
                  <th className="amount">Claimed</th>
                  <th>Status</th>
                  <th>Decision</th>
                </tr>
              </thead>
              <tbody>
                {claims.map((claim) => (
                  <tr key={claim.claim_id}>
                    <td className="mono">
                      <a href={`#/claims/${claim.claim_id}`}>
                        {claim.claim_id}
                      </a>
                    </td>
                    <td>{claim.customer_name}</td>
                    <td>{words(claim.claim_type)}</td>
                    <td>{claim.summary}</td>
                    <td className="mono">{day(claim.submitted_on)}</td>
                    <td className="mono amount">
                      {money(claim.amount_claimed)}
                    </td>
                    <td>
                      <StatusBadge status={claim.status} />
                    </td>
                    <td className="nowrap">
                      <Decision claim={claim} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </>
  );
}
