import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Queue } from "./Queue";
import { QUEUE, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("counts the claims in each state", async () => {
  stubApi({ "/api/claims": QUEUE });
  render(<Queue />);
  expect(await screen.findByLabelText("Waiting: 1")).toBeDefined();
  expect(screen.getByLabelText("In progress: 0")).toBeDefined();
  expect(screen.getByLabelText("Waiting for sign-off: 1")).toBeDefined();
  expect(screen.getByLabelText("Decided: 2")).toBeDefined();
});

it("lists each claim with a link to its page", async () => {
  stubApi({ "/api/claims": QUEUE });
  render(<Queue />);
  const link = await screen.findByRole("link", { name: "CLM-1002" });
  expect(link.getAttribute("href")).toBe("#/claims/CLM-1002");
  const row = within(link.closest("tr") ?? document.body);
  expect(row.getByText("Tom Becker")).toBeDefined();
  expect(row.getByText("Baggage")).toBeDefined();
  expect(row.getByText("$1,150.00")).toBeDefined();
  expect(row.getByText("Jul 20, 2026")).toBeDefined();
  expect(row.getByText("Waiting")).toBeDefined();
  expect(row.getByText("None yet")).toBeDefined();
});

it("shows each decision with its payout", async () => {
  stubApi({ "/api/claims": QUEUE });
  render(<Queue />);
  const approved = within(
    (await screen.findByRole("link", { name: "CLM-1001" })).closest("tr") ??
      document.body,
  );
  expect(approved.getByText("Approve")).toBeDefined();
  expect(approved.getAllByText("$420.00")).toHaveLength(2);
  expect(approved.getByText("Paid")).toBeDefined();
  const declined = within(
    screen.getByRole("link", { name: "CLM-1004" }).closest("tr") ??
      document.body,
  );
  expect(declined.getByText("Decline")).toBeDefined();
  expect(declined.queryByText("$0.00")).toBeNull();
});

it("says when the backend is not responding", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  render(<Queue />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "The backend is not responding. Trying again.",
  );
});
