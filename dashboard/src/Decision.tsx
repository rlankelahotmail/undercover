import { useState } from "react";
import { type Claim, post, read, useApi } from "./api";
import { OutcomeBadge } from "./Badges";
import { moment, money } from "./format";

function SignOffForm({
  claim,
  payout,
  onSignedOff,
}: Readonly<{ claim: Claim; payout: number; onSignedOff: () => void }>) {
  const { data: handlers } = useApi("/api/handlers", read.handlers, false);
  const [handlerId, setHandlerId] = useState("");
  const [failed, setFailed] = useState(false);

  const signOff = () => {
    void post(`/api/claims/${claim.claim_id}/sign-off`, {
      handler_id: handlerId,
    })
      .then(onSignedOff)
      .catch(() => {
        setFailed(true);
      });
  };

  return (
    <form
      className="sign-off"
      onSubmit={(event) => {
        event.preventDefault();
        signOff();
      }}
    >
      <p>
        This payout is over $1,000, so it waits for a handler&apos;s sign-off
        before it&apos;s paid.
      </p>
      <label>
        Handler
        <select
          value={handlerId}
          onChange={(event) => {
            setHandlerId(event.target.value);
          }}
        >
          <option value="">Choose a handler</option>
          {handlers
            ?.filter((handler) => handler.can_approve_over_limit)
            .map((handler) => (
              <option key={handler.handler_id} value={handler.handler_id}>
                {handler.name}
              </option>
            ))}
        </select>
      </label>
      <button type="submit" disabled={!handlerId}>
        Sign off and pay {money(payout)}
      </button>
      {failed && (
        <p className="alert" role="alert">
          The sign-off didn&apos;t go through. Try again.
        </p>
      )}
    </form>
  );
}

function Payment({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  const { decision, payment, sign_off: signOff } = claim;
  if (decision?.outcome !== "approve") return null;
  return (
    <>
      {signOff && (
        <p>
          Signed off by {signOff.handler_name} on{" "}
          <span className="mono">{moment(signOff.signed_off_at)}</span>
        </p>
      )}
      {payment && (
        <p>
          Paid <span className="mono">{money(payment.amount)}</span> on{" "}
          <span className="mono">{moment(payment.paid_at)}</span>
        </p>
      )}
      {!payment && claim.status === "waiting_for_sign_off" && (
        <SignOffForm
          claim={claim}
          payout={decision.payout}
          onSignedOff={onSignedOff}
        />
      )}
      {!payment && claim.status === "decided" && (
        <p className="muted">Not paid yet.</p>
      )}
    </>
  );
}

export function DecisionPanel({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  const { decision } = claim;
  return (
    <section className="panel">
      <h2>Decision</h2>
      {decision ? (
        <>
          <div className="decision">
            <OutcomeBadge outcome={decision.outcome} />
            {decision.outcome === "approve" && (
              <span className="mono payout">{money(decision.payout)}</span>
            )}
          </div>
          <p>{decision.reason}</p>
          <dl className="facts">
            <dt>Policy section</dt>
            <dd>{decision.policy_section}</dd>
            <dt>Decided</dt>
            <dd className="mono">{moment(decision.decided_at)}</dd>
          </dl>
          <Payment claim={claim} onSignedOff={onSignedOff} />
        </>
      ) : (
        <p className="muted">
          {claim.status === "in_progress"
            ? "The agent is working on this claim."
            : "The agent hasn't worked this claim yet."}
        </p>
      )}
    </section>
  );
}
