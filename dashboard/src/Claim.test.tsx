import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ClaimPage } from "./Claim";
import { CLAIM, claimRoutes, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the claim in full", async () => {
  stubApi(claimRoutes());
  render(<ClaimPage claimId="CLM-1003" />);
  expect(
    await screen.findByText(
      "I slipped on wet steps in Lisbon and broke my wrist.",
    ),
  ).toBeDefined();
  expect(screen.getByText("Emergency room visit")).toBeDefined();
  expect(screen.getByText("$3,800.00")).toBeDefined();
  expect(
    screen.getByText("Hospital de Santa Maria. Total: $3,800.00."),
  ).toBeDefined();
  expect(await screen.findByText("Premium")).toBeDefined();
  expect(screen.getByText("Adventure sports")).toBeDefined();
  expect(screen.getByText("$2,800.00")).toBeDefined();
  expect(await screen.findByText("CLM-0388")).toBeDefined();
  expect(screen.getByRole("heading", { name: /Aiko Tanaka/ })).toBeDefined();
});

it("shows the decision with its reason and section", async () => {
  stubApi(claimRoutes());
  render(<ClaimPage claimId="CLM-1003" />);
  expect(
    await screen.findByText("The treatment was necessary and covered."),
  ).toBeDefined();
  expect(screen.getByText("Section 7, Emergency Medical")).toBeDefined();
  expect(screen.getByText("Approve")).toBeDefined();
  expect(screen.getByText("$1,250.00")).toBeDefined();
});

it("signs off with the chosen handler", async () => {
  const fetch = stubApi({
    ...claimRoutes(),
    "POST /api/claims/CLM-1003/sign-off": CLAIM,
  });
  render(<ClaimPage claimId="CLM-1003" />);
  const button = await screen.findByRole("button", {
    name: "Sign off and pay $1,250.00",
  });
  expect(button).toHaveProperty("disabled", true);
  const select = screen.getByRole("combobox", { name: "Handler" });
  expect(await within(select).findByText("Dana Whitfield")).toBeDefined();
  expect(within(select).queryByText("Sam Trainee")).toBeNull();
  fireEvent.change(select, { target: { value: "HND-01" } });
  fireEvent.click(button);
  await vi.waitFor(() => {
    expect(fetch).toHaveBeenCalledWith("/api/claims/CLM-1003/sign-off", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ handler_id: "HND-01" }),
    });
  });
});

it("says when a sign-off fails", async () => {
  stubApi(claimRoutes());
  render(<ClaimPage claimId="CLM-1003" />);
  const select = await screen.findByRole("combobox", { name: "Handler" });
  await within(select).findByText("Dana Whitfield");
  fireEvent.change(select, { target: { value: "HND-01" } });
  fireEvent.click(
    screen.getByRole("button", { name: "Sign off and pay $1,250.00" }),
  );
  expect((await screen.findByRole("alert")).textContent).toBe(
    "The sign-off didn't go through. Try again.",
  );
});

it("offers a sign-off only while the claim waits for one", async () => {
  stubApi(
    claimRoutes({
      ...CLAIM,
      status: "decided",
      sign_off: {
        handler_id: "HND-01",
        handler_name: "Dana Whitfield",
        signed_off_at: "2026-10-30T07:00:00+00:00",
      },
      payment: { amount: 1250, paid_at: "2026-10-30T07:00:00+00:00" },
    }),
  );
  render(<ClaimPage claimId="CLM-1003" />);
  expect(await screen.findByText(/Signed off by Dana Whitfield/)).toBeDefined();
  expect(screen.getByText(/^Paid/, { selector: "p" }).textContent).toContain(
    "$1,250.00",
  );
  expect(screen.queryByRole("button")).toBeNull();
});

it("says when an approved claim is not paid yet", async () => {
  stubApi(claimRoutes({ ...CLAIM, status: "decided" }));
  render(<ClaimPage claimId="CLM-1003" />);
  expect(await screen.findByText("Not paid yet.")).toBeDefined();
  expect(screen.queryByRole("button")).toBeNull();
});

it("shows a claim the agent is working on", async () => {
  stubApi(claimRoutes({ ...CLAIM, status: "in_progress", decision: null }));
  render(<ClaimPage claimId="CLM-1003" />);
  expect(
    await screen.findByText("The agent is working on this claim."),
  ).toBeDefined();
  expect(screen.getByText("In progress")).toBeDefined();
});

it("says when a claim can't be loaded", async () => {
  stubApi({});
  render(<ClaimPage claimId="CLM-9999" />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Claim CLM-9999 could not be loaded.",
  );
});
