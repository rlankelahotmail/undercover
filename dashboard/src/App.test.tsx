import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { QUEUE, claimRoutes, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

it("shows the queue by default", async () => {
  stubApi({ "/api/claims": QUEUE });
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeDefined();
  expect(
    screen.getByRole("link", { name: "Queue" }).getAttribute("aria-current"),
  ).toBe("page");
  expect(
    screen.getByRole("link", { name: "Instructions" }).getAttribute("href"),
  ).toBe("#/instructions");
});

it("opens a claim from its route", async () => {
  stubApi(claimRoutes());
  window.location.hash = "#/claims/CLM-1003";
  render(<App />);
  expect(
    await screen.findByText(
      "I slipped on wet steps in Lisbon and broke my wrist.",
    ),
  ).toBeDefined();
});

it("opens the instructions from their route", async () => {
  stubApi({ "/api/instructions": { instructions: "Decide claims." } });
  window.location.hash = "#/instructions";
  render(<App />);
  expect(await screen.findByText("Decide claims.")).toBeDefined();
  expect(
    screen
      .getByRole("link", { name: "Instructions" })
      .getAttribute("aria-current"),
  ).toBe("page");
});
