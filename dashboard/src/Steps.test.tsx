import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Steps } from "./Steps";
import { claimRoutes, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("lists the steps in order", async () => {
  stubApi(claimRoutes());
  const { container } = render(<Steps claimId="CLM-1003" />);
  await screen.findByText("Approved CLM-1003 for $1,250.00.");
  const steps = [...container.querySelectorAll("li.step")];
  expect(steps.map((step) => step.className)).toEqual([
    "step step-call",
    "step step-result",
    "step step-message",
  ]);
  expect(steps[0]?.textContent).toBe("Calls get_claimclaim_id CLM-1003");
  expect(steps[1]?.textContent).toContain('"story": "I slipped"');
});

it("folds each result until it is opened", async () => {
  stubApi(claimRoutes());
  render(<Steps claimId="CLM-1003" />);
  const summary = await screen.findByText("Result from");
  const details = summary.closest("details");
  expect(details?.open).toBe(false);
  fireEvent.click(summary);
  expect(details?.open).toBe(true);
});

it("says when there are no steps yet", async () => {
  stubApi({ "/api/claims/CLM-1003/steps": [] });
  render(<Steps claimId="CLM-1003" />);
  expect(await screen.findByText("No steps yet.")).toBeDefined();
});
