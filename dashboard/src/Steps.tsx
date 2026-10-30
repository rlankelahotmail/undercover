import { type Step, read, useApi } from "./api";

function shown(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function StepView({ step }: Readonly<{ step: Step }>) {
  if (step.kind === "message") {
    return <p className="said">{step.content}</p>;
  }
  if (step.kind === "result") {
    return (
      <details>
        <summary>
          Result from <span className="mono">{step.name}</span>
        </summary>
        <pre>
          {JSON.stringify(JSON.parse(step.content) as unknown, null, 2)}
        </pre>
      </details>
    );
  }
  const args = Object.entries(JSON.parse(step.content) as object);
  return (
    <>
      <p>
        Calls <span className="mono">{step.name}</span>
      </p>
      <ul className="args">
        {args.map(([name, value]) => (
          <li key={name}>
            <span className="mono muted">{name}</span> {shown(value)}
          </li>
        ))}
      </ul>
    </>
  );
}

export function Steps({ claimId }: Readonly<{ claimId: string }>) {
  const { data: steps } = useApi(`/api/claims/${claimId}/steps`, read.steps);
  return (
    <section className="panel">
      <h2>The agent&apos;s steps</h2>
      {steps?.length ? (
        <ol className="steps">
          {steps.map((step) => (
            <li key={step.id} className={`step step-${step.kind}`}>
              <StepView step={step} />
            </li>
          ))}
        </ol>
      ) : (
        <p className="muted">No steps yet.</p>
      )}
    </section>
  );
}
