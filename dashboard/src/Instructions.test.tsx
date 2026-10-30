import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Instructions } from "./Instructions";
import { stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the instructions as read-only text", async () => {
  stubApi({
    "/api/instructions": {
      instructions: "# The UnderCover Agent\n\n# Policy Wording",
    },
  });
  render(<Instructions />);
  expect(await screen.findByText(/# The UnderCover Agent/)).toBeDefined();
  expect(screen.queryAllByRole("textbox")).toHaveLength(0);
  expect(screen.queryAllByRole("button")).toHaveLength(0);
});
