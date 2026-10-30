import { read, useApi } from "./api";

export function Instructions() {
  const { data } = useApi("/api/instructions", read.instructions, false);
  return (
    <>
      <h1>The agent&apos;s instructions</h1>
      <p className="muted">
        What the UnderCover Agent reads before every claim: its instructions,
        then the policy wording. Read only.
      </p>
      {data && (
        <section className="panel">
          <pre className="instructions">{data.instructions}</pre>
        </section>
      )}
    </>
  );
}
