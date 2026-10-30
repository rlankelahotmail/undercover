import { Queue } from "./Queue";
import { useHash } from "./route";

export function App() {
  const hash = useHash();

  return (
    <>
      <header className="header">
        <a className="brand" href="#/">
          UnderCover
        </a>
        <span className="tagline">Claims desk</span>
        <nav aria-label="Main">
          <a
            href="#/"
            aria-current={hash === "#/instructions" ? undefined : "page"}
          >
            Queue
          </a>
          <a
            href="#/instructions"
            aria-current={hash === "#/instructions" ? "page" : undefined}
          >
            Instructions
          </a>
        </nav>
      </header>
      <main>
        <Queue />
      </main>
    </>
  );
}
