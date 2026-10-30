import { type Claim, read, useApi } from "./api";
import { StatusBadge } from "./Badges";
import { DecisionPanel } from "./Decision";
import { day, money, words } from "./format";
import { Steps } from "./Steps";

function ClaimPanel({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel">
      <h2>The claim</h2>
      <dl className="facts">
        <dt>Type</dt>
        <dd>{words(claim.claim_type)}</dd>
        <dt>Incident</dt>
        <dd>
          <span className="mono">{day(claim.incident_date)}</span>
          {", "}
          {claim.incident_location}
        </dd>
        <dt>Submitted</dt>
        <dd className="mono">{day(claim.submitted_on)}</dd>
      </dl>
      <p className="story">{claim.story}</p>
    </section>
  );
}

function ItemsPanel({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel">
      <h2>Items claimed</h2>
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Category</th>
            <th className="amount">Amount</th>
          </tr>
        </thead>
        <tbody>
          {claim.items.map((item) => (
            <tr key={item.description}>
              <td>{item.description}</td>
              <td>{words(item.category)}</td>
              <td className="mono amount">{money(item.amount)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th colSpan={2}>Total claimed</th>
            <td className="mono amount">{money(claim.amount_claimed)}</td>
          </tr>
        </tfoot>
      </table>
    </section>
  );
}

function DocumentsPanel({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel">
      <h2>Documents</h2>
      <div className="documents">
        {claim.documents.map((document) => (
          <article key={document.name}>
            <h3>
              {document.name}{" "}
              <span className="muted">{words(document.type)}</span>
            </h3>
            <p>{document.content}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function PolicyPanel({ policyId }: Readonly<{ policyId: string }>) {
  const { data: policy } = useApi(
    `/api/policies/${policyId}`,
    read.policy,
    false,
  );
  if (!policy) return null;
  return (
    <section className="panel">
      <h2>
        Policy <span className="mono muted">{policy.policy_id}</span>
      </h2>
      <dl className="facts">
        <dt>Plan</dt>
        <dd>{words(policy.plan)}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_ons.map(words).join(", ") || "None"}</dd>
        <dt>Purchased</dt>
        <dd className="mono">{day(policy.purchased_on)}</dd>
        <dt>Sold through</dt>
        <dd>{policy.sold_through}</dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination},{" "}
          <span className="mono">
            {day(policy.trip.departs_on)} to {day(policy.trip.returns_on)}
          </span>
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{money(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
      </dl>
    </section>
  );
}

function HistoryPanel({ customerId }: Readonly<{ customerId: string }>) {
  const { data: history } = useApi(
    `/api/customers/${customerId}/history`,
    read.history,
    false,
  );
  if (!history) return null;
  return (
    <section className="panel">
      <h2>
        {history.name} <span className="mono muted">{history.customer_id}</span>
      </h2>
      <p className="muted">
        Customer since{" "}
        <span className="mono">{day(history.customer_since)}</span>
      </p>
      {history.previous_claims.length === 0 ? (
        <p>No earlier claims.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Earlier claim</th>
              <th>Filed</th>
              <th>Summary</th>
              <th>Outcome</th>
              <th className="amount">Paid</th>
            </tr>
          </thead>
          <tbody>
            {history.previous_claims.map((previous) => (
              <tr key={previous.claim_id}>
                <td className="mono">{previous.claim_id}</td>
                <td className="mono">{day(previous.filed_on)}</td>
                <td>{previous.summary}</td>
                <td>{words(previous.outcome)}</td>
                <td className="mono amount">{money(previous.amount_paid)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const {
    data: claim,
    failed,
    refresh,
  } = useApi(`/api/claims/${claimId}`, read.claim);

  if (!claim) {
    return failed ? (
      <p className="alert" role="alert">
        Claim {claimId} could not be loaded.
      </p>
    ) : null;
  }
  return (
    <>
      <a href="#/">Back to the queue</a>
      <div className="title">
        <h1>
          <span className="mono">{claim.claim_id}</span> {claim.summary}
        </h1>
        <StatusBadge status={claim.status} />
      </div>
      <div className="columns">
        <div className="column">
          <ClaimPanel claim={claim} />
          <ItemsPanel claim={claim} />
          <DocumentsPanel claim={claim} />
          <PolicyPanel policyId={claim.policy_id} />
          <HistoryPanel customerId={claim.customer_id} />
        </div>
        <div className="column">
          <DecisionPanel claim={claim} onSignedOff={refresh} />
          <Steps claimId={claim.claim_id} />
        </div>
      </div>
    </>
  );
}
