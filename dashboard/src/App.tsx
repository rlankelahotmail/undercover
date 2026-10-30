import { ClaimPage } from "./Claim";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";
import { useHash } from "./route";

function Page({ hash }: Readonly<{ hash: string }>) {
  if (hash === "#/instructions") return <Instructions />;
  const claimId = /^#\/claims\/(.+)$/.exec(hash)?.[1];
  if (claimId) return <ClaimPage key={claimId} claimId={claimId} />;
  return <Queue />;
}

export function App() {
  const hash = useHash();
  const onInstructions = hash === "#/instructions";

  return (
    <>
      <header className="header">
        <a className="brand" href="#/">
          UnderCover
        </a>
        <span className="tagline">Claims desk</span>
        <nav aria-label="Main">
          <a href="#/" aria-current={onInstructions ? undefined : "page"}>
            Queue
          </a>
          <a
            href="#/instructions"
            aria-current={onInstructions ? "page" : undefined}
          >
            Instructions
          </a>
        </nav>
      </header>
      <main>
        <Page hash={hash} />
      </main>
    </>
  );
}
